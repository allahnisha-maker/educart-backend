"""EduCart API: products, carts and orders on PostgreSQL."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://educart:educart@localhost:5432/educart")
SCHEMA = (Path(__file__).parent / "schema.sql").read_text()

PRODUCT_COLS = "id, name, description, price::float8 AS price, image, stock"
CART_ITEMS_SQL = f"""
    SELECT p.id, p.name, p.price::float8 AS price, p.image, p.stock, ci.quantity
    FROM cart_items ci JOIN products p ON p.id = ci.product_id
    WHERE ci.cart_id = %s ORDER BY p.name
"""


def db():
    # ponytail: one connection per request; add psycopg_pool if load ever matters.
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


@asynccontextmanager
async def lifespan(_app):
    with db() as conn:
        conn.execute(SCHEMA)
    yield


app = FastAPI(title="EduCart API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class Customer(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    studentClass: str = Field(pattern=r"^Class ([1-9]|1[0-2])$")
    address: str = Field(min_length=10, max_length=500)
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", max_length=254)
    phone: str = Field(pattern=r"^\+?[\d\s()-]+$", max_length=20)


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=99)


class QuantityIn(BaseModel):
    quantity: int = Field(ge=0, le=99)


class OrderIn(BaseModel):
    cart_id: UUID
    customer: Customer


# --- products ---------------------------------------------------------------


@app.get("/api/products")
def list_products(q: str = ""):
    terms = q.lower().split()
    where = " AND ".join("(name || ' ' || description) ILIKE %s" for _ in terms) or "TRUE"
    with db() as conn:
        return conn.execute(
            f"SELECT {PRODUCT_COLS} FROM products WHERE {where} ORDER BY id",
            [f"%{t}%" for t in terms],
        ).fetchall()


# --- carts ------------------------------------------------------------------


def load_cart(conn, cart_id):
    if conn.execute("SELECT 1 FROM carts WHERE id = %s", [cart_id]).fetchone() is None:
        raise HTTPException(404, "Cart not found")
    return {"id": str(cart_id), "items": conn.execute(CART_ITEMS_SQL, [cart_id]).fetchall()}


@app.post("/api/carts", status_code=201)
def create_cart():
    with db() as conn:
        row = conn.execute("INSERT INTO carts DEFAULT VALUES RETURNING id").fetchone()
        return {"id": str(row["id"]), "items": []}


@app.get("/api/carts/{cart_id}")
def get_cart(cart_id: UUID):
    with db() as conn:
        return load_cart(conn, cart_id)


@app.post("/api/carts/{cart_id}/items")
def add_cart_item(cart_id: UUID, item: CartItemIn):
    with db() as conn:
        load_cart(conn, cart_id)
        if conn.execute("SELECT 1 FROM products WHERE id = %s", [item.product_id]).fetchone() is None:
            raise HTTPException(404, "Product not found")
        conn.execute(
            """INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (%s, %s, %s)
               ON CONFLICT (cart_id, product_id)
               DO UPDATE SET quantity = LEAST(99, cart_items.quantity + EXCLUDED.quantity)""",
            [cart_id, item.product_id, item.quantity],
        )
        return load_cart(conn, cart_id)


@app.put("/api/carts/{cart_id}/items/{product_id}")
def set_cart_item(cart_id: UUID, product_id: int, body: QuantityIn):
    with db() as conn:
        load_cart(conn, cart_id)
        if body.quantity == 0:
            conn.execute("DELETE FROM cart_items WHERE cart_id = %s AND product_id = %s", [cart_id, product_id])
        else:
            conn.execute(
                "UPDATE cart_items SET quantity = %s WHERE cart_id = %s AND product_id = %s",
                [body.quantity, cart_id, product_id],
            )
        return load_cart(conn, cart_id)


# --- orders -----------------------------------------------------------------


@app.post("/api/orders", status_code=201)
def place_order(order: OrderIn):
    c = order.customer
    with db() as conn:  # one transaction: commits on success, rolls back on any exception
        load_cart(conn, order.cart_id)
        # Lock the product rows so two checkouts can't both take the last unit.
        items = conn.execute(
            """SELECT p.id, p.name, p.price::float8 AS price, p.stock, ci.quantity
               FROM cart_items ci JOIN products p ON p.id = ci.product_id
               WHERE ci.cart_id = %s ORDER BY p.id FOR UPDATE OF p""",
            [order.cart_id],
        ).fetchall()
        if not items:
            raise HTTPException(400, "Cart is empty")

        short = [i for i in items if i["quantity"] > i["stock"]]
        if short:
            raise HTTPException(
                409,
                {
                    "message": "Not enough stock for some items",
                    "items": [{"id": i["id"], "name": i["name"], "stock": i["stock"]} for i in short],
                },
            )

        total = sum(i["price"] * i["quantity"] for i in items)
        order_id = conn.execute(
            """INSERT INTO orders (customer_name, student_class, address, email, phone, total)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            [c.name.strip(), c.studentClass, c.address.strip(), c.email.strip(), c.phone.strip(), total],
        ).fetchone()["id"]
        for i in items:
            conn.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
                [order_id, i["id"], i["quantity"], i["price"]],
            )
            conn.execute("UPDATE products SET stock = stock - %s WHERE id = %s", [i["quantity"], i["id"]])
        conn.execute("DELETE FROM cart_items WHERE cart_id = %s", [order.cart_id])

        return {
            "id": order_id,
            "customer": c.model_dump(),
            "items": [{"id": i["id"], "name": i["name"], "price": i["price"], "quantity": i["quantity"]} for i in items],
            "itemCount": sum(i["quantity"] for i in items),
            "total": total,
        }
