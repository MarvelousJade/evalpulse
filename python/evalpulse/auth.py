import secrets
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Cookie, Depends, Header, HTTPException, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User

SESSION_COOKIE = "evalpulse_session"
CSRF_COOKIE = "evalpulse_csrf"
password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="evalpulse-session")


def set_session(response: Response, user: User) -> str:
    settings = get_settings()
    csrf_token = secrets.token_urlsafe(24)
    token = _serializer().dumps({"user_id": user.id, "csrf": csrf_token})
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=settings.session_max_age_seconds,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return csrf_token


def clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(CSRF_COOKIE)


def get_current_user(
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    db: Session = Depends(get_db),
) -> User:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        payload = _serializer().loads(session_token, max_age=get_settings().session_max_age_seconds)
    except (BadSignature, SignatureExpired) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
        ) from exc
    user = db.get(User, payload.get("user_id"))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return user


def require_csrf(
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias=CSRF_COOKIE)] = None,
) -> None:
    if not csrf_header or not csrf_cookie or not secrets.compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


def ensure_demo_user(db: Session) -> None:
    email = "demo@evalpulse.local"
    if db.scalar(select(User).where(User.email == email)) is None:
        db.add(
            User(
                email=email,
                display_name="Demo Reviewer",
                password_hash=hash_password("evalpulse-demo"),
            )
        )
        db.commit()
