import time
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import crud, models, security
from conftest import TestingSessionLocal


def registration(email="new@example.com", **overrides):
    return {"name": "New User", "email": email, "password": "secret123", **overrides}


def users():
    with TestingSessionLocal() as db:
        return db.query(models.User).all()


@pytest.mark.parametrize("email", ["new@example.com", "alice@example.com"])
def test_registration_saves_nothing_until_confirmation(client, verification_emails, email):
    details = registration(email)
    response = client.post("/auth/register", json=details)
    assert response.status_code == 200, response.text
    assert response.json()["email_verified"] is False
    assert "id" not in response.json()
    assert users() == []
    assert verification_emails[-1][0] == email

    login = client.post("/auth/login", data={"username": email, "password": details["password"]})
    assert login.status_code == 400
    assert users() == []

    token = verification_emails[-1][1]
    response = client.post("/auth/verify-email", json={"token": token})
    assert response.status_code == 200, response.text
    assert response.json()["email_verified"] is True
    assert response.json()["is_admin"] is (email == "alice@example.com")
    saved = users()
    assert len(saved) == 1
    assert saved[0].name == details["name"]
    assert security.verify_password(details["password"], saved[0].hashed_password)
    assert saved[0].email_verification_token is None
    assert client.post("/auth/login", data={"username": email, "password": details["password"]}).status_code == 200

    assert client.post("/auth/verify-email", json={"token": token}).status_code == 404
    assert len(users()) == 1


@pytest.mark.parametrize("error", [RuntimeError("Email is not configured"), OSError("SMTP unavailable")])
@pytest.mark.parametrize("email", ["new@example.com", "alice@example.com"])
def test_email_failure_creates_no_account_and_allows_retry(client, monkeypatch, verification_emails, error, email):
    def fail(*_args):
        raise error

    with monkeypatch.context() as patch:
        patch.setattr("app.email_service.send_account_verification", fail)
        response = client.post("/auth/register", json=registration(email))
    assert response.status_code == 503
    assert users() == []
    assert verification_emails == []
    assert client.post("/auth/register", json=registration(email)).status_code == 200
    assert users() == []
    assert client.post("/auth/verify-email", json={"token": verification_emails[-1][1]}).status_code == 200


@pytest.mark.parametrize("overrides", [{"email": "bad-email"}, {"name": "   "}, {"password": ""}, {"name": ""}])
def test_invalid_registration_saves_nothing(client, verification_emails, overrides):
    assert client.post("/auth/register", json=registration(**overrides)).status_code == 422
    assert users() == []
    assert verification_emails == []


def test_invalid_expired_and_tampered_links_create_no_account(client, verification_emails):
    client.post("/auth/register", json=registration())
    token = verification_emails[-1][1]
    encrypted = token[len(security.REGISTRATION_TOKEN_PREFIX):].encode()
    cipher = security._registration_cipher()
    expired = security.REGISTRATION_TOKEN_PREFIX + cipher.encrypt_at_time(
        cipher.decrypt(encrypted), int(time.time()) - security.REGISTRATION_TOKEN_TTL - 1,
    ).decode()
    tampered = token[:-10] + ("A" if token[-10] != "A" else "B") + token[-9:]

    for invalid in ["invalid-token-that-is-long-enough", tampered, security.create_access_token({"sub": "new@example.com"})]:
        response = client.post("/auth/verify-email", json={"token": invalid})
        assert response.status_code == 404
        assert users() == []
    response = client.post("/auth/verify-email", json={"token": expired})
    assert response.status_code == 400
    assert response.json()["detail"] == "Verification link has expired"
    assert users() == []


def test_pending_details_are_encrypted_and_contain_only_password_hash(client, verification_emails):
    details = registration()
    client.post("/auth/register", json=details)
    token = verification_emails[-1][1]
    assert all(details[field] not in token for field in ("name", "email", "password"))
    payload, error = security.decode_registration_token(token)
    assert error is None
    assert set(payload) == {"name", "email", "hashed_password"}
    assert security.verify_password(details["password"], payload["hashed_password"])
    assert users() == []


def test_unconfirmed_retry_does_not_overwrite_confirmed_account(client, verification_emails):
    client.post("/auth/register", json=registration("New@EXAMPLE.COM"))
    first = verification_emails[-1][1]
    client.post("/auth/register", json=registration(name="Updated User", password="updated-password"))
    second = verification_emails[-1][1]
    assert users() == []
    assert client.post("/auth/verify-email", json={"token": second}).status_code == 200
    assert client.post("/auth/verify-email", json={"token": first}).status_code == 404
    assert client.post("/auth/register", json=registration()).status_code == 400
    assert len(verification_emails) == 2
    saved = users()
    assert len(saved) == 1
    assert saved[0].name == "Updated User"
    assert security.verify_password("updated-password", saved[0].hashed_password)


def test_confirmation_database_failure_rolls_back_account_and_admin_changes(client, verification_emails, monkeypatch):
    with TestingSessionLocal() as db:
        old_admin = crud.create_verified_user(db, "Old Admin", "old@example.com", security.get_password_hash("old-password"), is_admin=True)
        old_admin_id = old_admin.id
    client.post("/auth/register", json=registration("alice@example.com"))
    assert len(users()) == 1
    assert users()[0].is_admin is True

    with TestingSessionLocal() as db:
        def fail_commit():
            raise SQLAlchemyError("Database unavailable")

        with monkeypatch.context() as patch:
            patch.setattr(db, "commit", fail_commit)
            with pytest.raises(SQLAlchemyError):
                crud.verify_user_email(db, verification_emails[-1][1])
        assert db.query(models.User).count() == 1
        assert db.get(models.User, old_admin_id).is_admin is True

    assert client.post("/auth/verify-email", json={"token": verification_emails[-1][1]}).status_code == 200
    with TestingSessionLocal() as db:
        assert db.get(models.User, old_admin_id).is_admin is False


def test_duplicate_confirmation_race_rolls_back(client, verification_emails, monkeypatch):
    client.post("/auth/register", json=registration())
    token = verification_emails[-1][1]
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
    # Simulate a second request that read the email before the first committed.
    with monkeypatch.context() as patch:
        patch.setattr(crud, "get_user_by_email", lambda *_args: None)
        assert client.post("/auth/verify-email", json={"token": token}).status_code == 404
    assert len(users()) == 1


def test_previously_issued_link_still_verifies_existing_account(client):
    token = "previous-verification-link-token"
    with TestingSessionLocal() as db:
        db.add(models.User(
            name="Legacy User", email="legacy@example.com",
            hashed_password=security.get_password_hash("secret123"), email_verified=False,
            email_verification_token=token,
            email_verification_expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ))
        db.commit()
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
    assert len(users()) == 1
    assert users()[0].email_verified is True
