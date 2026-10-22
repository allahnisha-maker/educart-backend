# EduCart Backend

Python (FastAPI) API for the [EduCart](https://github.com/djyuga2003/E-Commerce-Vels_Academy-) storefront, on PostgreSQL 17.
Products, search, carts and order placement live here; placing an order re-prices the cart from the database, checks stock and reduces it.

## Run

Requires Docker and [uv](https://docs.astral.sh/uv/).

```bash
docker compose up -d                       # PostgreSQL 17 on localhost:5432
uv run uvicorn main:app --port 8000        # creates tables and seeds 12 products on start-up
```

Test (needs the database running):

```bash
uv run pytest
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/products?q=` | catalogue, optional search over name + description |
| POST | `/api/carts` | new cart |
| GET | `/api/carts/{id}` | cart contents |
| POST | `/api/carts/{id}/items` | `{ product_id, quantity }` adds to the cart |
| PUT | `/api/carts/{id}/items/{product_id}` | `{ quantity }` sets it; 0 removes |
| POST | `/api/orders` | `{ cart_id, customer }` — re-prices, locks stock, writes the order, reduces stock, empties the cart. 409 if stock is short. |

Interactive docs: http://localhost:8000/docs

## Config

| Variable | Default |
| --- | --- |
| `DATABASE_URL` | `postgresql://educart:educart@localhost:5432/educart` |
| `CORS_ORIGINS` | `*` (comma-separated list of allowed frontend origins) |

## Frontend

The React frontend proxies `/api` to this server in development, or set `VITE_API_URL` there to point at it.
