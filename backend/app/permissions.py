from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Playlist, Role, Subscription, User, Video, VideoAccess, VideoStatus, Visibility


class AccessPolicy:
    """Единая точка проверки прав на видео, плейлисты и подписки."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def can_view_video(self, video: Video, user: User | None) -> bool:
        if user is not None and user.role in (Role.admin, Role.moderator):
            return True
        if user is not None and video.owner_id == user.id:
            return True
        if video.status != VideoStatus.published:
            return False
        if video.visibility in (Visibility.public, Visibility.unlisted):
            return True
        if video.visibility == Visibility.private and user is not None:
            allowed = self.db.scalar(
                select(VideoAccess.id).where(
                    VideoAccess.video_id == video.id,
                    VideoAccess.user_id == user.id,
                )
            )
            return allowed is not None
        return False

    def can_manage_video(self, video: Video, user: User | None) -> bool:
        if user is None:
            return False
        return user.id == video.owner_id or user.role == Role.admin

    def is_subscribed(self, subscriber: User | None, channel_id: int) -> bool:
        if subscriber is None:
            return False
        return (
            self.db.scalar(
                select(Subscription.id).where(
                    Subscription.subscriber_id == subscriber.id,
                    Subscription.channel_id == channel_id,
                )
            )
            is not None
        )

    def can_manage_playlist(self, playlist: Playlist, user: User | None) -> bool:
        if user is None:
            return False
        return playlist.owner_id == user.id or user.role == Role.admin
