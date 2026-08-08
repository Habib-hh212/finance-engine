"""Refresh tokens back the browser session cookie: a raw, random token goes
into an httpOnly cookie, only its SHA-256 hash is stored (same convention
as password_reset.py), and every successful refresh rotates it -- revokes
the one just used and issues a new one -- so a copied-but-unused token
stops working as soon as the real session refreshes again.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models import RefreshToken, User


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_refresh_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_hash(token),
            expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    return token


def rotate_refresh_token(db: Session, token: str) -> tuple[Optional[User], Optional[str]]:
    """Validates the given refresh token; if valid, revokes it and issues a
    replacement for the same user. Returns (None, None) if the token is
    missing, expired, or already revoked (e.g. reused after theft, or after
    logout)."""
    record = db.query(RefreshToken).filter(RefreshToken.token_hash == _hash(token)).first()
    if record is None or record.revoked_at is not None or record.expires_at < datetime.utcnow():
        return None, None
    record.revoked_at = datetime.utcnow()
    user = db.get(User, record.user_id)
    if user is None:
        return None, None
    return user, issue_refresh_token(db, user)


def revoke_refresh_token(db: Session, token: str) -> None:
    record = db.query(RefreshToken).filter(RefreshToken.token_hash == _hash(token)).first()
    if record is not None:
        record.revoked_at = datetime.utcnow()


def revoke_all_for_user(db: Session, user_id) -> None:
    """Called on password reset, so changing a compromised password also
    kills every other browser session logged in as that user."""
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)).update(
        {"revoked_at": datetime.utcnow()}
    )
