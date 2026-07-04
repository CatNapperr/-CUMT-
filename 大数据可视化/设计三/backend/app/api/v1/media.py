from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import settings
from app.db.session import get_db
from app.models.media_asset import MediaAsset
from app.schemas.media import MediaUploadResponse
from app.services.media import (
    validate_image,
    guess_extension,
    build_image_url,
    generate_storage_key,
    SOURCE_ENUMS,
    MAX_FILE_SIZE,
)

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/images", response_model=MediaUploadResponse, status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    source: str = Form(...),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if source not in SOURCE_ENUMS:
        allowed = ", ".join(sorted(SOURCE_ENUMS))
        raise HTTPException(status_code=422, detail=f"Invalid source; allowed: {allowed}")

    try:
        validate_image(file)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not file.filename:
        raise HTTPException(status_code=422, detail="Filename is required")

    contents = await file.read()
    size_bytes = len(contents)

    if size_bytes > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"File size exceeds {MAX_FILE_SIZE // (1024*1024)} MB limit",
        )

    file_ext = guess_extension(file.content_type)
    storage_key = generate_storage_key(current_user_id, file_ext)

    upload_path = Path(settings.UPLOAD_DIR) / storage_key
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    with open(upload_path, "wb") as f:
        f.write(contents)

    image_id = Path(storage_key).stem
    image_url = build_image_url(image_id)

    asset = MediaAsset(
        id=image_id,
        user_id=current_user_id,
        file_name=file.filename,
        content_type=file.content_type,
        storage_key=storage_key,
        image_url=image_url,
        size_bytes=size_bytes,
        width=None,
        height=None,
        source=source,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    return MediaUploadResponse(
        id=asset.id,
        image_url=asset.image_url,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        width=asset.width,
        height=asset.height,
        source=asset.source,
    )


@router.get("/images/{image_id}")
def get_image(
    image_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    asset = db.query(MediaAsset).filter(MediaAsset.id == image_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Image not found")
    if asset.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = Path(settings.UPLOAD_DIR) / asset.storage_key
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type=asset.content_type,
        filename=asset.file_name,
    )
