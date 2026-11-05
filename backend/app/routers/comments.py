from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..models import Comment, Role, User, Video
from ..permissions import AccessPolicy
from ..schemas import CommentIn, CommentOut, MessageOut
from ..serializers import comment_out

router = APIRouter(prefix="/api", tags=["Комментарии"])


def get_video(db: Session, video_id: int) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Видео не найдено")
    return video


@router.get("/videos/{video_id}/comments", response_model=list[CommentOut], summary="Комментарии к видео")
def list_comments(
    video_id: int,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    video = get_video(db, video_id)
    policy = AccessPolicy(db)
    if not policy.can_view_video(video, viewer):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому видео")
    comments = db.scalars(
        select(Comment).where(Comment.video_id == video.id).order_by(Comment.created_at.asc())
    ).unique().all()
    return [comment_out(comment, video, viewer) for comment in comments]


@router.post(
    "/videos/{video_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить комментарий",
)
def add_comment(
    video_id: int,
    payload: CommentIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    video = get_video(db, video_id)
    policy = AccessPolicy(db)
    if not policy.can_view_video(video, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому видео")
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Комментарий не может быть пустым")
    if payload.parent_id is not None:
        parent = db.get(Comment, payload.parent_id)
        if parent is None or parent.video_id != video.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Родительский комментарий не найден")
    comment = Comment(
        video_id=video.id,
        user_id=user.id,
        parent_id=payload.parent_id,
        text=text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment_out(comment, video, user)


@router.delete("/comments/{comment_id}", response_model=MessageOut, summary="Удалить комментарий")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комментарий не найден")
    video = get_video(db, comment.video_id)
    allowed = (
        comment.user_id == user.id
        or video.owner_id == user.id
        or user.role in (Role.moderator, Role.admin)
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нельзя удалить этот комментарий")
    db.delete(comment)
    db.commit()
    return MessageOut(message="Комментарий удалён")
