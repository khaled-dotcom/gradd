"""Serve uploaded files from local disk or Azure Blob."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.src.utils.blob_storage import blob_enabled, download_blob, resolve_local_path

router = APIRouter(tags=["files"])


@router.get("/uploads/{folder}/{filename}")
def get_upload_file(folder: str, filename: str):
    key = f"{folder}/{filename}"
    if blob_enabled():
        data = download_blob(key)
        if data:
            media = "application/pdf" if filename.endswith(".pdf") else "application/octet-stream"
            if filename.lower().endswith((".jpg", ".jpeg")):
                media = "image/jpeg"
            elif filename.lower().endswith(".png"):
                media = "image/png"
            elif filename.lower().endswith(".webp"):
                media = "image/webp"
            return Response(content=data, media_type=media)

    path = resolve_local_path(f"/uploads/{key}")
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media = "application/octet-stream"
    if path.suffix.lower() in (".jpg", ".jpeg"):
        media = "image/jpeg"
    elif path.suffix.lower() == ".png":
        media = "image/png"
    return Response(content=path.read_bytes(), media_type=media)
