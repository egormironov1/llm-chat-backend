from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import user as user_model
from app.services.auth_service import create_access_token


async def login_or_create_github_user(profile: dict, db: AsyncSession):
    github_id = str(profile["id"])
    login = profile.get("login", f"github_{github_id}")

    result = await db.execute(
        select(user_model.User).where(user_model.User.login == login)
    )

    user = result.scalar_one_or_none()

    if not user:
        user = user_model.User(
            login=login,
            password="oauth"
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "login": login
    }