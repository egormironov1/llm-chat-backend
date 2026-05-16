from fastapi import APIRouter, Depends

from app.models import user as user_model
from app.services.auth_service import get_current_user


router = APIRouter(tags=["User"])


@router.get("/me")
async def me(current_user: user_model.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "login": current_user.login
    }