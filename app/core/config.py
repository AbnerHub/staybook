from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    app_port: int = 8000
    debug: bool = False
    # Allowed CORS origins for the frontend, provided as a comma-separated
    # string via the CORS_ORIGINS environment variable. Defaults to the local
    # Vite dev server origin. Kept as a plain string so it can be supplied as a
    # simple env value; use `cors_origins` for the parsed list.
    cors_origins_raw: str = Field(
        default="http://localhost:5173",
        validation_alias="CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
