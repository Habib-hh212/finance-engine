import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.auth import (
    REFRESH_COOKIE_NAME,
    clear_session_cookies,
    create_access_token,
    get_current_user,
    hash_password,
    set_session_cookies,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.services import password_reset, rate_limit
from app.services import refresh_token as refresh_token_service
from app.services.email import EmailError, send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

GENERIC_FORGOT_PASSWORD_MESSAGE = "If an account exists for that email, a password reset link has been sent."
RATE_LIMIT_MESSAGE = "Too many attempts. Please try again in a few minutes."


def _issue_session(db: Session, response: Response, user: User) -> str:
    """Sets the browser session cookies and returns the access token, which
    callers also put in the JSON body -- the web frontend ignores that
    field (it relies on the cookie), but it's what the test suite and any
    non-browser API client authenticate with, via a normal Bearer header."""
    access_token = create_access_token(str(user.id))
    refresh_token = refresh_token_service.issue_refresh_token(db, user)
    set_session_cookies(response, access_token, refresh_token)
    return access_token


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = rate_limit.client_ip(request)
    if rate_limit.is_rate_limited(db, f"register-ip:{ip}", max_attempts=20, window_minutes=60):
        db.commit()
        raise HTTPException(status_code=429, detail=RATE_LIMIT_MESSAGE)

    if db.query(User).filter(User.email == payload.email).first() is not None:
        db.commit()
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(email=payload.email, hashed_password=hash_password(payload.password), name=payload.name)
    db.add(user)
    db.flush()
    access_token = _issue_session(db, response, user)
    db.commit()
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = rate_limit.client_ip(request)
    email_key = f"login:{payload.email.lower()}"
    if rate_limit.is_rate_limited(db, email_key, max_attempts=8, window_minutes=15) or rate_limit.is_rate_limited(
        db, f"login-ip:{ip}", max_attempts=30, window_minutes=15
    ):
        db.commit()
        raise HTTPException(status_code=429, detail=RATE_LIMIT_MESSAGE)

    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        db.commit()
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = _issue_session(db, response, user)
    db.commit()
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    user, new_refresh_token = refresh_token_service.rotate_refresh_token(db, token)
    if user is None or new_refresh_token is None:
        clear_session_cookies(response)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired, please log in again")
    access_token = create_access_token(str(user.id))
    set_session_cookies(response, access_token, new_refresh_token)
    db.commit()
    return TokenResponse(access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if token:
        refresh_token_service.revoke_refresh_token(db, token)
        db.commit()
    clear_session_cookies(response)
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    ip = rate_limit.client_ip(request)
    if rate_limit.is_rate_limited(db, f"forgot-password:{payload.email.lower()}", max_attempts=5, window_minutes=60) or rate_limit.is_rate_limited(
        db, f"forgot-password-ip:{ip}", max_attempts=20, window_minutes=60
    ):
        db.commit()
        raise HTTPException(status_code=429, detail=RATE_LIMIT_MESSAGE)

    # Always return the same message whether or not the email is registered
    # -- otherwise this endpoint becomes a way to enumerate real accounts.
    user = db.query(User).filter(User.email == payload.email).first()
    if user is not None:
        token = password_reset.create_reset_token(db, user)
        db.commit()
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        try:
            send_password_reset_email(user.email, reset_url)
        except EmailError:
            logger.exception("Failed to send password reset email to %s", user.email)
    else:
        db.commit()
    return MessageResponse(message=GENERIC_FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = password_reset.consume_reset_token(db, payload.token)
    if user is None:
        db.commit()
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    user.hashed_password = hash_password(payload.new_password)
    # A password reset almost always means "I think someone else has my
    # password" -- kill every other browser session logged in as this user,
    # not just the device doing the reset.
    refresh_token_service.revoke_all_for_user(db, user.id)
    db.commit()
    return MessageResponse(message="Your password has been reset. You can now log in.")
