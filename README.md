# LLM Chat Backend

This is a backend application made with FastAPI for a homework project.

## Features

- user registration
- login with JWT
- refresh token using Redis
- GitHub OAuth login
- create chats
- send messages
- message history is saved
- local LLM is connected (llama-cpp)

## Stack

- Python
- FastAPI
- PostgreSQL
- Redis
- JWT
- GitHub OAuth
- llama-cpp-python

## How to run

1. Clone repository:

git clone https://github.com/egormironov1/llm-chat-backend.git  
cd llm-chat-backend

2. Create virtual environment:

python -m venv .venv

3. Activate (Windows):

.venv\Scripts\activate

4. Install dependencies:

pip install -r requirements.txt

5. Create `.env` file:

GITHUB_CLIENT_ID=your_id  
GITHUB_CLIENT_SECRET=your_secret

6. Start database and Redis:

docker compose up -d

7. Run migrations:

alembic upgrade head

8. Run server:

uvicorn app.main:app --reload

9. Open Swagger:

http://127.0.0.1:8000/docs

## Endpoints

- POST /register
- POST /login
- POST /refresh
- GET /me
- POST /chats
- GET /chats
- POST /chats/{chat_id}/ask
- GET /chats/{chat_id}/messages
- GET /auth/github

## LLM

Uses local GGUF model.

You need to put file:

model.gguf

in the root of the project.

If model is not available, API still works but returns placeholder answers.

## Architecture

SPA approach (API only).

MCS:
- models — database models
- controllers — API endpoints
- services — LLM logic