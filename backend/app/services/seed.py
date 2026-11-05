from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    Comment,
    Like,
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
from ..security import hash_password
from .media import MediaService, media_service

logger = logging.getLogger("tubeclone.seed")


class DemoSeeder:
    """Создаёт согласованный набор демо-данных при первом запуске."""

    FONT_CANDIDATES = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]

    USERS = [
        {
            "username": "admin",
            "email": "admin@example.com",
            "display_name": "Админ",
            "password": "Admin123!",
            "role": Role.admin,
            "bio": "Администратор TubeClone. Управляет пользователями и ролями.",
        },
        {
            "username": "moderator",
            "email": "moderator@example.com",
            "display_name": "Модератор",
            "password": "Moder123!",
            "role": Role.moderator,
            "bio": "Следит за порядком, обрабатывает жалобы и скрывает нарушения.",
        },
        {
            "username": "creator",
            "email": "creator@example.com",
            "display_name": "Иван Петров",
            "password": "Creator123!",
            "role": Role.user,
            "bio": "Обзоры техники, монтаж и всё про цифровые инструменты.",
        },
        {
            "username": "maria",
            "email": "maria@example.com",
            "display_name": "Мария Соколова",
            "password": "Maria123!",
            "role": Role.user,
            "bio": "Готовлю, путешествую и делюсь уютными историями.",
        },
        {
            "username": "user",
            "email": "user@example.com",
            "display_name": "Алексей",
            "password": "User123!",
            "role": Role.user,
            "bio": "Просто смотрю интересное видео.",
        },
    ]

    VIDEOS = [
        {
            "title": "Обзор нового смартфона: честный тест",
            "description": (
                "Тестируем флагман неделю: камера, автономность, экран и реальная производительность. "
                "В конце — честный вердикт, стоит ли переплачивать."
            ),
            "owner": "creator",
            "visibility": Visibility.public,
            "status": VideoStatus.published,
            "color": "1f3a5f",
            "duration": 10,
            "views": 18420,
            "days_ago": 1,
        },
        {
            "title": "Как приготовить пасту за 15 минут",
            "description": "Простой ужин из доступных продуктов: сливочный соус, чеснок, пармезан и немного зелени.",
            "owner": "maria",
            "visibility": Visibility.public,
            "status": VideoStatus.published,
            "color": "2e5d4b",
            "duration": 9,
            "views": 9320,
            "days_ago": 2,
        },
        {
            "title": "Приватный влог: только для своих",
            "description": "Личная история о поездке и планах на месяц. Видео доступно только приглашённым зрителям.",
            "owner": "creator",
            "visibility": Visibility.private,
            "status": VideoStatus.published,
            "color": "1f4f4a",
            "duration": 8,
            "views": 74,
            "days_ago": 3,
        },
        {
            "title": "Секреты монтажа видео",
            "description": "Пять приёмов, которые ускоряют монтаж и делают картинку дороже. Ссылка доступна только по прямой ссылке.",
            "owner": "creator",
            "visibility": Visibility.unlisted,
            "status": VideoStatus.published,
            "color": "2f2f5f",
            "duration": 11,
            "views": 412,
            "days_ago": 4,
        },
        {
            "title": "Утренняя рутина и продуктивность",
            "description": "Как выстроить утро, чтобы успевать главное и не выгорать. Спокойный влог без спешки.",
            "owner": "maria",
            "visibility": Visibility.public,
            "status": VideoStatus.published,
            "color": "5a2e4f",
            "duration": 9,
            "views": 12310,
            "days_ago": 5,
        },
        {
            "title": "Скрытый ролик: пример модерации",
            "description": "Этот ролик скрыт модератором. Владелец видит его в своём канале, остальные — нет.",
            "owner": "creator",
            "visibility": Visibility.public,
            "status": VideoStatus.hidden,
            "color": "3a3a3a",
            "duration": 7,
            "views": 230,
            "days_ago": 6,
        },
        {
            "title": "Путешествие в горы: лучшие кадры",
            "description": "Три дня в горах, рассветы, туман и невероятные виды. Собрала самые атмосферные моменты.",
            "owner": "maria",
            "visibility": Visibility.public,
            "status": VideoStatus.published,
            "color": "6b4a1f",
            "duration": 10,
            "views": 6410,
            "days_ago": 7,
        },
    ]

    COMMENTS = [
        ("Обзор нового смартфона: честный тест", "user", "Спасибо за честный тест! Особенно про автономность."),
        ("Обзор нового смартфона: честный тест", "maria", "Отличный обзор, всё по делу."),
        ("Обзор нового смартфона: честный тест", "creator", "Рад, что зашло! Скоро будет продолжение."),
        ("Как приготовить пасту за 15 минут", "user", "Приготовил — получилось очень вкусно!"),
        ("Как приготовить пасту за 15 минут", "creator", "Сохранил рецепт, надо попробовать."),
        ("Утренняя рутина и продуктивность", "user", "Очень спокойное и полезное видео."),
        ("Путешествие в горы: лучшие кадры", "moderator", "Красивые кадры, особенно рассвет."),
        ("Секреты монтажа видео", "maria", "Приём с ритмом реально работает."),
    ]

    SUBSCRIPTIONS = [
        ("user", "creator"),
        ("user", "maria"),
        ("creator", "maria"),
        ("maria", "creator"),
        ("moderator", "creator"),
    ]

    LIKE_PLAN = {
        "Обзор нового смартфона: честный тест": [("user", 1), ("maria", 1), ("moderator", 1), ("admin", 1)],
        "Как приготовить пасту за 15 минут": [("user", 1), ("creator", 1), ("moderator", 1)],
        "Утренняя рутина и продуктивность": [("user", 1), ("creator", 1)],
        "Путешествие в горы: лучшие кадры": [("user", 1), ("moderator", 1), ("creator", 1)],
        "Секреты монтажа видео": [("maria", 1)],
        "Скрытый ролик: пример модерации": [("user", -1)],
    }

    PLAYLIST_ITEMS = [
        ("public", "Обзор нового смартфона: честный тест"),
        ("public", "Секреты монтажа видео"),
        ("lifestyle", "Как приготовить пасту за 15 минут"),
        ("lifestyle", "Утренняя рутина и продуктивность"),
        ("private", "Обзор нового смартфона: честный тест"),
        ("private", "Путешествие в горы: лучшие кадры"),
    ]

    HISTORY_ITEMS = [
        ("user", "Обзор нового смартфона: честный тест"),
        ("user", "Как приготовить пасту за 15 минут"),
        ("creator", "Утренняя рутина и продуктивность"),
    ]

    PRIVATE_ACCESS_USERS = ("user", "maria")

    def __init__(self, db: Session, media: MediaService | None = None) -> None:
        self.db = db
        self.media = media or media_service

    def seed(self) -> None:
        self.media.ensure_dirs()
        if not settings.seed_demo:
            return
        if (self.db.scalar(select(func.count(User.id))) or 0) > 0:
            return

        logger.info("Создаём демо-данные TubeClone…")
        users = self._create_users()
        now = datetime.now(timezone.utc)
        videos = self._create_videos(users, now)
        self._create_subscriptions(users)
        self._create_likes(users, videos)
        self._create_comments(users, videos, now)
        self._create_private_access(users, videos)
        self._create_playlists(users, videos)
        self._create_history(users, videos, now)
        self._create_reports(users, videos, now)
        self.db.commit()
        logger.info("Демо-данные TubeClone созданы: %s пользователей, %s видео", len(users), len(videos))

    def _create_users(self) -> dict[str, User]:
        users: dict[str, User] = {}
        for data in self.USERS:
            user = User(
                username=data["username"],
                email=data["email"],
                display_name=data["display_name"],
                password_hash=hash_password(data["password"]),
                role=data["role"],
                bio=data["bio"],
            )
            self.db.add(user)
            users[user.username] = user
        self.db.commit()
        for user in users.values():
            self.db.refresh(user)
        return users

    def _create_videos(self, users: dict[str, User], now: datetime) -> dict[str, Video]:
        videos: dict[str, Video] = {}
        for index, data in enumerate(self.VIDEOS, start=1):
            generated = self._generate_demo_video(index, data["title"], data["color"], data["duration"])
            if generated is None:
                logger.warning("Демо-видео %s пропущено", data["title"])
                continue
            video_rel, thumb_rel = generated
            video_path = self.media.path(video_rel)
            owner = users[data["owner"]]
            video = Video(
                title=data["title"],
                description=data["description"],
                visibility=data["visibility"],
                status=data["status"],
                storage_path=video_rel,
                thumbnail_path=thumb_rel,
                original_filename=f"seed-{index}.mp4",
                content_type="video/mp4",
                size_bytes=video_path.stat().st_size,
                duration_seconds=self.media.probe_duration(video_path) or float(data["duration"]),
                views_count=data["views"],
                owner_id=owner.id,
                created_at=now - timedelta(days=data["days_ago"], hours=index),
                updated_at=now - timedelta(days=data["days_ago"], hours=index),
            )
            self.db.add(video)
            videos[video.title] = video
        self.db.commit()
        for video in videos.values():
            self.db.refresh(video)
        return videos

    def _generate_demo_video(
        self,
        index: int,
        title: str,
        color: str,
        duration: int,
    ) -> tuple[str, str] | None:
        self.media.ensure_dirs()
        video_rel = f"videos/seed-{index}.mp4"
        thumb_rel = f"thumbnails/seed-{index}.jpg"
        video_path = self.media.path(video_rel)
        thumb_path = self.media.path(thumb_rel)

        if not video_path.is_file():
            title_file = self.media.media_dir / f".seed-title-{index}.txt"
            title_file.write_text(title, encoding="utf-8")
            font = self._font_path()
            video_filter = None
            if font:
                video_filter = (
                    f"drawtext=fontfile={font}:textfile={title_file}:fontcolor=white:fontsize=54:"
                    "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.25:boxborderw=24"
                )
            command = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x{color}:s=1280x720:r=30:d={duration}",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={300 + index * 55}:duration={duration}",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-af",
                "volume=0.06",
                "-shortest",
            ]
            if video_filter:
                command.extend(["-vf", video_filter])
            command.append(str(video_path))
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=120)
                if result.returncode != 0:
                    logger.warning("ffmpeg seed error: %s", result.stderr[-500:])
                    video_path.unlink(missing_ok=True)
                    return None
            except (OSError, subprocess.SubprocessError) as exc:
                logger.warning("Не удалось создать демо-видео: %s", exc)
                video_path.unlink(missing_ok=True)
                return None
            finally:
                title_file.unlink(missing_ok=True)

        if not thumb_path.is_file():
            self.media.generate_thumbnail(video_path, thumb_path, self.media.probe_duration(video_path))

        if not video_path.is_file():
            return None
        return video_rel, thumb_rel

    def _font_path(self) -> str | None:
        for candidate in self.FONT_CANDIDATES:
            if Path(candidate).is_file():
                return candidate
        return None

    def _create_subscriptions(self, users: dict[str, User]) -> None:
        for subscriber, channel in self.SUBSCRIPTIONS:
            self.db.add(Subscription(subscriber_id=users[subscriber].id, channel_id=users[channel].id))

    def _create_likes(self, users: dict[str, User], videos: dict[str, Video]) -> None:
        for title, reactions in self.LIKE_PLAN.items():
            video = videos.get(title)
            if video is None:
                continue
            for username, value in reactions:
                self.db.add(Like(user_id=users[username].id, video_id=video.id, value=value))

    def _create_comments(self, users: dict[str, User], videos: dict[str, Video], now: datetime) -> None:
        for title, username, text in self.COMMENTS:
            video = videos.get(title)
            if video is None:
                continue
            self.db.add(
                Comment(
                    video_id=video.id,
                    user_id=users[username].id,
                    text=text,
                    created_at=now - timedelta(hours=len(text) % 20 + 1),
                )
            )

    def _create_private_access(self, users: dict[str, User], videos: dict[str, Video]) -> None:
        private_video = videos.get("Приватный влог: только для своих")
        if private_video is None:
            return
        for username in self.PRIVATE_ACCESS_USERS:
            self.db.add(VideoAccess(video_id=private_video.id, user_id=users[username].id))

    def _create_playlists(self, users: dict[str, User], videos: dict[str, Video]) -> None:
        playlists = {
            "public": Playlist(
                title="Лучшие обзоры",
                description="Подборка обзоров техники и полезных материалов.",
                visibility=Visibility.public,
                owner_id=users["creator"].id,
            ),
            "lifestyle": Playlist(
                title="Рецепты и лайфстайл",
                description="Уютные видео для хорошего вечера.",
                visibility=Visibility.public,
                owner_id=users["maria"].id,
            ),
            "private": Playlist(
                title="Избранное",
                description="Личная подборка.",
                visibility=Visibility.private,
                owner_id=users["user"].id,
            ),
        }
        self.db.add_all(list(playlists.values()))
        self.db.commit()
        for playlist in playlists.values():
            self.db.refresh(playlist)

        position_by_playlist: dict[int, int] = {}
        for key, title in self.PLAYLIST_ITEMS:
            playlist = playlists[key]
            video = videos.get(title)
            if video is None:
                continue
            position = position_by_playlist.get(playlist.id, 0) + 1
            position_by_playlist[playlist.id] = position
            self.db.add(PlaylistItem(playlist_id=playlist.id, video_id=video.id, position=position))

    def _create_history(self, users: dict[str, User], videos: dict[str, Video], now: datetime) -> None:
        for username, title in self.HISTORY_ITEMS:
            video = videos.get(title)
            if video is None:
                continue
            self.db.add(
                WatchHistory(
                    user_id=users[username].id,
                    video_id=video.id,
                    watched_at=now - timedelta(hours=3),
                    position_seconds=12,
                )
            )

    def _create_reports(self, users: dict[str, User], videos: dict[str, Video], now: datetime) -> None:
        reported_video = videos.get("Обзор нового смартфона: честный тест")
        hidden_video = videos.get("Скрытый ролик: пример модерации")
        pasta_video = videos.get("Как приготовить пасту за 15 минут")

        if reported_video is not None:
            self.db.add(
                Report(
                    video_id=reported_video.id,
                    reporter_id=users["user"].id,
                    category="inappropriate",
                    reason="В видео есть спорное утверждение о характеристиках устройства.",
                    status=ReportStatus.open,
                )
            )
        if hidden_video is not None:
            self.db.add(
                Report(
                    video_id=hidden_video.id,
                    reporter_id=users["maria"].id,
                    category="spam",
                    reason="Подозрительное содержимое и вводящее в заблуждение название.",
                    status=ReportStatus.resolved,
                    resolved_at=now - timedelta(days=1),
                    resolved_by_id=users["moderator"].id,
                    resolution_note="Видео скрыто модератором.",
                )
            )
        if pasta_video is not None:
            self.db.add(
                Report(
                    video_id=pasta_video.id,
                    reporter_id=users["creator"].id,
                    category="other",
                    reason="Проверка очереди жалоб.",
                    status=ReportStatus.dismissed,
                    resolved_at=now - timedelta(days=2),
                    resolved_by_id=users["moderator"].id,
                    resolution_note="Нарушений не найдено.",
                )
            )
