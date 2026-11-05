from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..models import Playlist, PlaylistItem, Role, User, Video, Visibility
from ..permissions import AccessPolicy
from ..schemas import (
    MessageOut,
    PlaylistDetail,
    PlaylistIn,
    PlaylistItemIn,
    PlaylistOrderIn,
    PlaylistOut,
    PlaylistUpdate,
)
from ..serializers import playlist_detail_out, playlist_out

router = APIRouter(prefix="/api", tags=["Плейлисты"])


def get_playlist_or_404(db: Session, playlist_id: int) -> Playlist:
    playlist = db.scalar(
        select(Playlist)
        .where(Playlist.id == playlist_id)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.video))
        .execution_options(populate_existing=True)
    )
    if playlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Плейлист не найден")
    return playlist


def require_playlist_owner(policy: AccessPolicy, playlist: Playlist, user: User) -> None:
    if not policy.can_manage_playlist(playlist, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")


@router.post("/playlists", response_model=PlaylistOut, status_code=status.HTTP_201_CREATED, summary="Создать плейлист")
def create_playlist(
    payload: PlaylistIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlist = Playlist(
        title=payload.title.strip(),
        description=payload.description.strip(),
        visibility=payload.visibility,
        owner_id=user.id,
    )
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist_out(playlist, user, items_count=0)


@router.get("/me/playlists", response_model=list[PlaylistOut], summary="Мои плейлисты")
def my_playlists(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlists = db.scalars(
        select(Playlist)
        .where(Playlist.owner_id == user.id)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.video))
        .order_by(Playlist.updated_at.desc())
    ).unique().all()
    return [playlist_out(item, user) for item in playlists]


@router.get("/playlists/{playlist_id}", response_model=PlaylistDetail, summary="Плейлист")
def get_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    playlist = get_playlist_or_404(db, playlist_id)
    policy = AccessPolicy(db)
    is_owner = viewer is not None and (playlist.owner_id == viewer.id or viewer.role == Role.admin)
    if playlist.visibility == Visibility.private and not is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Это приватный плейлист")
    items = (
        playlist.items
        if is_owner
        else [item for item in playlist.items if policy.can_view_video(item.video, viewer)]
    )
    return playlist_detail_out(playlist, viewer, items)


@router.patch("/playlists/{playlist_id}", response_model=PlaylistOut, summary="Изменить плейлист")
def update_playlist(
    playlist_id: int,
    payload: PlaylistUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlist = get_playlist_or_404(db, playlist_id)
    policy = AccessPolicy(db)
    require_playlist_owner(policy, playlist, user)
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название не может быть пустым")
        playlist.title = title
    if payload.description is not None:
        playlist.description = payload.description.strip()
    if payload.visibility is not None:
        playlist.visibility = payload.visibility
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist_out(playlist, user)


@router.delete("/playlists/{playlist_id}", response_model=MessageOut, summary="Удалить плейлист")
def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlist = get_playlist_or_404(db, playlist_id)
    policy = AccessPolicy(db)
    require_playlist_owner(policy, playlist, user)
    db.delete(playlist)
    db.commit()
    return MessageOut(message="Плейлист удалён")


@router.post(
    "/playlists/{playlist_id}/items",
    response_model=PlaylistDetail,
    summary="Добавить видео в плейлист",
)
def add_item(
    playlist_id: int,
    payload: PlaylistItemIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlist = get_playlist_or_404(db, playlist_id)
    policy = AccessPolicy(db)
    require_playlist_owner(policy, playlist, user)
    video = db.get(Video, payload.video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Видео не найдено")
    if not policy.can_view_video(video, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому видео")
    existing = db.scalar(
        select(PlaylistItem).where(
            PlaylistItem.playlist_id == playlist.id,
            PlaylistItem.video_id == video.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Видео уже есть в плейлисте")
    max_position = (
        db.scalar(select(func.max(PlaylistItem.position)).where(PlaylistItem.playlist_id == playlist.id)) or 0
    )
    db.add(PlaylistItem(playlist_id=playlist.id, video_id=video.id, position=max_position + 1))
    db.commit()
    playlist = get_playlist_or_404(db, playlist_id)
    return playlist_detail_out(playlist, user, playlist.items)


@router.delete(
    "/playlists/{playlist_id}/items/{item_id}",
    response_model=PlaylistDetail,
    summary="Удалить видео из плейлиста",
)
def remove_item(
    playlist_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlist = get_playlist_or_404(db, playlist_id)
    policy = AccessPolicy(db)
    require_playlist_owner(policy, playlist, user)
    item = db.get(PlaylistItem, item_id)
    if item is None or item.playlist_id != playlist.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Элемент плейлиста не найден")
    db.delete(item)
    db.commit()
    playlist = get_playlist_or_404(db, playlist_id)
    return playlist_detail_out(playlist, user, playlist.items)


@router.put(
    "/playlists/{playlist_id}/order",
    response_model=PlaylistDetail,
    summary="Изменить порядок видео",
)
def reorder_items(
    playlist_id: int,
    payload: PlaylistOrderIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlist = get_playlist_or_404(db, playlist_id)
    policy = AccessPolicy(db)
    require_playlist_owner(policy, playlist, user)
    by_id = {item.id: item for item in playlist.items}
    if set(payload.item_ids) != set(by_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Передан неполный список элементов")
    for position, item_id in enumerate(payload.item_ids):
        by_id[item_id].position = position
        db.add(by_id[item_id])
    db.commit()
    playlist = get_playlist_or_404(db, playlist_id)
    return playlist_detail_out(playlist, user, playlist.items)
