from sqlalchemy.orm import Session

from app.models import user as user_model
from app.services.auth_service import create_access_token


def login_or_create_github_user(profile: dict, db: Session):
    github_id = str(profile["id"])
    login = profile.get("login", f"github_{github_id}")

    user = db.query(user_model.User).filter(
        user_model.User.login == login
    ).first()

    if not user:
        user = user_model.User(
            login=login,
            password="oauth"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "login": login
    }