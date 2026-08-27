# backend/tests/conftest.py
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

# đảm bảo import được app
sys.path.append("/app")  # phòng khi PYTHONPATH chưa set
os.environ.setdefault("ADMIN_EMAIL", "alice@example.com")

from app.main import app
from app.database import Base, get_db
from app import models

# SQLite in-memory dùng chung 1 connection cho toàn bộ test session
engine = create_engine(
    "sqlite://",  # chú ý: không dùng sqlite:///:memory:
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # giữ nguyên 1 connection => không mất bảng
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# tạo bảng 1 lần
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# override dependency DB
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def reset_database(monkeypatch):
    """Keep every test independent and avoid sending real email."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(
        "app.email_service.send_account_verification", lambda *_args, **_kwargs: None
    )
    yield

@pytest.fixture
def login_user(client):
    def _login(email, password="secret123", name="Test User", verified=True):
        response = client.post("/auth/register", json={
            "name": name, "email": email, "password": password,
        })
        assert response.status_code == 200, response.text
        if verified:
            db = TestingSessionLocal()
            try:
                user = db.query(models.User).filter(models.User.email == email).first()
                user.email_verified = True
                db.commit()
            finally:
                db.close()
        response = client.post(
            "/auth/login", data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]
    return _login

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

# ✅ Fixture mặc định bạn đang thiếu
@pytest.fixture
def user_data():
    return {"name": "Alice", "email": "alice@example.com", "password": "secret123"}

# ✅ Nếu bài test nào có dùng other_user_data thì mới cần cái này
@pytest.fixture
def other_user_data():
    return {"name": "Bob", "email": "bob@example.com", "password": "secret456"}
