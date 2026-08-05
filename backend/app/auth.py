from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import CompanyMembership, User

JWT_ALGORITHM = "HS256"
_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _credentials_exception()
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
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
