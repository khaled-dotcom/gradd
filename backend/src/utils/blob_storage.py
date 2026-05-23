"""Azure Blob Storage helpers (optional — falls back to local disk)."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import BinaryIO, Optional, Union

from backend.src.config import settings

_blob_service = None


def blob_enabled() -> bool:
    return bool(settings.AZURE_STORAGE_CONNECTION_STRING)


def _client():
    global _blob_service
    if _blob_service is None:
        from azure.storage.blob import BlobServiceClient

        _blob_service = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
    return _blob_service


def _container() -> str:
    return settings.AZURE_STORAGE_CONTAINER or "empowerwork"


def upload_file(
    blob_path: str,
    data: Union[bytes, BinaryIO],
    content_type: Optional[str] = None,
) -> str:
    if not blob_enabled():
        return ""

    client = _client()
    blob_client = client.get_blob_client(container=_container(), blob=blob_path)
    if isinstance(data, bytes):
        body = data
    else:
        body = data.read()

    ct = content_type or mimetypes.guess_type(blob_path)[0] or "application/octet-stream"
    blob_client.upload_blob(body, overwrite=True, content_type=ct)
    return f"/uploads/{blob_path}"


def download_blob(blob_path: str) -> Optional[bytes]:
    if not blob_enabled():
        return None
    try:
        client = _client()
        blob_client = client.get_blob_client(container=_container(), blob=blob_path)
        return blob_client.download_blob().readall()
    except Exception as e:
        print(f"Blob download failed for {blob_path}: {e}")
        return None


def save_upload_local_or_blob(
    local_dir: Path,
    filename: str,
    file_obj: BinaryIO,
    subfolder: str,
) -> str:
    """Returns DB path like /uploads/cvs/file.pdf"""
    blob_key = f"{subfolder}/{filename}"
    if blob_enabled():
        content = file_obj.read()
        upload_file(blob_key, content)
        return f"/uploads/{blob_key}"

    local_dir.mkdir(parents=True, exist_ok=True)
    dest = local_dir / filename
    file_obj.seek(0)
    with open(dest, "wb") as out:
        out.write(file_obj.read())
    return f"/uploads/{subfolder}/{filename}"


def resolve_local_path(upload_url_path: str) -> Optional[Path]:
    if not upload_url_path or not upload_url_path.startswith("/uploads/"):
        return None
    rel = upload_url_path[len("/uploads/") :]
    for base in (Path("uploads"), Path("/home/site/wwwroot/uploads"), Path("/tmp/uploads")):
        p = base / rel
        if p.exists():
            return p
    return None


def upload_spark_report(local_path: Path, blob_name: str) -> bool:
    if not blob_enabled() or not local_path.exists():
        return False
    data = local_path.read_bytes()
    upload_file(blob_name, data, content_type="application/json")
    return True


def read_upload_file(upload_url_path: str) -> Optional[bytes]:
    if blob_enabled() and upload_url_path.startswith("/uploads/"):
        key = upload_url_path[len("/uploads/") :]
        data = download_blob(key)
        if data:
            return data
    local = resolve_local_path(upload_url_path)
    if local and local.exists():
        return local.read_bytes()
    return None
