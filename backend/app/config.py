from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://finance:finance@localhost:5432/finance_engine"

    class Config:
        env_file = ".env"


settings = Settings()
