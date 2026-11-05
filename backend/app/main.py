import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from .config import settings
from .database import Base, SessionLocal, engine
from .metrics import metrics_middleware, metrics_response
from .routers import admin, auth, channels, comments, feed, moderation, playlists, videos
from .services.seed import DemoSeeder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("tubeclone")


def wait_for_database(max_attempts: int = 45) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("PostgreSQL доступен")
            return
        except OperationalError as exc:
            logger.warning("Ожидание PostgreSQL (%s/%s): %s", attempt, max_attempts, exc.__class__.__name__)
            time.sleep(1)
    raise RuntimeError("Не удалось подключиться к PostgreSQL")


@asynccontextmanager
async def lifespan(_: FastAPI):
    wait_for_database()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        DemoSeeder(db).seed()
    yield


tags_metadata = [
    {"name": "Аутентификация", "description": "Регистрация, вход, JWT в httpOnly cookie, профиль."},
    {"name": "Лента и поиск", "description": "Главная лента, подписки, поиск по названию, история."},
    {"name": "Видео", "description": "Загрузка, метаданные, Range-стриминг, превью, лайки, приватный доступ, жалобы."},
    {"name": "Комментарии", "description": "Комментарии и ответы к видео."},
    {"name": "Каналы и подписки", "description": "Страницы каналов, видео, плейлисты, подписки."},
    {"name": "Плейлисты", "description": "Создание плейлистов и управление содержимым."},
    {"name": "Модерация", "description": "Очередь жалоб, скрытие и восстановление видео."},
    {"name": "Администрирование", "description": "Пользователи, роли, блокировки и статистика."},
]

app = FastAPI(
    title=settings.app_name,
    description=(
        f"{settings.app_description}\n\n"
        "**Роли:** `user` — обычный пользователь, `moderator` — обрабатывает жалобы и скрывает видео, "
        "`admin` — полный доступ, управление ролями и пользователями.\n\n"
        "**Демо-аккаунты:** `admin / Admin123!`, `moderator / Moder123!`, `creator / Creator123!`, "
        "`maria / Maria123!`, `user / User123!` (вход по username или email).\n\n"
        "Для Swagger нажмите **Authorize** и войдите через OAuth2 password flow "
        "(username и пароль). В браузере токен также хранится в httpOnly cookie."
    ),
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(metrics_middleware)

app.include_router(auth.router)
app.include_router(feed.router)
app.include_router(channels.router)
app.include_router(videos.router)
app.include_router(comments.router)
app.include_router(playlists.router)
app.include_router(moderation.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["Служебное"], summary="Проверка работоспособности")
def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    """Метрики для Prometheus (не входит в публичный Swagger)."""
    return metrics_response()


frontend_dir = Path(settings.frontend_dist)
assets_dir = frontend_dir / "assets"
if assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="Not found")
    if frontend_dir.is_dir():
        candidate = frontend_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        index = frontend_dir / "index.html"
        if index.is_file():
            return FileResponse(index)
    return {
        "message": "API TubeClone работает. Swagger: /docs",
        "frontend": "Соберите frontend (npm run build) или запустите через ./run.sh",
    }
