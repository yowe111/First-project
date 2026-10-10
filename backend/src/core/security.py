"""
security.py — ПАРОЛИ И ТОКЕНЫ.

Две независимые задачи.

1. **Хранение паролей.** Пароль не хранится как есть: если базу украдут,
   утекут все пароли. Храним `bcrypt`-хеш — необратимый отпечаток.
   Аналогия: отпечаток пальца позволяет ПРОВЕРИТЬ человека, но не даёт
   «собрать» его обратно.

2. **Токены (JWT).** Спрашивать логин и пароль при каждом запросе неудобно,
   поэтому после входа выдаём временный «пропуск».
   Аналогия: браслет на входе в клуб — показал охране, паспорт заново
   не спрашивают.

В модуле нет ни одного обращения к базе и ни одного упоминания HTTP:
это чистые функции, которые легко тестировать по отдельности.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from src.core.config import settings

# Алгоритм подписи. Подпись гарантирует, что токен не подделали.
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Превратить пароль в хеш для хранения в базе."""
    # gensalt() добавляет случайную «соль», поэтому одинаковые пароли
    # дают разные хеши — по базе нельзя найти людей с общим паролем.
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return hashed.decode()


def verify_password(password: str, hashed: str) -> bool:
    """Проверить, соответствует ли пароль сохранённому хешу."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(subject: str) -> str:
    """Выдать токен доступа.

    `subject` — id пользователя строкой. Именно id, а не логин: логин можно
    сменить через `PATCH /users/me`, и тогда токен со логином внутри
    разлогинил бы человека на середине действия.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    # "sub" (subject) — кому принадлежит токен, "exp" — до какого момента жив.
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Проверить токен и достать из него `sub`. Плохой токен → `None`."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        # Любая причина: подделанная подпись, истёкший срок, мусор вместо токена.
        return None
