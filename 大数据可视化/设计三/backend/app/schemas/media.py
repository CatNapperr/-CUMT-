from app.schemas.common import CamelCaseModel


class MediaUploadResponse(CamelCaseModel):
    id: str
    image_url: str
    content_type: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    source: str
