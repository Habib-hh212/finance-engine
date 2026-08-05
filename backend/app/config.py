from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+psycopg2://finance:finance@localhost:5432/finance_engine"
    # Dev-only default. Production deploys MUST set JWT_SECRET_KEY to a real
    # random secret via environment variable, not this fallback.
    jwt_secret_key: str = "dev-only-insecure-secret-change-me"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Password reset email. RESEND_API_KEY must be set in production for
    # /auth/forgot-password to actually deliver mail; left blank locally,
    # where the reset link is only useful via the API response in tests.
    resend_api_key: str = ""
    email_from: str = "Finance Engine <onboarding@resend.dev>"
    frontend_url: str = "http://localhost:5173"
    password_reset_expire_minutes: int = 30


settings = Settings()
