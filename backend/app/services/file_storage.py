import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


async def save_upload(file: UploadFile, subdir: str) -> str:
    """Save an uploaded file and return relative path."""
    file_id = str(uuid.uuid4())
    ext = Path(file.filename or "file").suffix
    relative_dir = f"{subdir}/{file_id}"
    abs_dir = Path(settings.UPLOAD_DIR) / relative_dir
    _ensure_dir(abs_dir)

    filename = f"original{ext}"
    filepath = abs_dir / filename
    content = await file.read()
    filepath.write_bytes(content)

    return f"{relative_dir}/{filename}"


def get_file_path(relative_path: str) -> Path:
    """Get absolute path from relative path."""
    return Path(settings.UPLOAD_DIR) / relative_path


def delete_file(relative_path: str) -> bool:
    """Delete a file by relative path."""
    try:
        filepath = get_file_path(relative_path)
        if filepath.exists():
            filepath.unlink()
            # Try to remove parent dir if empty
            parent = filepath.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        return True
    except Exception:
        return False
