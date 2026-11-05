import math
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..metrics import metrics
from ..models import (
    Like,
    Report,
    ReportStatus,
    User,
    Video,
    VideoAccess,
    VideoRendition,
    VideoStatus,
    Visibility,
    WatchHistory,
)
from ..permissions import AccessPolicy
from ..schemas import (
    AccessIn,
    AccessOut,
    MessageOut,
    ReactionIn,
    ReactionOut,
    ReportIn,
    VideoOut,
    VideoUpdate,
    ViewIn,
    ViewOut,
)
from ..serializers import user_public, video_out
from ..services.editor import ALLOWED_QUALITY_VARIANTS, QUALITY_HEIGHTS, EditOptions, editor
from ..services.media import media_service
from ..services.streaming import streamer

router = APIRouter(prefix="/api/videos", tags=["Видео"])

CONTENT_TYPE_BY_EXT = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".m4v": "video/x-m4v",
}


def get_video_or_404(db: Session, video_id: int) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Видео не найдено")
    return video


def require_view(policy: AccessPolicy, video: Video, viewer: User | None) -> None:
    if not policy.can_view_video(video, viewer):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому видео")


def require_manage(policy: AccessPolicy, video: Video, viewer: User) -> None:
    if not policy.can_manage_video(video, viewer):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")


@router.post("", response_model=VideoOut, status_code=status.HTTP_201_CREATED, summary="Загрузить видео")
def upload_video(
    title: str = Form(..., min_length=1, max_length=200),
    file: UploadFile = File(...),
    description: str = Form(""),
    visibility: Visibility = Form(Visibility.public),
    thumbnail: UploadFile | None = File(None),
    trim_start: float = Form(0.0),
    trim_end: float | None = Form(None),
    rotate: int = Form(0),
    flip_horizontal: bool = Form(False),
    flip_vertical: bool = Form(False),
    crop_aspect: str = Form("original"),
    video_filter: str = Form("none"),
    speed: float = Form(1.0),
    mute: bool = Form(False),
    volume: float = Form(1.0),
    thumbnail_timestamp: float | None = Form(None),
    qualities: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    title = title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название не может быть пустым")
    if len(description) > 10000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Описание слишком длинное")

    extension = media_service.video_extension(file.filename, file.content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются видеоформаты MP4, WebM, MOV и M4V",
        )

    thumb_extension = None
    if thumbnail is not None and thumbnail.filename:
        thumb_extension = media_service.image_extension(thumbnail.filename, thumbnail.content_type)
        if thumb_extension is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Превью должно быть изображением JPG, PNG или WebP",
            )

    options = EditOptions(
        trim_start=trim_start,
        trim_end=trim_end,
        rotate=rotate,
        flip_horizontal=flip_horizontal,
        flip_vertical=flip_vertical,
        crop_aspect=crop_aspect,
        video_filter=video_filter,
        speed=speed,
        mute=mute,
        volume=volume,
    )
    options.validate()
    if thumbnail_timestamp is not None and (
        not math.isfinite(thumbnail_timestamp) or thumbnail_timestamp < 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректное время кадра для превью",
        )

    requested_qualities: list[str] = []
    for raw_quality in qualities.replace(" ", ",").split(","):
        quality = raw_quality.strip().lower()
        if not quality or quality == "original":
            continue
        if quality not in ALLOWED_QUALITY_VARIANTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недопустимое качество видео",
            )
        if quality not in requested_qualities:
            requested_qualities.append(quality)

    media_service.ensure_dirs()
    stem = uuid.uuid4().hex
    video_rel = f"videos/{stem}{extension}"
    video_path = settings.media_dir / video_rel
    thumb_rel = f"thumbnails/{stem}.jpg"
    thumb_path = settings.media_dir / thumb_rel
    processed_path = None
    rendition_files: list[str] = []
    rendition_rows: list[dict] = []
    video: Video | None = None

    def cleanup_files() -> None:
        if processed_path is not None:
            processed_path.unlink(missing_ok=True)
        media_service.delete_file(video_rel)
        media_service.delete_file(thumb_rel)
        for rendition_rel in rendition_files:
            media_service.delete_file(rendition_rel)

    size_bytes = media_service.save_upload(file, video_path, settings.max_upload_mb * 1024 * 1024)

    try:
        original_duration = media_service.probe_duration(video_path)
        options.validate_duration(original_duration)

        if options.has_edits:
            processed_path = settings.media_dir / f"videos/{stem}-edited.mp4"
            editor.process(video_path, processed_path, options)
            media_service.delete_file(video_rel)
            video_rel = f"videos/{stem}.mp4"
            video_path = settings.media_dir / video_rel
            processed_path.replace(video_path)
            processed_path = None
            extension = ".mp4"
            size_bytes = video_path.stat().st_size

        if thumbnail_timestamp is not None:
            final_duration = media_service.probe_duration(video_path)
            timestamp = max(0.0, thumbnail_timestamp)
            if final_duration is not None:
                timestamp = min(timestamp, max(0.0, final_duration - 0.1))
            has_thumb = editor.extract_frame(video_path, thumb_path, timestamp)
            if not has_thumb:
                has_thumb = media_service.generate_thumbnail(video_path, thumb_path, final_duration)
        elif thumb_extension is not None and thumbnail is not None:
            thumb_rel = f"thumbnails/{stem}{thumb_extension}"
            thumb_path = settings.media_dir / thumb_rel
            media_service.save_upload(thumbnail, thumb_path, settings.max_thumbnail_mb * 1024 * 1024)
            has_thumb = True
        else:
            duration_for_thumb = media_service.probe_duration(video_path)
            has_thumb = media_service.generate_thumbnail(video_path, thumb_path, duration_for_thumb)

        dimensions = editor.probe_dimensions(video_path)
        if dimensions is not None:
            source_height = dimensions[1]
            for quality in requested_qualities:
                target_height = QUALITY_HEIGHTS[quality]
                if source_height <= target_height:
                    continue
                rendition_rel = f"videos/{stem}-{quality}.mp4"
                rendition_path = settings.media_dir / rendition_rel
                editor.create_rendition(video_path, rendition_path, target_height)
                rendition_files.append(rendition_rel)
                rendition_width, rendition_height = editor.probe_dimensions(rendition_path) or (None, None)
                rendition_rows.append(
                    {
                        "quality": quality,
                        "storage_path": rendition_rel,
                        "content_type": "video/mp4",
                        "size_bytes": rendition_path.stat().st_size,
                        "width": rendition_width,
                        "height": rendition_height,
                    }
                )

        duration = media_service.probe_duration(video_path)
        content_type = CONTENT_TYPE_BY_EXT.get(extension) or file.content_type or "video/mp4"

        video = Video(
            title=title,
            description=description.strip(),
            visibility=visibility,
            storage_path=video_rel,
            thumbnail_path=thumb_rel if has_thumb else None,
            original_filename=file.filename or f"video{extension}",
            content_type=content_type,
            size_bytes=size_bytes,
            duration_seconds=duration,
            owner_id=user.id,
        )
        db.add(video)
        db.flush()
        for row in rendition_rows:
            db.add(VideoRendition(video_id=video.id, **row))
        db.commit()
        db.refresh(video)
    except HTTPException:
        db.rollback()
        cleanup_files()
        raise
    except Exception:
        db.rollback()
        cleanup_files()
        raise

    assert video is not None
    metrics.record_upload(size_bytes)
    return video_out(video, user)


@router.get("/{video_id}", response_model=VideoOut, summary="Получить видео")
def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_view(policy, video, viewer)
    reaction = None
    if viewer is not None:
        reaction = db.scalar(select(Like.value).where(Like.user_id == viewer.id, Like.video_id == video.id))
    return video_out(
        video,
        viewer,
        my_reaction=reaction,
        subscribed=policy.is_subscribed(viewer, video.owner_id),
    )


@router.patch("/{video_id}", response_model=VideoOut, summary="Изменить метаданные видео")
def update_video(
    video_id: int,
    payload: VideoUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_manage(policy, video, user)
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название не может быть пустым")
        video.title = title
    if payload.description is not None:
        video.description = payload.description.strip()
    if payload.visibility is not None:
        video.visibility = payload.visibility
    db.add(video)
    db.commit()
    db.refresh(video)
    return video_out(video, user, subscribed=policy.is_subscribed(user, video.owner_id))


@router.post("/{video_id}/thumbnail", response_model=VideoOut, summary="Заменить превью")
def replace_thumbnail(
    video_id: int,
    thumbnail: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_manage(policy, video, user)
    extension = media_service.image_extension(thumbnail.filename, thumbnail.content_type)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужно изображение JPG, PNG или WebP")
    media_service.ensure_dirs()
    stem = uuid.uuid4().hex
    thumb_rel = f"thumbnails/{stem}{extension}"
    media_service.save_upload(thumbnail, settings.media_dir / thumb_rel, settings.max_thumbnail_mb * 1024 * 1024)
    old = video.thumbnail_path
    video.thumbnail_path = thumb_rel
    db.add(video)
    db.commit()
    db.refresh(video)
    media_service.delete_file(old)
    return video_out(video, user)


@router.delete("/{video_id}", response_model=MessageOut, summary="Удалить видео")
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_manage(policy, video, user)
    storage_path = video.storage_path
    thumb_path = video.thumbnail_path
    rendition_paths = [item.storage_path for item in video.renditions]
    db.delete(video)
    db.commit()
    media_service.delete_file(storage_path)
    media_service.delete_file(thumb_path)
    for rendition_path in rendition_paths:
        media_service.delete_file(rendition_path)
    return MessageOut(message="Видео удалено")


@router.get("/{video_id}/stream", summary="Поток видео (HTTP Range)")
def stream_video(
    video_id: int,
    request: Request,
    quality: str | None = Query(None),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_view(policy, video, viewer)
    requested = (quality or "").strip().lower()
    if requested and requested != "original":
        rendition = db.scalar(
            select(VideoRendition).where(
                VideoRendition.video_id == video.id,
                VideoRendition.quality == requested,
            )
        )
        if rendition is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Качество недоступно")
        return streamer.stream(video, request, rendition.storage_path, rendition.content_type)
    return streamer.stream(video, request)


@router.get("/{video_id}/thumbnail", summary="Превью видео")
def video_thumbnail(
    video_id: int,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_view(policy, video, viewer)
    return streamer.thumbnail(video)


@router.post("/{video_id}/view", response_model=ViewOut, summary="Отметить просмотр")
def mark_view(
    video_id: int,
    payload: ViewIn,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_view(policy, video, viewer)
    video.views_count = (video.views_count or 0) + 1
    if viewer is not None:
        history = db.scalar(
            select(WatchHistory).where(WatchHistory.user_id == viewer.id, WatchHistory.video_id == video.id)
        )
        if history is None:
            db.add(
                WatchHistory(
                    user_id=viewer.id,
                    video_id=video.id,
                    position_seconds=payload.position_seconds,
                )
            )
        else:
            history.watched_at = datetime.now(timezone.utc)
            history.position_seconds = payload.position_seconds
            db.add(history)
    db.add(video)
    db.commit()
    metrics.record_view()
    return ViewOut(views_count=video.views_count)


@router.post("/{video_id}/reaction", response_model=ReactionOut, summary="Лайк / дизлайк")
def react(
    video_id: int,
    payload: ReactionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_view(policy, video, user)
    existing = db.scalar(select(Like).where(Like.user_id == user.id, Like.video_id == video.id))
    if payload.value == 0:
        if existing is not None:
            db.delete(existing)
    elif existing is None:
        db.add(Like(user_id=user.id, video_id=video.id, value=payload.value))
    else:
        existing.value = payload.value
        db.add(existing)
    db.commit()
    db.refresh(video)
    my_reaction = db.scalar(select(Like.value).where(Like.user_id == user.id, Like.video_id == video.id))
    return ReactionOut(
        likes_count=video.likes_count or 0,
        dislikes_count=video.dislikes_count or 0,
        my_reaction=my_reaction,
    )


@router.get("/{video_id}/access", response_model=AccessOut, summary="Список доступа к приватному видео")
def get_access(
    video_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_manage(policy, video, user)
    users = db.scalars(
        select(User).join(VideoAccess, VideoAccess.user_id == User.id).where(VideoAccess.video_id == video.id)
    ).unique().all()
    return AccessOut(users=[user_public(item) for item in users])


@router.post("/{video_id}/access", response_model=AccessOut, summary="Разрешить пользователю приватное видео")
def add_access(
    video_id: int,
    payload: AccessIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_manage(policy, video, user)
    target = db.scalar(select(User).where(User.username == payload.username.strip()))
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    if target.id == video.owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Владелец уже имеет доступ")
    existing = db.scalar(
        select(VideoAccess).where(VideoAccess.video_id == video.id, VideoAccess.user_id == target.id)
    )
    if existing is None:
        db.add(VideoAccess(video_id=video.id, user_id=target.id))
        db.commit()
    users = db.scalars(
        select(User).join(VideoAccess, VideoAccess.user_id == User.id).where(VideoAccess.video_id == video.id)
    ).unique().all()
    return AccessOut(users=[user_public(item) for item in users])


@router.delete("/{video_id}/access/{target_user_id}", response_model=AccessOut, summary="Забрать доступ")
def remove_access(
    video_id: int,
    target_user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_manage(policy, video, user)
    access = db.scalar(
        select(VideoAccess).where(VideoAccess.video_id == video.id, VideoAccess.user_id == target_user_id)
    )
    if access is not None:
        db.delete(access)
        db.commit()
    users = db.scalars(
        select(User).join(VideoAccess, VideoAccess.user_id == User.id).where(VideoAccess.video_id == video.id)
    ).unique().all()
    return AccessOut(users=[user_public(item) for item in users])


@router.post("/{video_id}/report", response_model=MessageOut, summary="Пожаловаться на видео")
def report_video(
    video_id: int,
    payload: ReportIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_view(policy, video, user)
    existing = db.scalar(
        select(Report).where(
            Report.video_id == video.id,
            Report.reporter_id == user.id,
            Report.status == ReportStatus.open,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Вы уже отправили жалобу на это видео")
    db.add(
        Report(
            video_id=video.id,
            reporter_id=user.id,
            category=payload.category.value,
            reason=(payload.reason or "").strip() or None,
        )
    )
    db.commit()
    metrics.record_report(payload.category.value)
    return MessageOut(message="Жалоба отправлена модераторам")


@router.get("/{video_id}/related", response_model=list[VideoOut], summary="Похожие видео")
def related_videos(
    video_id: int,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
    limit: int = Query(12, ge=1, le=30),
):
    video = get_video_or_404(db, video_id)
    policy = AccessPolicy(db)
    require_view(policy, video, viewer)
    same_owner = case((Video.owner_id == video.owner_id, 0), else_=1)
    items = db.scalars(
        select(Video)
        .where(
            Video.id != video.id,
            Video.status == VideoStatus.published,
            Video.visibility == Visibility.public,
        )
        .order_by(same_owner, Video.views_count.desc(), Video.created_at.desc())
        .limit(limit)
    ).unique().all()
    return [video_out(item, viewer) for item in items]
