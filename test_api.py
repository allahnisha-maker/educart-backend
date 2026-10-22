"""End-to-end check against a running PostgreSQL (docker compose up -d)."""

from fastapi.testclient import TestClient

from main import app


def test_search_cart_checkout_reduces_stock():
    with TestClient(app) as client:
        assert [p["name"] for p in client.get("/api/products", params={"q": "gel pen"}).json()] == ["Gel Pen Set"]

        before = next(p for p in client.get("/api/products").json() if p["id"] == 1)["stock"]
        cart_id = client.post("/api/carts").json()["id"]
        cart = client.post(f"/api/carts/{cart_id}/items", json={"product_id": 1, "quantity": 2}).json()
        assert cart["items"][0]["quantity"] == 2
        cart = client.put(f"/api/carts/{cart_id}/items/1", json={"quantity": 3}).json()
        assert cart["items"][0]["quantity"] == 3

        customer = {
            "name": "Priya Sharma",
            "studentClass": "Class 8",
            "address": "12, MG Road, Bengaluru 560038",
            "email": "priya@example.com",
            "phone": "+91 98765 43210",
        }
        res = client.post("/api/orders", json={"cart_id": cart_id, "customer": customer})
        assert res.status_code == 201, res.text
        assert res.json()["total"] == 3 * 120

        after = next(p for p in client.get("/api/products").json() if p["id"] == 1)["stock"]
        assert after == before - 3
        assert client.get(f"/api/carts/{cart_id}").json()["items"] == []

        # Over-ordering is refused and nothing changes.
        client.post(f"/api/carts/{cart_id}/items", json={"product_id": 10, "quantity": 99})
        res = client.post("/api/orders", json={"cart_id": cart_id, "customer": customer})
        assert res.status_code == 409
        assert res.json()["detail"]["items"][0]["id"] == 10
