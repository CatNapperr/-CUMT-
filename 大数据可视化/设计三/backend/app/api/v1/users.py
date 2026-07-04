from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.user import UserOut
from app.schemas.user_profile import UserProfileOut, UserProfileUpdate
from app.schemas.nutrition_targets import NutritionTargetsOut
from app.services.nutrition import calculate_targets as compute_targets

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_current_user(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(
        id=user.id,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_test_user=user.is_test_user,
    )


@router.get("/me/profile", response_model=UserProfileOut)
def get_user_profile(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return UserProfileOut(
        nickname=profile.nickname,
        gender=profile.gender,
        age=profile.age,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        body_fat_rate=profile.body_fat_rate,
        activity_level=profile.activity_level,
        health_goal=profile.health_goal,
    )


@router.put("/me/profile", response_model=UserProfileOut)
def update_user_profile(
    payload: UserProfileUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    profile.nickname = payload.nickname
    profile.gender = payload.gender
    profile.age = payload.age
    profile.height_cm = payload.height_cm
    profile.weight_kg = payload.weight_kg
    profile.body_fat_rate = payload.body_fat_rate
    profile.activity_level = payload.activity_level
    profile.health_goal = payload.health_goal

    db.commit()
    db.refresh(profile)

    return UserProfileOut(
        nickname=profile.nickname,
        gender=profile.gender,
        age=profile.age,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        body_fat_rate=profile.body_fat_rate,
        activity_level=profile.activity_level,
        health_goal=profile.health_goal,
    )


@router.get("/me/targets", response_model=NutritionTargetsOut)
def get_nutrition_targets(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return NutritionTargetsOut(**compute_targets(profile))
