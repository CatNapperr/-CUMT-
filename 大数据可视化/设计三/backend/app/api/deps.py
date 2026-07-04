from app.core.config import settings


def get_current_user_id() -> str:
    return settings.TEST_USER_ID
