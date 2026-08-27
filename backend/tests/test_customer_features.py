from app import models
from conftest import TestingSessionLocal


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_profile_is_saved_and_returned(client, login_user):
    token = login_user("profile@example.com", name="Profile Customer")
    response = client.put("/profile", json={
        "phone": "+84 900 111 222", "delivery_address": "12 Nguyen Hue, Ho Chi Minh City",
    }, headers=headers(token))
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Profile Customer"

    response = client.get("/profile", headers=headers(token))
    assert response.status_code == 200
    assert response.json()["phone"] == "+84 900 111 222"
    assert response.json()["delivery_address"] == "12 Nguyen Hue, Ho Chi Minh City"


def test_inventory_and_admin_order_progression(client, login_user, monkeypatch):
    confirmation_tokens = []
    monkeypatch.setattr(
        "app.email_service.send_order_confirmation",
        lambda _email, _order_id, token: confirmation_tokens.append(token),
    )
    customer_token = login_user("buyer@example.com", name="Buyer")
    admin_token = login_user("alice@example.com", name="Admin")
    product = client.post("/products/", json={
        "name": "Tracked product", "price": 15, "stock": 3,
    }, headers=headers(admin_token)).json()

    assert client.post("/cart/items", json={"product_id": product["id"], "quantity": 2}, headers=headers(customer_token)).status_code == 200
    order = client.post("/cart/checkout", json={
        "customer_name": "Buyer", "phone": "0900111222", "delivery_address": "1 Test Street",
    }, headers=headers(customer_token))
    assert order.status_code == 200
    order_id = order.json()["id"]
    assert client.post("/orders/confirm", json={"token": confirmation_tokens[0]}).json()["status"] == "confirmed"

    # The API allows only the immediate next state, never a skipped stage.
    skipped = client.put(f"/orders/{order_id}/status", json={"status": "delivered"}, headers=headers(admin_token))
    assert skipped.status_code == 400
    for status in ("preparing", "shipping", "delivered"):
        response = client.put(f"/orders/{order_id}/status", json={"status": status}, headers=headers(admin_token))
        assert response.status_code == 200, response.text
        assert response.json()["status"] == status

    db = TestingSessionLocal()
    try:
        assert db.get(models.Product, product["id"]).stock == 1
    finally:
        db.close()


def test_chat_unread_read_and_image_validation(client, login_user):
    customer_token = login_user("chat-customer@example.com", name="Chat Customer")
    admin_token = login_user("alice@example.com", name="Admin")

    sent = client.post("/chat/messages", json={"body": "Need help with my order"}, headers=headers(customer_token))
    assert sent.status_code == 200, sent.text
    assert client.get("/chat/unread", headers=headers(admin_token)).json()["unread_count"] == 1

    conversations = client.get("/chat/conversations", headers=headers(admin_token)).json()
    assert conversations[0]["customer_email"] == "chat-customer@example.com"
    assert conversations[0]["unread_count"] == 1
    customer_id = conversations[0]["customer_id"]
    assert client.post(f"/chat/read?customer_id={customer_id}", headers=headers(admin_token)).status_code == 200
    assert client.get("/chat/unread", headers=headers(admin_token)).json()["unread_count"] == 0

    reply = client.post("/chat/messages", json={
        "body": "We are checking it now", "customer_id": customer_id,
    }, headers=headers(admin_token))
    assert reply.status_code == 200, reply.text
    assert client.get("/chat/unread", headers=headers(customer_token)).json()["unread_count"] == 1

    invalid_upload = client.post("/chat/files/upload", files={
        "file": ("note.txt", b"not an image", "text/plain"),
    }, headers=headers(customer_token))
    assert invalid_upload.status_code == 400
