from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..models import Playlist, PlaylistItem, Role, Subscription, User, Video, VideoStatus, Visibility
from ..pagination import paginate
from ..permissions import AccessPolicy
from ..schemas import ChannelOut, PlaylistPage, VideoPage
from ..serializers import channel_out, playlist_out, video_out

router = APIRouter(prefix="/api", tags=["Каналы и подписки"])


def get_channel_or_404(db: Session, username: str) -> User:
    channel = db.scalar(select(User).where(User.username == username))
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Канал не найден")
    return channel


def channel_counts(db: Session, channel: User) -> tuple[int, int]:
    subscribers = db.scalar(select(func.count(Subscription.id)).where(Subscription.channel_id == channel.id)) or 0
    videos = (
        db.scalar(
            select(func.count(Video.id)).where(
                Video.owner_id == channel.id,
                Video.status == VideoStatus.published,
                Video.visibility == Visibility.public,
            )
        )
        or 0
    )
    return subscribers, videos


@router.get("/channels/{username}", response_model=ChannelOut, summary="Информация о канале")
def get_channel(
    username: str,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    channel = get_channel_or_404(db, username)
    subscribers, videos = channel_counts(db, channel)
    policy = AccessPolicy(db)
    return channel_out(channel, subscribers, videos, viewer, policy.is_subscribed(viewer, channel.id))


@router.get("/channels/{username}/videos", response_model=VideoPage, summary="Видео канала")
def channel_videos(
    username: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    channel = get_channel_or_404(db, username)
    stmt = select(Video).where(Video.owner_id == channel.id)
    if viewer is None or (viewer.id != channel.id and viewer.role != Role.admin):
        stmt = stmt.where(Video.status == VideoStatus.published, Video.visibility == Visibility.public)
    stmt = stmt.order_by(Video.created_at.desc())
    items, total, page, page_size, pages = paginate(db, stmt, page, page_size)
    policy = AccessPolicy(db)
    subscribed = policy.is_subscribed(viewer, channel.id)
    return VideoPage(
        items=[video_out(video, viewer, subscribed=subscribed) for video in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/channels/{username}/playlists", response_model=PlaylistPage, summary="Плейлисты канала")
def channel_playlists(
    username: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    channel = get_channel_or_404(db, username)
    stmt = (
        select(Playlist)
        .where(Playlist.owner_id == channel.id)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.video))
        .order_by(Playlist.created_at.desc())
    )
    if viewer is None or (viewer.id != channel.id and viewer.role != Role.admin):
        stmt = stmt.where(Playlist.visibility == Visibility.public)
    items, total, page, page_size, pages = paginate(db, stmt, page, page_size)
    return PlaylistPage(
        items=[playlist_out(item, viewer) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/channels/{username}/subscribe", response_model=ChannelOut, summary="Подписаться на канал")
def subscribe(
    username: str,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    channel = get_channel_or_404(db, username)
    if channel.id == viewer.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя подписаться на себя")
    existing = db.scalar(
        select(Subscription).where(
            Subscription.subscriber_id == viewer.id,
            Subscription.channel_id == channel.id,
        )
    )
    if existing is None:
        db.add(Subscription(subscriber_id=viewer.id, channel_id=channel.id))
        db.commit()
    subscribers, videos = channel_counts(db, channel)
    return channel_out(channel, subscribers, videos, viewer, True)


@router.delete("/channels/{username}/subscribe", response_model=ChannelOut, summary="Отписаться от канала")
def unsubscribe(
    username: str,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    channel = get_channel_or_404(db, username)
    existing = db.scalar(
        select(Subscription).where(
            Subscription.subscriber_id == viewer.id,
            Subscription.channel_id == channel.id,
        )
    )
    if existing is not None:
        db.delete(existing)
        db.commit()
    subscribers, videos = channel_counts(db, channel)
    return channel_out(channel, subscribers, videos, viewer, False)


@router.get("/me/subscriptions", response_model=list[ChannelOut], summary="Мои подписки")
def my_subscriptions(
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    channels = db.scalars(
        select(User)
        .join(Subscription, Subscription.channel_id == User.id)
        .where(Subscription.subscriber_id == viewer.id)
        .order_by(Subscription.created_at.desc())
    ).unique().all()
    result = []
    for channel in channels:
        subscribers, videos = channel_counts(db, channel)
        result.append(channel_out(channel, subscribers, videos, viewer, True))
    return result
