# backend/tests/conftest.py
import sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

# đảm bảo import được app
sys.path.append("/app")  # phòng khi PYTHONPATH chưa set

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

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

# ✅ Fixture mặc định bạn đang thiếu
@pytest.fixture
def user_data():
    return {"email": "alice@example.com", "password": "secret123"}

# ✅ Nếu bài test nào có dùng other_user_data thì mới cần cái này
@pytest.fixture
def other_user_data():
    return {"email": "bob@example.com", "password": "secret456"}
