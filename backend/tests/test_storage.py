from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError, AzureError

from app import storage


@pytest.fixture
def blob_config(monkeypatch):
    storage._azure_service_client.cache_clear()
    for name, value in {
        "STORAGE_BACKEND": "azure",
        "AZURE_STORAGE_ACCOUNT_URL": "https://test.blob.core.windows.net",
        "AZURE_STORAGE_CONNECTION_STRING": "",
        "AZURE_STORAGE_CONTAINER": "products",
        "AZURE_CLIENT_ID": "",
        "AZURE_STORAGE_AUTO_CREATE_CONTAINER": False,
        "AZURE_BLOB_PUBLIC_URL": "",
        "AZURE_BLOB_PROXY_URL": "/api/files/images",
    }.items():
        monkeypatch.setattr(storage, name, value)
    yield
    storage._azure_service_client.cache_clear()


@pytest.mark.parametrize("client_id", ["", "assigned-identity-client-id"])
def test_identity_authentication_and_client_reuse(blob_config, monkeypatch, client_id):
    monkeypatch.setattr(storage, "AZURE_CLIENT_ID", client_id)
    # An old connection string must not override the requested managed identity.
    monkeypatch.setattr(storage, "AZURE_STORAGE_CONNECTION_STRING", "old-secret")
    credential_factory = MagicMock()
    service_factory = MagicMock()
    monkeypatch.setattr(storage, "DefaultAzureCredential", credential_factory)
    monkeypatch.setattr(storage, "BlobServiceClient", service_factory)

    first = storage._azure_container_client()
    assert storage._azure_container_client() is first
    credential_factory.assert_called_once_with(managed_identity_client_id=client_id or None)
    service_factory.assert_called_once_with(
        account_url="https://test.blob.core.windows.net",
        credential=credential_factory.return_value,
    )
    service_factory.from_connection_string.assert_not_called()
    service_factory.return_value.get_container_client.assert_called_with("products")


def test_connection_string_fallback(blob_config, monkeypatch):
    monkeypatch.setattr(storage, "AZURE_STORAGE_ACCOUNT_URL", "")
    monkeypatch.setattr(storage, "AZURE_STORAGE_CONNECTION_STRING", "test-connection")
    credential_factory = MagicMock()
    service_factory = MagicMock()
    monkeypatch.setattr(storage, "DefaultAzureCredential", credential_factory)
    monkeypatch.setattr(storage, "BlobServiceClient", service_factory)

    storage._azure_container_client()
    service_factory.from_connection_string.assert_called_once_with("test-connection")
    credential_factory.assert_not_called()


@pytest.mark.parametrize("setting", ["account", "container"])
def test_missing_configuration_has_clear_error(blob_config, monkeypatch, setting):
    if setting == "account":
        monkeypatch.setattr(storage, "AZURE_STORAGE_ACCOUNT_URL", "")
        message = "AZURE_STORAGE_ACCOUNT_URL"
    else:
        monkeypatch.setattr(storage, "AZURE_STORAGE_CONTAINER", "")
        message = "AZURE_STORAGE_CONTAINER"
    with pytest.raises(RuntimeError, match=message):
        storage._azure_container_client()


def test_upload_to_existing_private_container(blob_config, monkeypatch):
    container = MagicMock()
    monkeypatch.setattr(storage, "_azure_container_client", lambda: container)
    monkeypatch.setattr(storage.uuid, "uuid4", lambda: SimpleNamespace(hex="abc123"))

    url = storage.put_file(b"image-data", "image/png", ".png")
    assert url == "/api/files/images/products/abc123.png"
    container.create_container.assert_not_called()
    container.get_blob_client.assert_called_once_with("products/abc123.png")
    args, kwargs = container.get_blob_client.return_value.upload_blob.call_args
    assert args == (b"image-data",)
    assert kwargs["blob_type"] == "BlockBlob"
    assert kwargs["overwrite"] is False
    assert kwargs["content_settings"].content_type == "image/png"


@pytest.mark.parametrize("already_exists", [False, True])
def test_optional_container_creation(blob_config, monkeypatch, already_exists):
    monkeypatch.setattr(storage, "AZURE_STORAGE_AUTO_CREATE_CONTAINER", True)
    container = MagicMock()
    if already_exists:
        container.create_container.side_effect = ResourceExistsError("exists")
    monkeypatch.setattr(storage, "_azure_container_client", lambda: container)
    storage.put_file(b"image", "image/jpeg", ".jpg")
    container.create_container.assert_called_once_with()
    container.get_blob_client.return_value.upload_blob.assert_called_once()


@pytest.mark.parametrize("setting,base", [
    ("AZURE_BLOB_PUBLIC_URL", "https://cdn.example.com/products/"),
    ("AZURE_BLOB_PROXY_URL", "https://api.example.com/files/images/"),
])
def test_custom_image_delivery_urls(blob_config, monkeypatch, setting, base):
    monkeypatch.setattr(storage, setting, base)
    monkeypatch.setattr(storage, "_azure_container_client", MagicMock())
    monkeypatch.setattr(storage.uuid, "uuid4", lambda: SimpleNamespace(hex="abc123"))
    url = storage.put_file(b"image", "image/png", ".png")
    assert url == base.rstrip("/") + "/products/abc123.png"


def test_private_image_download(blob_config, monkeypatch):
    container = MagicMock()
    downloader = container.get_blob_client.return_value.download_blob.return_value
    downloader.chunks.return_value = iter([b"first", b"second"])
    downloader.properties.content_settings.content_type = "image/png"
    downloader.size = 11
    monkeypatch.setattr(storage, "_azure_container_client", lambda: container)

    chunks, content_type, size = storage.get_image("products/example.png")
    assert b"".join(chunks) == b"firstsecond"
    assert content_type == "image/png"
    assert size == 11
    container.get_blob_client.assert_called_once_with("products/example.png")
    container.create_container.assert_not_called()


@pytest.mark.parametrize("key", ["other/secret.png", "products/../secret.png", "products//file.png", "products/./file.png", "products/"])
def test_image_reads_stay_in_upload_namespace(blob_config, monkeypatch, key):
    container_factory = MagicMock()
    monkeypatch.setattr(storage, "_azure_container_client", container_factory)
    with pytest.raises(ValueError):
        storage.get_image(key)
    container_factory.assert_not_called()


def test_minio_uploads_still_use_existing_adapter(blob_config, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_BACKEND", "minio")
    uploader = MagicMock(return_value="http://localhost/uploads/example.png")
    monkeypatch.setattr(storage, "_put_minio_object", uploader)
    assert storage.put_file(b"image", "image/png", ".png") == uploader.return_value
    uploader.assert_called_once_with(b"image", "image/png", ".png")
    with pytest.raises(ValueError):
        storage.get_image("products/example.png")


def test_image_route_streams_without_browser_azure_credentials(client, monkeypatch):
    reader = MagicMock(return_value=(iter([b"first", b"second"]), "image/png", 11))
    monkeypatch.setattr(storage, "get_image", reader)
    response = client.get("/files/images/products/example.png")
    assert response.status_code == 200
    assert response.content == b"firstsecond"
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-length"] == "11"
    assert response.headers["x-content-type-options"] == "nosniff"
    reader.assert_called_once_with("products/example.png")


@pytest.mark.parametrize("error,status", [
    (ValueError("invalid key"), 404),
    (ResourceNotFoundError("missing blob"), 404),
    (AzureError("storage failure"), 503),
    (RuntimeError("missing configuration"), 503),
])
def test_image_route_handles_missing_blobs_and_storage_failures(client, monkeypatch, error, status):
    monkeypatch.setattr(storage, "get_image", MagicMock(side_effect=error))
    response = client.get("/files/images/products/example.png")
    assert response.status_code == status
    assert str(error) not in response.text


def test_upload_url_resolves_to_image_route(client, login_user, blob_config, monkeypatch):
    token = login_user("alice@example.com")
    container = MagicMock()
    monkeypatch.setattr(storage, "_azure_container_client", lambda: container)
    download = container.get_blob_client.return_value.download_blob.return_value
    download.chunks.return_value = iter([b"image-data"])
    download.properties.content_settings.content_type = "image/png"
    download.size = 10

    response = client.post(
        "/files/upload",
        files={"file": ("test.png", b"image-data", "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    url = response.json()["url"]
    assert url.startswith("/api/files/images/products/")
    # Nginx strips /api/ before forwarding to FastAPI.
    image = client.get(url.removeprefix("/api"))
    assert image.status_code == 200
    assert image.content == b"image-data"
