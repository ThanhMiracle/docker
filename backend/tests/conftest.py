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
def reset_database():
    """Keep every test independent."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture(autouse=True)
def verification_emails(monkeypatch):
    """Capture confirmation links without sending real email."""
    sent = []
    monkeypatch.setattr(
        "app.email_service.send_account_verification",
        lambda email, token: sent.append((email, token)),
    )
    return sent


@pytest.fixture
def login_user(client, verification_emails):
    def _login(email, password="secret123", name="Test User"):
        response = client.post("/auth/register", json={
            "name": name, "email": email, "password": password,
        })
        assert response.status_code == 200, response.text
        if not response.json()["email_verified"]:
            response = client.post("/auth/verify-email", json={
                "token": verification_emails[-1][1],
            })
            assert response.status_code == 200, response.text
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
