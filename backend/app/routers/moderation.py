from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_moderator
from ..models import Report, ReportAction, ReportStatus, User, Video, VideoStatus
from ..pagination import paginate
from ..schemas import HideVideoIn, ReportPage, ReportResolveIn, VideoOut, VideoPage
from ..serializers import report_out, video_out

router = APIRouter(prefix="/api/moderation", tags=["Модерация"])


@router.get("/reports", response_model=ReportPage, summary="Очередь жалоб")
def list_reports(
    status_filter: str = Query("open", alias="status", pattern="^(open|resolved|dismissed|all)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    moderator: User = Depends(require_moderator),
):
    stmt = select(Report).order_by(Report.created_at.desc())
    if status_filter != "all":
        stmt = stmt.where(Report.status == ReportStatus(status_filter))
    items, total, page, page_size, pages = paginate(db, stmt, page, page_size)
    return ReportPage(
        items=[report_out(item, moderator) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/reports/{report_id}/resolve", summary="Обработать жалобу")
def resolve_report(
    report_id: int,
    payload: ReportResolveIn,
    db: Session = Depends(get_db),
    moderator: User = Depends(require_moderator),
):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Жалоба не найдена")
    if report.status != ReportStatus.open:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Жалоба уже обработана")

    now = datetime.now(timezone.utc)
    report.resolved_at = now
    report.resolved_by_id = moderator.id
    report.resolution_note = (payload.note or "").strip() or None

    if payload.action == ReportAction.hide:
        report.status = ReportStatus.resolved
        report.video.status = VideoStatus.hidden
        db.add(report.video)
        others = db.scalars(
            select(Report).where(
                Report.video_id == report.video_id,
                Report.status == ReportStatus.open,
                Report.id != report.id,
            )
        ).all()
        for other in others:
            other.status = ReportStatus.resolved
            other.resolved_at = now
            other.resolved_by_id = moderator.id
            other.resolution_note = "Видео скрыто по другой жалобе"
            db.add(other)
    else:
        report.status = ReportStatus.dismissed

    db.add(report)
    db.commit()
    db.refresh(report)
    return report_out(report, moderator)


@router.get("/videos", response_model=VideoPage, summary="Видео для модерации")
def moderation_videos(
    status_filter: str = Query("hidden", alias="status", pattern="^(hidden|published|all)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
    moderator: User = Depends(require_moderator),
):
    stmt = select(Video).order_by(Video.created_at.desc())
    if status_filter != "all":
        stmt = stmt.where(Video.status == VideoStatus(status_filter))
    items, total, page, page_size, pages = paginate(db, stmt, page, page_size)
    return VideoPage(
        items=[video_out(item, moderator) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/videos/{video_id}/hide", response_model=VideoOut, summary="Скрыть видео")
def hide_video(
    video_id: int,
    payload: HideVideoIn | None = None,
    db: Session = Depends(get_db),
    moderator: User = Depends(require_moderator),
):
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Видео не найдено")
    video.status = VideoStatus.hidden
    db.add(video)
    db.commit()
    db.refresh(video)
    return video_out(video, moderator)


@router.post("/videos/{video_id}/unhide", response_model=VideoOut, summary="Восстановить видео")
def unhide_video(
    video_id: int,
    db: Session = Depends(get_db),
    moderator: User = Depends(require_moderator),
):
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Видео не найдено")
    video.status = VideoStatus.published
    db.add(video)
    db.commit()
    db.refresh(video)
    return video_out(video, moderator)
