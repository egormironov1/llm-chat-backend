from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.controllers import auth_controller
from app.controllers import github_controller
from app.controllers import user_controller
from app.controllers import chat_controller
from app.controllers import frontend_controller


app = FastAPI(title="LLM Chat Backend")

app.add_middleware(
    SessionMiddleware,
    secret_key="session-secret-key-change-me"
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_controller.router)
app.include_router(github_controller.router)
app.include_router(user_controller.router)
app.include_router(chat_controller.router)
app.include_router(frontend_controller.router)