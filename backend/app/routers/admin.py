from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import (
    Comment,
    Like,
    Report,
    ReportStatus,
    Subscription,
    User,
    Video,
    VideoStatus,
    Visibility,
)
from ..pagination import paginate
from ..schemas import AdminStats, AdminUserOut, AdminUserPage, AdminUserUpdate
from ..serializers import admin_user_out

router = APIRouter(prefix="/api/admin", tags=["Администрирование"])


def user_counts(db: Session, user: User) -> tuple[int, int, int]:
    videos = db.scalar(select(func.count(Video.id)).where(Video.owner_id == user.id)) or 0
    subscribers = db.scalar(select(func.count(Subscription.id)).where(Subscription.channel_id == user.id)) or 0
    subscriptions = (
        db.scalar(select(func.count(Subscription.id)).where(Subscription.subscriber_id == user.id)) or 0
    )
    return videos, subscribers, subscriptions


@router.get("/stats", response_model=AdminStats, summary="Статистика сервиса")
def stats(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    def count(model, *conditions) -> int:
        return db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0

    return AdminStats(
        users_count=count(User),
        videos_count=count(Video),
        public_videos_count=count(Video, Video.visibility == Visibility.public, Video.status == VideoStatus.published),
        hidden_videos_count=count(Video, Video.status == VideoStatus.hidden),
        private_videos_count=count(Video, Video.visibility == Visibility.private),
        views_total=db.scalar(select(func.coalesce(func.sum(Video.views_count), 0))) or 0,
        comments_count=count(Comment),
        likes_count=count(Like),
        reports_open=count(Report, Report.status == ReportStatus.open),
        subscriptions_count=count(Subscription),
    )


@router.get("/users", response_model=AdminUserPage, summary="Список пользователей")
def list_users(
    q: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    stmt = select(User).order_by(User.created_at.desc())
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                User.username.ilike(pattern),
                User.email.ilike(pattern),
                User.display_name.ilike(pattern),
            )
        )
    items, total, page, page_size, pages = paginate(db, stmt, page, page_size)
    result = []
    for user in items:
        videos, subscribers, subscriptions = user_counts(db, user)
        result.append(admin_user_out(user, videos, subscribers, subscriptions))
    return AdminUserPage(items=result, total=total, page=page, page_size=page_size, pages=pages)


@router.patch("/users/{user_id}", response_model=AdminUserOut, summary="Изменить роль или блокировку")
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    if user.id == admin.id:
        if payload.role is not None and payload.role != admin.role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя изменить свою роль")
        if payload.is_active is not None and payload.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя заблокировать себя")
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    videos, subscribers, subscriptions = user_counts(db, user)
    return admin_user_out(user, videos, subscribers, subscriptions)
