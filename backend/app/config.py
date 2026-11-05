from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TubeClone"
    app_description: str = (
        "Клон YouTube: загрузка и раздача видео, приватные видео, каналы, "
        "подписки, плейлисты, комментарии, жалобы и модерация."
    )

    database_url: str = "postgresql+psycopg://tube:tube@localhost:5432/tube"
    jwt_secret: str = "dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    cookie_name: str = "tube_access_token"
    cookie_secure: bool = False

    media_dir: Path = Path("./media")
    frontend_dist: Path = Path("./frontend_dist")
    max_upload_mb: int = 1024
    max_thumbnail_mb: int = 10

    seed_demo: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def videos_dir(self) -> Path:
        return self.media_dir / "videos"

    @property
    def thumbnails_dir(self) -> Path:
        return self.media_dir / "thumbnails"


settings = Settings()
