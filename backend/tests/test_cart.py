def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def login_or_register(client, email, password):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post(
        "/auth/login", data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return response.json()["access_token"]

def test_cart_and_checkout(client, monkeypatch):
    sent_tokens = []
    monkeypatch.setattr("app.email_service.send_order_confirmation", lambda _email, _order_id, token: sent_tokens.append(token))
    token = login_or_register(client, "shopper@example.com", "secret123")
    admin_token = login_or_register(client, "alice@example.com", "secret123")
    product = client.post(
        "/products/", json={"name": "Cart test product", "price": 12.5}, headers=auth_header(admin_token)
    ).json()

    response = client.post("/cart/items", json={"product_id": product["id"], "quantity": 2}, headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["total"] == 25.0

    response = client.put(f"/cart/items/{product['id']}", json={"quantity": 3}, headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 3

    response = client.post("/cart/checkout", json={
        "customer_name": "Test Shopper", "phone": "+1 555 0100", "delivery_address": "123 Test Street"
    }, headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["total"] == 37.5
    assert response.json()["items"][0]["product_name"] == "Cart test product"
    assert response.json()["delivery_address"] == "123 Test Street"
    assert response.json()["status"] == "pending_confirmation"

    response = client.post("/orders/confirm", json={"token": sent_tokens[0]})
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert client.get("/cart", headers=auth_header(token)).json()["items"] == []
    assert len(client.get("/orders/mine", headers=auth_header(token)).json()) == 1
