def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def test_create_product_requires_auth(client):
    """Không có token thì không tạo được sản phẩm"""
    r = client.post(
        "/products/",
        json={"name": "P1", "price": 9.9, "image_url": None, "description": "demo"},
    )
    assert r.status_code == 401

def test_create_edit_delete_product_simple(client, user_data):
    """Tạo, sửa, xóa sản phẩm với chính user đó (không test ownership phức tạp)"""

    # Đăng nhập hoặc đăng ký nếu chưa có
    r = client.post(
        "/auth/login",
        data={"username": user_data["email"], "password": user_data["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if r.status_code != 200:
        client.post("/auth/register", json=user_data)
        r = client.post(
            "/auth/login",
            data={"username": user_data["email"], "password": user_data["password"]},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    token = r.json()["access_token"]

    # Tạo sản phẩm
    body = {"name": "Book", "price": 19.99, "image_url": None, "description": "Novel"}
    r = client.post("/products/", json=body, headers=auth_header(token))
    assert r.status_code == 200
    pid = r.json()["id"]

    # Sửa sản phẩm
    upd = {"name": "Book Deluxe", "price": 25.99, "image_url": None, "description": "Upgraded"}
    r = client.put(f"/products/{pid}", json=upd, headers=auth_header(token))
    assert r.status_code == 200
    assert r.json()["name"] == "Book Deluxe"

    # Xóa sản phẩm
    r = client.delete(f"/products/{pid}", headers=auth_header(token))
    assert r.status_code == 200
