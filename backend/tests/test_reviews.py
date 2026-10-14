from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from sqlalchemy.exc import IntegrityError

from app import models, reviews, storage
from conftest import TestingSessionLocal

PNG = b"\x89PNG\r\n\x1a\n" + b"photo-data"
MP4 = b"\x00\x00\x00\x18ftypisom" + b"video-data"


@pytest.fixture
def purchase(client, login_user):
    buyer = login_user("review-buyer@example.com", name="Review Buyer")
    other = login_user("review-other@example.com")
    admin = login_user("alice@example.com")
    db = TestingSessionLocal()
    try:
        user = db.query(models.User).filter_by(email="review-buyer@example.com").one()
        owner = db.query(models.User).filter_by(email="alice@example.com").one()
        product = models.Product(name="Review product", price=10, stock=5, owner_id=owner.id)
        unrelated = models.Product(name="Other product", price=20, stock=5, owner_id=owner.id)
        db.add_all([product, unrelated]); db.flush()
        order = models.Order(user_id=user.id, total=10, customer_name=user.name,
                             phone="0900111222", delivery_address="1 Test Street", status="delivered")
        order.items.append(models.OrderItem(product_id=product.id, product_name=product.name, unit_price=10, quantity=1))
        db.add(order); db.commit()
        return dict(product_id=product.id, other_product_id=unrelated.id, order_id=order.id,
                    headers={"Authorization": f"Bearer {buyer}"}, other_headers={"Authorization": f"Bearer {other}"},
                    admin_headers={"Authorization": f"Bearer {admin}"})
    finally:
        db.close()


def submit(client, purchase, files=None, **changes):
    data = dict(order_id=purchase["order_id"], rating=5, comment="Lovely quality and packaging")
    data.update(changes)
    return client.post(f'/products/{purchase["product_id"]}/reviews', data=data, files=files, headers=purchase["headers"])


def test_text_review_is_public_and_order_marks_it_reviewed(client, purchase):
    pid = purchase["product_id"]
    eligibility = client.get(f"/products/{pid}/review-eligibility", headers=purchase["headers"]).json()
    assert eligibility["eligible_orders"][0]["order_id"] == purchase["order_id"]
    response = submit(client, purchase, comment="  Excellent product  ")
    assert response.status_code == 201, response.text
    assert response.json()["comment"] == "Excellent product"
    assert response.json()["author_name"] == "Review Buyer"
    assert response.json()["verified_purchase"] is True
    assert response.json()["media"] == []
    assert "email" not in response.json()
    page = client.get(f"/products/{pid}/reviews").json()
    assert page["total"] == 1 and page["average_rating"] == 5.0
    assert page["items"][0]["id"] == response.json()["id"]
    assert client.get(f"/products/{pid}/review-eligibility", headers=purchase["headers"]).json()["eligible_orders"] == []
    assert client.get("/orders/mine", headers=purchase["headers"]).json()[0]["items"][0]["reviewed"] is True
    assert submit(client, purchase).status_code == 409


@pytest.mark.parametrize("status", ["pending_confirmation", "confirmed", "preparing", "shipping", "cancelled"])
def test_cannot_review_before_delivery_or_after_cancellation(client, purchase, status):
    with TestingSessionLocal() as db:
        db.get(models.Order, purchase["order_id"]).status = status
        db.commit()
    assert submit(client, purchase).status_code == 403
    result = client.get(f'/products/{purchase["product_id"]}/review-eligibility', headers=purchase["headers"])
    assert result.json()["eligible_orders"] == []


def test_order_ownership_product_membership_and_authentication(client, purchase):
    assert submit(client, dict(purchase, headers=purchase["other_headers"])).status_code == 404
    assert submit(client, dict(purchase, product_id=purchase["other_product_id"])).status_code == 403
    assert submit(client, dict(purchase, headers=purchase["admin_headers"])).status_code == 403
    assert submit(client, dict(purchase, headers={})).status_code == 401


@pytest.mark.parametrize("changes", [{"rating": 0}, {"rating": 6}, {"rating": 2.5}, {"comment": "   "}, {"comment": "a" * 3001}])
def test_review_fields_are_validated(client, purchase, changes):
    assert submit(client, purchase, **changes).status_code == 422


def test_photos_and_unboxing_videos_go_to_azure_when_configured(client, purchase, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_BACKEND", "azure")
    monkeypatch.setattr(storage, "AZURE_BLOB_PUBLIC_URL", "")
    monkeypatch.setattr(storage, "AZURE_BLOB_PROXY_URL", "/api/files/images")
    container = MagicMock()
    monkeypatch.setattr(storage, "_azure_container_client", lambda: container)
    minio = MagicMock()
    monkeypatch.setattr(storage, "_put_minio_object", minio)
    response = submit(client, purchase, files=[
        ("files", ("untrusted-filename.html", PNG, "image/png")),
        ("files", ("unboxing.mp4", MP4, "video/mp4")),
    ])
    assert response.status_code == 201, response.text
    media = response.json()["media"]
    assert [item["kind"] for item in media] == ["image", "video"]
    assert media[0]["url"].startswith("/api/files/images/reviews/images/") and media[0]["url"].endswith(".png")
    assert media[1]["url"].startswith("/api/files/images/reviews/videos/") and media[1]["url"].endswith(".mp4")
    assert container.get_blob_client.call_count == 2
    assert container.get_blob_client.call_args_list[0].args[0].startswith("reviews/images/")
    assert container.get_blob_client.call_args_list[1].args[0].startswith("reviews/videos/")
    assert container.get_blob_client.return_value.upload_blob.call_args.kwargs["content_settings"].content_type == "video/mp4"
    minio.assert_not_called()
    with TestingSessionLocal() as db:
        assert db.query(models.ReviewMedia).count() == 2


def test_local_review_media_uses_minio_without_azure_credentials(client, purchase, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_BACKEND", "minio")
    monkeypatch.setattr(storage, "MINIO_BUCKET", "uploads")
    monkeypatch.setattr(storage, "MINIO_PUBLIC_URL", "http://localhost/uploads")
    monkeypatch.setattr(storage, "AZURE_STORAGE_ACCOUNT_URL", "")
    monkeypatch.setattr(storage, "AZURE_STORAGE_CONNECTION_STRING", "")
    minio = MagicMock()
    monkeypatch.setattr(storage, "_minio_client", lambda: minio)
    azure = MagicMock()
    monkeypatch.setattr(storage, "_azure_container_client", azure)
    response = submit(client, purchase, files=[
        ("files", ("photo.png", PNG, "image/png")),
        ("files", ("unboxing.mp4", MP4, "video/mp4")),
    ])
    assert response.status_code == 201, response.text
    media = response.json()["media"]
    assert [item["kind"] for item in media] == ["image", "video"]
    assert media[0]["url"].startswith("http://localhost/uploads/reviews/images/")
    assert media[1]["url"].startswith("http://localhost/uploads/reviews/videos/")
    writes = minio.put_object.call_args_list
    assert len(writes) == 2
    assert [call.kwargs["Body"] for call in writes] == [PNG, MP4]
    assert [call.kwargs["ContentType"] for call in writes] == ["image/png", "video/mp4"]
    assert all(call.kwargs["Bucket"] == "uploads" and call.kwargs["Key"].startswith("reviews/") for call in writes)
    assert writes[0].kwargs["Key"].startswith("reviews/images/")
    assert writes[1].kwargs["Key"].startswith("reviews/videos/")
    azure.assert_not_called()


@pytest.mark.parametrize("filename,data,content_type,status", [
    ("bad.svg", b"<svg />", "image/svg+xml", 400),
    ("fake.png", b"<script>alert(1)</script>", "image/png", 400),
    ("empty.mp4", b"", "video/mp4", 400),
    ("large.png", b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024), "image/png", 413),
], ids=["svg", "spoofed", "empty", "too-large"])
def test_invalid_media_is_rejected_before_blob_writes(client, purchase, monkeypatch, filename, data, content_type, status):
    uploader = MagicMock()
    monkeypatch.setattr(storage, "put_review_file", uploader)
    response = submit(client, purchase, files=[("files", (filename, data, content_type))])
    assert response.status_code == status, response.text
    uploader.assert_not_called()
    with TestingSessionLocal() as db:
        assert db.query(models.ProductReview).count() == 0


def test_attachment_count_limit(client, purchase, monkeypatch):
    uploader = MagicMock()
    monkeypatch.setattr(storage, "put_review_file", uploader)
    assert submit(client, purchase, files=[("files", ("photo.png", PNG, "image/png"))] * 7).status_code == 400
    uploader.assert_not_called()


def test_total_attachment_limit_is_checked_before_blob_writes(client, purchase, monkeypatch):
    monkeypatch.setattr(reviews, "TOTAL_LIMIT", len(MP4) + 1)
    uploader = MagicMock()
    monkeypatch.setattr(storage, "put_review_file", uploader)
    assert submit(client, purchase, files=[("files", ("unboxing.mp4", MP4, "video/mp4"))] * 2).status_code == 413
    uploader.assert_not_called()


def test_a_later_delivered_purchase_can_have_its_own_review(client, purchase):
    assert submit(client, purchase, rating=5).status_code == 201
    with TestingSessionLocal() as db:
        original = db.get(models.Order, purchase["order_id"])
        repeat = models.Order(user_id=original.user_id, total=10, customer_name=original.customer_name,
                              phone=original.phone, delivery_address=original.delivery_address, status="delivered")
        repeat.items.append(models.OrderItem(product_id=purchase["product_id"], product_name="Review product", unit_price=10, quantity=1))
        db.add(repeat); db.commit()
        repeat_id = repeat.id
    assert submit(client, purchase, order_id=repeat_id, rating=4).status_code == 201
    page = client.get(f'/products/{purchase["product_id"]}/reviews?limit=1').json()
    assert page["total"] == 2 and page["average_rating"] == 4.5
    assert len(page["items"]) == 1
    next_page = client.get(f'/products/{purchase["product_id"]}/reviews?limit=1&skip=1').json()
    assert next_page["items"][0]["id"] != page["items"][0]["id"]


def test_failed_upload_rolls_back_review_and_cleans_up_prior_blob(client, purchase, monkeypatch):
    key = "reviews/" + "a" * 32 + ".png"
    uploader = MagicMock(side_effect=[(key, "/api/files/images/" + key), RuntimeError("private storage details")])
    cleanup = MagicMock()
    monkeypatch.setattr(storage, "put_review_file", uploader)
    monkeypatch.setattr(storage, "delete_review_file", cleanup)
    response = submit(client, purchase, files=[("files", ("photo.png", PNG, "image/png"))] * 2)
    assert response.status_code == 503 and "private storage details" not in response.text
    cleanup.assert_called_once_with(key)
    with TestingSessionLocal() as db:
        assert db.query(models.ProductReview).count() == 0
        assert db.query(models.ReviewMedia).count() == 0
    # A failed attempt does not consume the customer's right to review.
    assert submit(client, purchase).status_code == 201


def test_missing_blob_configuration_allows_retry_without_attachments(client, purchase, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_BACKEND", "azure")
    monkeypatch.setattr(storage, "AZURE_STORAGE_ACCOUNT_URL", "")
    monkeypatch.setattr(storage, "AZURE_STORAGE_CONNECTION_STRING", "")
    storage._azure_service_client.cache_clear()
    try:
        response = submit(client, purchase, files=[("files", ("photo.png", PNG, "image/png"))])
        assert response.status_code == 503
        assert "Remove the attachments" in response.json()["detail"]
        assert "AZURE_STORAGE" not in response.text
        with TestingSessionLocal() as db:
            assert db.query(models.ProductReview).count() == 0
            assert db.query(models.ReviewMedia).count() == 0
        response = submit(client, purchase)
        assert response.status_code == 201, response.text
        assert response.json()["media"] == []
    finally:
        storage._azure_service_client.cache_clear()


def test_database_enforces_one_review_per_order_product(purchase):
    with TestingSessionLocal() as db:
        order = db.get(models.Order, purchase["order_id"])
        for _ in range(2):
            db.add(models.ProductReview(order_id=order.id, product_id=purchase["product_id"], user_id=order.user_id,
                                       author_name="Buyer", rating=5, comment="Review"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


@pytest.mark.parametrize("folder", ["", "videos/"])
@pytest.mark.parametrize("range_header,start,end", [(None, 0, 99), ("bytes=10-19", 10, 19), ("bytes=90-", 90, 99), ("bytes=-5", 95, 99), ("bytes=0-200", 0, 99)])
def test_private_blob_video_stream_supports_ranges(client, monkeypatch, range_header, start, end, folder):
    monkeypatch.setattr(storage, "STORAGE_BACKEND", "azure")
    container = MagicMock()
    blob = container.get_blob_client.return_value
    blob.get_blob_properties.return_value = SimpleNamespace(size=100, content_settings=SimpleNamespace(content_type="video/mp4"))
    blob.download_blob.return_value.chunks.return_value = iter([b"v" * (end - start + 1)])
    monkeypatch.setattr(storage, "_azure_container_client", lambda: container)
    key = "reviews/" + folder + "a" * 32 + ".mp4"
    response = client.get("/files/images/" + key, headers={"Range": range_header} if range_header else {})
    assert response.status_code == (206 if range_header else 200)
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers["accept-ranges"] == "bytes"
    assert len(response.content) == end - start + 1
    if range_header:
        assert response.headers["content-range"] == f"bytes {start}-{end}/100"
        blob.download_blob.assert_called_once_with(offset=start, length=end - start + 1)
    else:
        blob.download_blob.assert_called_once_with()


@pytest.mark.parametrize("range_header", ["bytes=100-", "bytes=20-10", "bytes=-0", "bytes=0-1,5-6", "invalid", "bytes=-"])
def test_invalid_media_range_returns_416(client, monkeypatch, range_header):
    monkeypatch.setattr(storage, "STORAGE_BACKEND", "azure")
    container = MagicMock()
    container.get_blob_client.return_value.get_blob_properties.return_value = SimpleNamespace(size=100, content_settings=SimpleNamespace(content_type="video/mp4"))
    monkeypatch.setattr(storage, "_azure_container_client", lambda: container)
    response = client.get("/files/images/reviews/" + "a" * 32 + ".mp4", headers={"Range": range_header})
    assert response.status_code == 416
    assert response.headers["content-range"] == "bytes */100"
    container.get_blob_client.return_value.download_blob.assert_not_called()


@pytest.mark.parametrize("folder", ["", "videos/"])
@pytest.mark.parametrize("range_header,start,end", [(None, 0, 99), ("bytes=10-19", 10, 19), ("bytes=90-", 90, 99), ("bytes=-5", 95, 99), ("bytes=0-200", 0, 99)])
def test_minio_video_stream_supports_ranges(client, monkeypatch, range_header, start, end, folder):
    monkeypatch.setattr(storage, "STORAGE_BACKEND", "minio")
    monkeypatch.setattr(storage, "MINIO_BUCKET", "uploads")
    minio = MagicMock()
    minio.head_object.return_value = {"ContentLength": 100, "ContentType": "video/mp4"}
    body = minio.get_object.return_value["Body"]
    body.iter_chunks.return_value = iter([b"v" * (end - start + 1)])
    monkeypatch.setattr(storage, "_minio_client", lambda: minio)
    key = "reviews/" + folder + "a" * 32 + ".mp4"
    response = client.get("/files/images/" + key, headers={"Range": range_header} if range_header else {})
    assert response.status_code == (206 if range_header else 200)
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers["accept-ranges"] == "bytes"
    assert len(response.content) == end - start + 1
    options = {"Range": f"bytes={start}-{end}"} if range_header else {}
    minio.get_object.assert_called_once_with(Bucket="uploads", Key=key, **options)
    body.close.assert_called_once()
    if range_header:
        assert response.headers["content-range"] == f"bytes {start}-{end}/100"


@pytest.mark.parametrize("range_header", ["bytes=100-", "bytes=20-10", "bytes=-0", "bytes=0-1,5-6", "invalid", "bytes=-"])
def test_invalid_minio_media_range_returns_416(client, monkeypatch, range_header):
    monkeypatch.setattr(storage, "STORAGE_BACKEND", "minio")
    minio = MagicMock()
    minio.head_object.return_value = {"ContentLength": 100}
    monkeypatch.setattr(storage, "_minio_client", lambda: minio)
    response = client.get("/files/images/reviews/" + "a" * 32 + ".mp4", headers={"Range": range_header})
    assert response.status_code == 416
    assert response.headers["content-range"] == "bytes */100"
    minio.get_object.assert_not_called()


@pytest.mark.parametrize("error,status", [
    (ClientError({"Error": {"Code": "404"}}, "HeadObject"), 404),
    (ClientError({"Error": {"Code": "NoSuchKey"}}, "HeadObject"), 404),
    (ClientError({"Error": {"Code": "AccessDenied"}}, "HeadObject"), 503),
    (EndpointConnectionError(endpoint_url="http://private-minio:9000"), 503),
])
def test_minio_media_read_failures_are_handled(client, monkeypatch, error, status):
    monkeypatch.setattr(storage, "STORAGE_BACKEND", "minio")
    minio = MagicMock()
    minio.head_object.side_effect = error
    monkeypatch.setattr(storage, "_minio_client", lambda: minio)
    response = client.get("/files/images/reviews/" + "a" * 32 + ".mp4")
    assert response.status_code == status
    assert "private-minio" not in response.text


@pytest.mark.parametrize("backend", ["azure", "minio"])
@pytest.mark.parametrize("path,ext", [("", ".png"), ("images/", ".png"), ("videos/", ".mp4")])
def test_failed_review_cleanup_uses_configured_backend(monkeypatch, backend, path, ext):
    monkeypatch.setattr(storage, "STORAGE_BACKEND", backend)
    monkeypatch.setattr(storage, "MINIO_BUCKET", "uploads")
    minio, azure = MagicMock(), MagicMock()
    monkeypatch.setattr(storage, "_minio_client", lambda: minio)
    monkeypatch.setattr(storage, "_azure_container_client", lambda: azure)
    key = "reviews/" + path + "a" * 32 + ext
    storage.delete_review_file(key)
    if backend == "minio":
        minio.delete_object.assert_called_once_with(Bucket="uploads", Key=key)
        azure.get_blob_client.assert_not_called()
    else:
        azure.get_blob_client.assert_called_once_with(key)
        azure.get_blob_client.return_value.delete_blob.assert_called_once()
        minio.delete_object.assert_not_called()


@pytest.mark.parametrize("key", [
    "reviews/secret.txt", "reviews/images/../secret.png", "reviews/videos/../../secret.mp4",
    "reviews/images/" + "a" * 32 + ".mp4", "reviews/videos/" + "a" * 32 + ".png",
])
def test_review_media_cannot_read_arbitrary_blob_keys(client, monkeypatch, key):
    container = MagicMock()
    monkeypatch.setattr(storage, "_azure_container_client", container)
    response = client.get("/files/images/" + key)
    assert response.status_code == 404
    container.assert_not_called()
