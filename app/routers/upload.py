from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_current_user, get_current_user_optional
from app.models import Entry, Image, User
from app.settings import Settings, get_settings

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

_MAGIC: dict[str, bytes | list[bytes]] = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": b"RIFF",
}


def _validate_magic_bytes(content_type: str, data: bytes) -> bool:
    magic = _MAGIC.get(content_type)
    if magic is None:
        return False
    if content_type == "image/webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if isinstance(magic, list):
        return any(data[: len(m)] == m for m in magic)
    return data[: len(magic)] == magic


@router.post("/upload")
async def upload_image(
    file: UploadFile,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type")

    extension = ALLOWED_TYPES[file.content_type]
    filename = f"{uuid4().hex}{extension}"

    upload_dir = Path(settings.data_dir) / "uploads" / str(user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    content = await file.read(MAX_SIZE + 1)
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    if not _validate_magic_bytes(file.content_type, content):
        raise HTTPException(status_code=400, detail="Invalid image content")
    (upload_dir / filename).write_bytes(content)

    image = Image(
        entry_id=None,
        user_id=user.id,
        filename=filename,
        original_name=file.filename or "",
    )
    session.add(image)
    session.commit()

    return {"url": f"/uploads/{user.id}/{filename}"}


@router.get("/uploads/{user_id}/{filename}")
async def serve_upload(
    user_id: int,
    filename: str,
    share_token: str | None = None,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
):
    if current_user is None:
        if not share_token:
            raise HTTPException(status_code=401, detail="Authentication required")
        stmt = select(Entry).where(Entry.share_token == share_token, Entry.user_id == user_id)
        entry = session.exec(stmt).first()
        if not entry:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    file_path = Path(settings.data_dir) / "uploads" / str(user_id) / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    try:
        file_path.resolve().relative_to((Path(settings.data_dir) / "uploads").resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    return FileResponse(file_path)
