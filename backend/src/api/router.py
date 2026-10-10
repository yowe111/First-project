"""
router.py — СБОРКА ВСЕХ ЭНДПОИНТОВ В ОДИН РОУТЕР.

Зачем отдельный файл, если роутеры можно подключить прямо в `main.py`:
когда у API появится версионирование, достаточно будет написать здесь
`APIRouter(prefix="/api/v1")` — и все адреса переедут разом, без правки
десятка файлов.
"""

from fastapi import APIRouter

from src.api.routers import auth, notes, users

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(notes.router)
