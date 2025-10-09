# backend/tests/test_basic.py
API_REGISTER = "/auth/register"
API_LOGIN = "/auth/login"
API_PRODUCTS = "/products/"

def test_register_login_and_create_product(client):
    # 1) Đăng ký
    user = {"email": "alice@example.com", "password": "secret123"}
    r = client.post(API_REGISTER, json=user)
    assert r.status_code in (200, 400)  # 400 nếu đã chạy test trước đó

    # 2) Đăng nhập
    form = {"username": user["email"], "password": user["password"]}
    r = client.post(API_LOGIN, data=form, headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3) Tạo sản phẩm
    product = {"name": "Test Product", "price": 9.99, "image_url": None, "description": "demo"}
    r = client.post(API_PRODUCTS, json=product, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "Test Product"
    assert float(data["price"]) == 9.99
