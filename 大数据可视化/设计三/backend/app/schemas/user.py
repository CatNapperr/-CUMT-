from app.schemas.common import CamelCaseModel


class UserOut(CamelCaseModel):
    id: str
    display_name: str
    avatar_url: str | None = None
    is_test_user: bool
