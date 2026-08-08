from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import CompanyMembership, User

JWT_ALGORITHM = "HS256"
ACCESS_COOKIE_NAME = "fe_access_token"
REFRESH_COOKIE_NAME = "fe_refresh_token"
_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    # SameSite=None is required for the cookie to be sent cross-site at all
    # (frontend and backend are separate Vercel domains); browsers require
    # Secure whenever SameSite=None is used, hence tying the two together.
    samesite = "none" if settings.cookie_secure else "lax"
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=samesite,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=samesite,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    # The web app authenticates purely via the httpOnly access-token cookie
    # (set by /auth/login, /auth/register, /auth/refresh) and never sees a
    # raw token in JS. A Bearer header, when present, still works too --
    # for API/script clients and for the test suite, which authenticates
    # this way deliberately so it's unaffected by any cookie a test
    # incidentally picks up by calling /auth/register or /auth/login again
    # on the shared client.
    token = credentials.credentials if credentials is not None else request.cookies.get(ACCESS_COOKIE_NAME)
    if token is None:
        raise _credentials_exception()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise _credentials_exception()
    if user_id is None:
        raise _credentials_exception()

    try:
        user = db.get(User, uuid.UUID(user_id))
    except ValueError:
        raise _credentials_exception()
    if user is None:
        raise _credentials_exception()
    return user


def _forbidden_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this company")


def user_has_company_access(db: Session, user_id, company_id) -> bool:
    return (
        db.query(CompanyMembership)
        .filter(CompanyMembership.user_id == user_id, CompanyMembership.company_id == company_id)
        .first()
        is not None
    )


def require_company_access(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> uuid.UUID:
    """Drop-in replacement for a plain `company_id: uuid.UUID` endpoint
    parameter -- FastAPI parses `company_id` off the same query string
    either way, so this only adds the membership check, nothing else about
    the endpoint has to change. Every endpoint that takes company_id
    directly should use this instead of the bare type annotation."""
    if not user_has_company_access(db, current_user.id, company_id):
        raise _forbidden_exception()
    return company_id


def require_resource_company_access(db: Session, current_user: User, company_id) -> None:
    """The equivalent check for endpoints keyed by a resource id (a budget,
    a journal entry, an asset...) instead of a direct company_id query
    param -- call this from inside the shared _get_X_or_404 helper once
    the resource (and therefore its company_id) has been loaded."""
    if not user_has_company_access(db, current_user.id, company_id):
        raise _forbidden_exception()
