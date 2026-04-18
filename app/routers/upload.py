from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models import Image, User
from app.settings import Settings, get_settings

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


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
    settings: Settings = Depends(get_settings),
):
    file_path = Path(settings.data_dir) / "uploads" / str(user_id) / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    try:
        file_path.resolve().relative_to((Path(settings.data_dir) / "uploads").resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden")
    return FileResponse(file_path)
