# LLM Chat Backend

Backend application built with FastAPI.

## Stack

- FastAPI
- PostgreSQL
- Redis
- JWT
- GitHub OAuth

## Features

- User registration
- Login with JWT
- Refresh token via Redis
- GitHub OAuth login
- Protected endpoint (/me)

## Run

1. Clone repository:

```bash
git clone https://github.com/your-username/llm-chat-backend.git
cd llm-chat-backend

2. Create virtual environment:

python -m venv .venv

3. Activate (Windows):

.venv\Scripts\activate

4. Install dependencies:

pip install fastapi uvicorn[standard] sqlalchemy psycopg2-binary passlib[bcrypt] bcrypt==4.0.1 python-jose[cryptography] redis authlib httpx itsdangerous python-dotenv

5.Create .env file:

GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret

6. Start PostgreSQL and Redis:

docker compose up -d

7.Run backend:

uvicorn app.main:app --reload

8.Open Swagger:

http://127.0.0.1:8000/docs