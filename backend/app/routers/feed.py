from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..models import Subscription, User, Video, VideoStatus, Visibility, WatchHistory
from ..pagination import paginate
from ..permissions import AccessPolicy
from ..schemas import HistoryOut, MessageOut, VideoPage
from ..serializers import video_out

router = APIRouter(prefix="/api", tags=["Лента и поиск"])


@router.get("/feed", response_model=VideoPage, summary="Главная лента")
def feed(
    sort: str = Query("new", pattern="^(new|popular)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    stmt = select(Video).where(Video.status == VideoStatus.published, Video.visibility == Visibility.public)
    if sort == "popular":
        stmt = stmt.order_by(Video.views_count.desc(), Video.created_at.desc())
    else:
        stmt = stmt.order_by(Video.created_at.desc())
    items, total, page, page_size, pages = paginate(db, stmt, page, page_size)
    return VideoPage(
        items=[video_out(video, viewer) for video in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/feed/subscriptions", response_model=VideoPage, summary="Лента подписок")
def subscriptions_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    stmt = (
        select(Video)
        .join(Subscription, Subscription.channel_id == Video.owner_id)
        .where(
            Subscription.subscriber_id == viewer.id,
            Video.status == VideoStatus.published,
            Video.visibility == Visibility.public,
        )
        .order_by(Video.created_at.desc())
    )
    items, total, page, page_size, pages = paginate(db, stmt, page, page_size)
    return VideoPage(
        items=[video_out(video, viewer, subscribed=True) for video in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/search", response_model=VideoPage, summary="Поиск по названию")
def search(
    q: str = Query(..., min_length=1, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    query = q.strip()
    stmt = select(Video).where(
        Video.status == VideoStatus.published,
        Video.visibility == Visibility.public,
        Video.title.ilike(f"%{query}%"),
    )
    stmt = stmt.order_by(Video.views_count.desc(), Video.created_at.desc())
    items, total, page, page_size, pages = paginate(db, stmt, page, page_size)
    return VideoPage(
        items=[video_out(video, viewer) for video in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/history", response_model=list[HistoryOut], summary="История просмотров")
def history(
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    rows = db.scalars(
        select(WatchHistory)
        .where(WatchHistory.user_id == viewer.id)
        .order_by(WatchHistory.watched_at.desc())
        .limit(limit)
    ).unique().all()
    policy = AccessPolicy(db)
    result = []
    for row in rows:
        if row.video is not None and policy.can_view_video(row.video, viewer):
            result.append(
                HistoryOut(
                    video=video_out(row.video, viewer),
                    watched_at=row.watched_at,
                    position_seconds=row.position_seconds,
                )
            )
    return result


@router.delete("/history", response_model=MessageOut, summary="Очистить историю")
def clear_history(
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    rows = db.scalars(select(WatchHistory).where(WatchHistory.user_id == viewer.id)).all()
    for row in rows:
        db.delete(row)
    db.commit()
    return MessageOut(message="История очищена")


@router.delete("/history/{video_id}", response_model=MessageOut, summary="Удалить видео из истории")
def delete_history_item(
    video_id: int,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    row = db.scalar(
        select(WatchHistory).where(WatchHistory.user_id == viewer.id, WatchHistory.video_id == video_id)
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Записи нет в истории")
    db.delete(row)
    db.commit()
    return MessageOut(message="Запись удалена из истории")
