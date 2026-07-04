import uuid

from fastapi import UploadFile

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
SOURCE_ENUMS = {"camera", "gallery", "mock"}


def validate_image(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
        raise ValueError(f"Unsupported content type '{file.content_type}'; allowed: {allowed}")


def generate_storage_key(user_id: str, file_ext: str) -> str:
    image_id = str(uuid.uuid4())
    return f"{user_id}/{image_id}{file_ext}"


def guess_extension(content_type: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    return mapping.get(content_type, ".jpg")


def build_image_url(image_id: str) -> str:
    return f"{settings.MEDIA_BASE_URL}/api/v1/media/images/{image_id}"
