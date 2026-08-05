import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models import PasswordResetToken, User


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_reset_token(db: Session, user: User) -> str:
    """Invalidates any outstanding reset tokens for this user and issues a
    fresh one. Returns the raw token -- only the caller (the forgot-password
    endpoint, to put in the emailed link) ever sees it; the DB only stores
    its hash."""
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)).delete()

    token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash(token),
            expires_at=datetime.utcnow() + timedelta(minutes=settings.password_reset_expire_minutes),
        )
    )
    return token


def consume_reset_token(db: Session, token: str) -> Optional[User]:
    """Looks up the token by hash, checks it's unused and unexpired, marks
    it used, and returns the user it belongs to -- or None if the token is
    invalid, expired, or already used."""
    record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == _hash(token)).first()
    if record is None or record.used_at is not None or record.expires_at < datetime.utcnow():
        return None
    record.used_at = datetime.utcnow()
    return db.get(User, record.user_id)
