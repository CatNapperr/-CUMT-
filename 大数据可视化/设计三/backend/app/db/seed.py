import uuid
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User
from app.models.user_profile import UserProfile

TEST_USER_ID = settings.TEST_USER_ID


def seed_test_user(db: Session) -> None:
    if not db.query(User).filter(User.id == TEST_USER_ID).first():
        user = User(
            id=TEST_USER_ID,
            display_name="王志豪",
            is_test_user=True,
        )
        db.add(user)
        db.commit()

    if not db.query(UserProfile).filter(UserProfile.user_id == TEST_USER_ID).first():
        profile = UserProfile(
            user_id=TEST_USER_ID,
            nickname="王志豪",
            gender="male",
            age=22,
            height_cm=175.0,
            weight_kg=70.0,
            body_fat_rate=18.0,
            activity_level="moderate",
            health_goal="fat_loss",
        )
        db.add(profile)
        db.commit()
