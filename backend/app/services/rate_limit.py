"""A minimal, database-backed rate limiter -- deliberately not in-memory,
since Vercel serverless functions don't share memory between invocations
(each cold start would reset an in-process counter to zero, making it
useless). Postgres is the one thing every invocation already shares.

`key` scopes the window: callers compose it per action and per identity,
e.g. "login:user@example.com" or "login-ip:203.0.113.4", so a login
lockout on one email doesn't affect anyone else, and a registration flood
from one IP doesn't affect a different IP.
"""
from datetime import datetime, timedelta

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import RateLimitAttempt


def is_rate_limited(db: Session, key: str, max_attempts: int, window_minutes: int) -> bool:
    window_start = datetime.utcnow() - timedelta(minutes=window_minutes)
    # Prune this key's aged-out rows so the table doesn't grow unbounded --
    # cheap, since it only ever touches rows for this one key.
    db.query(RateLimitAttempt).filter(RateLimitAttempt.key == key, RateLimitAttempt.created_at < window_start).delete()

    count = db.query(RateLimitAttempt).filter(RateLimitAttempt.key == key).count()
    if count >= max_attempts:
        return True

    db.add(RateLimitAttempt(key=key))
    return False


def client_ip(request: Request) -> str:
    """Vercel (and most reverse proxies) put the real client address in
    X-Forwarded-For, not request.client -- that would otherwise just be the
    proxy's own address for every request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
