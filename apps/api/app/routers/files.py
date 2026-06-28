from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import UploadedFile, new_id
from app.schemas import UploadedFileRead

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload", response_model=UploadedFileRead)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)) -> UploadedFile:
    settings = get_settings()
    suffix = Path(file.filename or "").suffix
    filename = f"{new_id()}{suffix}"
    path = settings.upload_dir / filename
    content = await file.read()
    path.write_bytes(content)
    item = UploadedFile(
        original_name=file.filename or filename,
        path=str(path),
        content_type=file.content_type or "",
        size=len(content),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

