from .models import Comment, Playlist, PlaylistItem, Report, Role, User, Video
from .schemas import (
    AdminUserOut,
    ChannelOut,
    CommentOut,
    PlaylistDetail,
    PlaylistItemOut,
    PlaylistOut,
    ReportOut,
    UserMe,
    UserPublic,
    VideoOut,
    VideoQualityOut,
)

QUALITY_LABELS = {
    "original": "Оригинал",
    "1080p": "1080p",
    "720p": "720p",
    "480p": "480p",
}
QUALITY_ORDER = {"original": 0, "1080p": 1, "720p": 2, "480p": 3}


def video_qualities(video: Video) -> list[VideoQualityOut]:
    qualities = [
        VideoQualityOut(
            quality="original",
            label=QUALITY_LABELS["original"],
            stream_url=f"/api/videos/{video.id}/stream",
            size_bytes=video.size_bytes,
        )
    ]
    for rendition in sorted(video.renditions or [], key=lambda item: QUALITY_ORDER.get(item.quality, 99)):
        qualities.append(
            VideoQualityOut(
                quality=rendition.quality,
                label=QUALITY_LABELS.get(rendition.quality, rendition.quality),
                stream_url=f"/api/videos/{video.id}/stream?quality={rendition.quality}",
                width=rendition.width,
                height=rendition.height,
                size_bytes=rendition.size_bytes,
            )
        )
    return qualities


def user_public(user: User) -> UserPublic:
    return UserPublic.model_validate(user)


def user_me(
    user: User,
    videos_count: int = 0,
    subscribers_count: int = 0,
    subscriptions_count: int = 0,
) -> UserMe:
    base = user_public(user).model_dump()
    return UserMe(
        **base,
        email=user.email,
        is_active=user.is_active,
        videos_count=videos_count,
        subscribers_count=subscribers_count,
        subscriptions_count=subscriptions_count,
    )


def video_out(
    video: Video,
    viewer: User | None = None,
    my_reaction: int | None = None,
    subscribed: bool = False,
) -> VideoOut:
    is_owner = viewer is not None and video.owner_id == viewer.id
    can_manage = viewer is not None and (is_owner or viewer.role == Role.admin)
    return VideoOut(
        id=video.id,
        title=video.title,
        description=video.description,
        visibility=video.visibility,
        status=video.status,
        thumbnail_url=f"/api/videos/{video.id}/thumbnail",
        stream_url=f"/api/videos/{video.id}/stream",
        qualities=video_qualities(video),
        duration_seconds=video.duration_seconds,
        size_bytes=video.size_bytes,
        original_filename=video.original_filename,
        created_at=video.created_at,
        updated_at=video.updated_at,
        views_count=video.views_count,
        likes_count=video.likes_count or 0,
        dislikes_count=video.dislikes_count or 0,
        comments_count=video.comments_count or 0,
        access_count=video.access_count or 0,
        owner=user_public(video.owner),
        is_owner=is_owner,
        can_manage=can_manage,
        my_reaction=my_reaction,
        is_subscribed=subscribed,
    )


def channel_out(user: User, subscribers_count: int, videos_count: int, viewer: User | None, subscribed: bool) -> ChannelOut:
    return ChannelOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        role=user.role,
        created_at=user.created_at,
        subscribers_count=subscribers_count,
        videos_count=videos_count,
        is_subscribed=subscribed,
        is_owner=viewer is not None and viewer.id == user.id,
    )


def comment_out(comment: Comment, video: Video, viewer: User | None) -> CommentOut:
    can_delete = False
    if viewer is not None:
        can_delete = (
            comment.user_id == viewer.id
            or video.owner_id == viewer.id
            or viewer.role in (Role.moderator, Role.admin)
        )
    return CommentOut(
        id=comment.id,
        video_id=comment.video_id,
        parent_id=comment.parent_id,
        text=comment.text,
        created_at=comment.created_at,
        user=user_public(comment.user),
        can_delete=can_delete,
    )


def playlist_out(
    playlist: Playlist,
    viewer: User | None,
    items_count: int | None = None,
    cover_url: str | None = None,
) -> PlaylistOut:
    count = len(playlist.items) if items_count is None else items_count
    if cover_url is None and playlist.items:
        first = playlist.items[0]
        if first.video is not None:
            cover_url = f"/api/videos/{first.video_id}/thumbnail"
    return PlaylistOut(
        id=playlist.id,
        title=playlist.title,
        description=playlist.description,
        visibility=playlist.visibility,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
        owner=user_public(playlist.owner),
        items_count=count,
        cover_url=cover_url,
        is_owner=viewer is not None and (playlist.owner_id == viewer.id or viewer.role == Role.admin),
    )


def playlist_detail_out(
    playlist: Playlist,
    viewer: User | None,
    items: list[PlaylistItem],
) -> PlaylistDetail:
    base = playlist_out(playlist, viewer, items_count=len(items))
    return PlaylistDetail(
        **base.model_dump(),
        items=[
            PlaylistItemOut(id=item.id, position=item.position, video=video_out(item.video, viewer))
            for item in items
        ],
    )


def report_out(report: Report, viewer: User | None) -> ReportOut:
    return ReportOut(
        id=report.id,
        category=report.category,
        reason=report.reason,
        status=report.status,
        created_at=report.created_at,
        resolved_at=report.resolved_at,
        resolution_note=report.resolution_note,
        video=video_out(report.video, viewer),
        reporter=user_public(report.reporter),
        resolved_by=user_public(report.resolved_by) if report.resolved_by else None,
    )


def admin_user_out(
    user: User,
    videos_count: int,
    subscribers_count: int,
    subscriptions_count: int,
) -> AdminUserOut:
    base = user_public(user).model_dump()
    return AdminUserOut(
        **base,
        email=user.email,
        is_active=user.is_active,
        videos_count=videos_count,
        subscribers_count=subscribers_count,
        subscriptions_count=subscriptions_count,
    )
