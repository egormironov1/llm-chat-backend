from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models import user as user_model
from app.models import chat as chat_model
from app.schemas.chat import ChatCreate, MessageCreate
from app.schemas.user import UserCreate, UserLogin
from app.services.auth_service import (
    ALGORITHM,
    SECRET_KEY,
    login_user,
    register_user,
)
from app.services.chat_service import (
    ask_llm_in_chat,
    create_user_chat,
    get_chat_messages,
    get_user_chats,
)


router = APIRouter(tags=["Frontend"])
templates = Jinja2Templates(directory="app/templates")


def redirect(url: str):
    return RedirectResponse(url=url, status_code=303)


async def get_user_from_session(request: Request, db: AsyncSession):
    token = request.session.get("access_token")

    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            return None

    except JWTError:
        return None

    result = await db.execute(
        select(user_model.User).where(user_model.User.id == int(user_id))
    )

    return result.scalar_one_or_none()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if request.session.get("access_token"):
        return redirect("/ui/chats")

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "title": "Home",
        },
    )


# Redirect old route to new UI route
@router.get("/login")
async def old_login_page():
    return redirect("/ui/login")


@router.get("/ui/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "title": "Login",
            "error": None,
        },
    )


@router.post("/ui/login", response_class=HTMLResponse)
async def login_action(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await login_user(
            UserLogin(login=login, password=password),
            db,
        )

    except HTTPException as exc:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "title": "Login",
                "error": exc.detail,
            },
            status_code=400,
        )

    request.session["access_token"] = result["access_token"]
    request.session["login"] = login

    return redirect("/ui/chats")


# Redirect old route to new UI route
@router.get("/register")
async def old_register_page():
    return redirect("/ui/register")


@router.get("/ui/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "title": "Register",
            "error": None,
        },
    )


@router.post("/ui/register", response_class=HTMLResponse)
async def register_action(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        await register_user(
            UserCreate(login=login, password=password),
            db,
        )

        result = await login_user(
            UserLogin(login=login, password=password),
            db,
        )

    except HTTPException as exc:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "title": "Register",
                "error": exc.detail,
            },
            status_code=400,
        )

    request.session["access_token"] = result["access_token"]
    request.session["login"] = login

    return redirect("/ui/chats")


@router.get("/ui/logout")
async def logout(request: Request):
    request.session.clear()
    return redirect("/")


@router.post("/ui/logout")
async def logout_post(request: Request):
    request.session.clear()
    return redirect("/")


@router.get("/ui/chats", response_class=HTMLResponse)
async def chats_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_user_from_session(request, db)

    if current_user is None:
        return redirect("/ui/login")

    chats = await get_user_chats(current_user, db)

    return templates.TemplateResponse(
        request,
        "chats.html",
        {
            "title": "My Chats",
            "chats": chats,
        },
    )


@router.post("/ui/chats/create")
async def create_chat_action(
    request: Request,
    title: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_user_from_session(request, db)

    if current_user is None:
        return redirect("/ui/login")

    new_chat = await create_user_chat(
        ChatCreate(title=title),
        current_user,
        db,
    )

    return redirect(f"/ui/chats/{new_chat['id']}")


# Old route support
@router.post("/ui/chats")
async def create_chat_action_old(
    request: Request,
    title: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    return await create_chat_action(request, title, db)


@router.get("/ui/chats/{chat_id}", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    chat_id: int,
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_user_from_session(request, db)

    if current_user is None:
        return redirect("/ui/login")

    result = await db.execute(
        select(chat_model.Chat).where(
            chat_model.Chat.id == chat_id,
            chat_model.Chat.user_id == current_user.id,
        )
    )

    chat = result.scalar_one_or_none()

    if chat is None:
        return redirect("/ui/chats")

    chats = await get_user_chats(current_user, db)
    messages = await get_chat_messages(chat_id, current_user, db)

    return templates.TemplateResponse(
        request,
        "chat.html",
        {
            "title": chat.title,
            "chat": chat,
            "chats": chats,
            "messages": messages,
        },
    )


@router.post("/ui/chats/{chat_id}/send")
async def send_message_action(
    request: Request,
    chat_id: int,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_user_from_session(request, db)

    if current_user is None:
        return redirect("/ui/login")

    await ask_llm_in_chat(
        chat_id,
        MessageCreate(content=content),
        current_user,
        db,
    )

    return redirect(f"/ui/chats/{chat_id}")


# Old route support
@router.post("/ui/chats/{chat_id}/ask")
async def ask_action_old(
    request: Request,
    chat_id: int,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    return await send_message_action(request, chat_id, content, db)