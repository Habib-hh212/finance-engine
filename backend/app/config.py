from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+psycopg2://finance:finance@localhost:5432/finance_engine"
    # Dev-only default. Production deploys MUST set JWT_SECRET_KEY to a real
    # random secret via environment variable, not this fallback.
    jwt_secret_key: str = "dev-only-insecure-secret-change-me"
    # Short-lived on purpose: this is the window a stolen access token stays
    # usable. The browser session doesn't feel this -- refresh_token_expire_days
    # below silently renews it. API/bearer-token clients (and tests) that
    # never refresh will need to re-authenticate after this expires.
    jwt_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    # False only in the test suite (see conftest.py) -- the ASGI TestClient's
    # base_url is plain http, and a real browser session always gets this
    # over HTTPS in both prod and local dev (Chrome/Firefox treat
    # http://localhost as a secure context, so Secure cookies still work
    # there without turning this off).
    cookie_secure: bool = True

    # Password reset email. RESEND_API_KEY must be set in production for
    # /auth/forgot-password to actually deliver mail; left blank locally,
    # where the reset link is only useful via the API response in tests.
    resend_api_key: str = ""
    email_from: str = "Finance Engine <onboarding@resend.dev>"
    frontend_url: str = "http://localhost:5173"
    password_reset_expire_minutes: int = 30


settings = Settings()
