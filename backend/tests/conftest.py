from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

# Окружение должно быть настроено до импорта приложения: config читает переменные
# при создании объекта settings.
TMP_DIR = Path(tempfile.mkdtemp(prefix="tubeclone-tests-"))
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TMP_DIR / 'test.db'}"
os.environ["SEED_DEMO"] = "false"
os.environ["MEDIA_DIR"] = str(TMP_DIR / "media")
os.environ["FRONTEND_DIST"] = str(TMP_DIR / "frontend")
os.environ["JWT_SECRET"] = "test-secret"
os.environ["COOKIE_SECURE"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import (
    Comment,
    Playlist,
    PlaylistItem,
    Report,
    ReportStatus,
    Role,
    Subscription,
    User,
    Video,
    VideoAccess,
    VideoStatus,
    Visibility,
    WatchHistory,
)
from app.security import hash_password

PASSWORD = "Passw0rd!"
# Один хеш на всех тестовых пользователей: bcrypt намеренно медленный,
# а проверять разные пароли в тестах не нужно.
PASSWORD_HASH = hash_password(PASSWORD)

USERS = [
    ("admin", "admin@example.com", "Админ", Role.admin),
    ("moderator", "moderator@example.com", "Модератор", Role.moderator),
    ("creator", "creator@example.com", "Иван Петров", Role.user),
    ("maria", "maria@example.com", "Мария Соколова", Role.user),
    ("user", "user@example.com", "Алексей", Role.user),
]

VIDEOS = [
    ("public1", "Обзор нового смартфона", "creator", Visibility.public, VideoStatus.published, 100),
    ("public2", "Как приготовить пасту", "maria", Visibility.public, VideoStatus.published, 50),
    ("private", "Приватный влог", "creator", Visibility.private, VideoStatus.published, 10),
    ("unlisted", "Секреты монтажа", "creator", Visibility.unlisted, VideoStatus.published, 5),
    ("public5", "Утренняя рутина", "maria", Visibility.public, VideoStatus.published, 200),
    ("hidden", "Скрытый ролик", "creator", Visibility.public, VideoStatus.hidden, 1),
    ("public7", "Путешествие в горы", "creator", Visibility.public, VideoStatus.published, 75),
]


def _reset_database() -> SimpleNamespace:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    media_dir = Path(os.environ["MEDIA_DIR"])
    (media_dir / "videos").mkdir(parents=True, exist_ok=True)
    (media_dir / "thumbnails").mkdir(parents=True, exist_ok=True)
    # Настоящий контейнер не нужен: Range-стриминг работает с любыми байтами.
    (media_dir / "videos" / "sample.mp4").write_bytes(b"\x00\x01\x02\x03" * 2048)

    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        users: dict[str, User] = {}
        for username, email, display_name, role in USERS:
            user = User(
                username=username,
                email=email,
                display_name=display_name,
                password_hash=PASSWORD_HASH,
                role=role,
            )
            db.add(user)
            users[username] = user
        db.flush()

        videos: dict[str, Video] = {}
        for index, (key, title, owner, visibility, status, views) in enumerate(VIDEOS, start=1):
            video = Video(
                title=title,
                description=f"Описание видео «{title}»",
                visibility=visibility,
                status=status,
                storage_path="videos/sample.mp4",
                original_filename=f"sample-{index}.mp4",
                content_type="video/mp4",
                size_bytes=8192,
                duration_seconds=10.0,
                views_count=views,
                owner_id=users[owner].id,
                created_at=now - timedelta(days=index),
                updated_at=now - timedelta(days=index),
            )
            db.add(video)
            videos[key] = video
        db.flush()

        db.add_all(
            [
                Subscription(subscriber_id=users["user"].id, channel_id=users["creator"].id),
                Subscription(subscriber_id=users["user"].id, channel_id=users["maria"].id),
            ]
        )
        db.add_all(
            [
                VideoAccess(video_id=videos["private"].id, user_id=users["user"].id),
                VideoAccess(video_id=videos["private"].id, user_id=users["maria"].id),
            ]
        )
        db.add_all(
            [
                Comment(video_id=videos["public1"].id, user_id=users["user"].id, text="Отличный обзор"),
                Comment(video_id=videos["public1"].id, user_id=users["maria"].id, text="Согласна"),
            ]
        )
        db.add(
            Report(
                video_id=videos["public1"].id,
                reporter_id=users["maria"].id,
                category="spam",
                reason="Тестовая жалоба",
                status=ReportStatus.open,
            )
        )

        public_playlist = Playlist(
            title="Лучшие обзоры",
            description="Подборка",
            visibility=Visibility.public,
            owner_id=users["creator"].id,
        )
        private_playlist = Playlist(
            title="Избранное",
            description="Личное",
            visibility=Visibility.private,
            owner_id=users["user"].id,
        )
        db.add_all([public_playlist, private_playlist])
        db.flush()
        db.add_all(
            [
                PlaylistItem(
                    playlist_id=public_playlist.id,
                    video_id=videos["public1"].id,
                    position=1,
                ),
                PlaylistItem(
                    playlist_id=private_playlist.id,
                    video_id=videos["public1"].id,
                    position=1,
                ),
            ]
        )
        db.add(
            WatchHistory(
                user_id=users["user"].id,
                video_id=videos["public1"].id,
                watched_at=now - timedelta(hours=1),
                position_seconds=5,
            )
        )
        db.commit()

        world = SimpleNamespace(
            password=PASSWORD,
            users={name: user.id for name, user in users.items()},
            videos={name: video.id for name, video in videos.items()},
            playlists={"public": public_playlist.id, "private": private_playlist.id},
        )
    return world


@pytest.fixture(scope="session", autouse=True)
def app_lifespan():
    """Один раз запускает lifespan приложения (создание таблиц, проверка БД)."""
    with TestClient(app):
        yield


@pytest.fixture()
def world() -> SimpleNamespace:
    return _reset_database()


@pytest.fixture()
def client():
    test_client = TestClient(app)
    yield test_client
    test_client.close()


@pytest.fixture()
def make_client():
    clients: list[TestClient] = []

    def factory() -> TestClient:
        test_client = TestClient(app)
        clients.append(test_client)
        return test_client

    yield factory
    for test_client in clients:
        test_client.close()


@pytest.fixture()
def login(make_client):
    def do_login(username: str, password: str | None = None) -> TestClient:
        test_client = make_client()
        response = test_client.post(
            "/api/auth/login",
            json={"login": username, "password": password or PASSWORD},
        )
        assert response.status_code == 200, response.text
        return test_client

    return do_login


@pytest.fixture()
def db():
    with SessionLocal() as session:
        yield session


def db_user(db, username: str) -> User:
    return db.scalar(select(User).where(User.username == username))


def db_video(db, video_id: int) -> Video:
    return db.get(Video, video_id)
