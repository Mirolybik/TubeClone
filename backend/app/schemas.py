from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import ReportAction, ReportCategory, ReportStatus, Role, VideoStatus, Visibility


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Users / auth ----------


class UserPublic(ORMModel):
    id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    role: Role
    bio: str | None = None
    created_at: datetime


class UserMe(UserPublic):
    email: str
    is_active: bool
    videos_count: int = 0
    subscribers_count: int = 0
    subscriptions_count: int = 0


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    display_name: str | None = Field(default=None, max_length=80)
    password: str = Field(min_length=6, max_length=72)


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=72)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    bio: str | None = Field(default=None, max_length=1000)


class AuthOut(BaseModel):
    user: UserMe


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Channels ----------


class ChannelOut(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    role: Role
    created_at: datetime
    subscribers_count: int
    videos_count: int
    is_subscribed: bool
    is_owner: bool


# ---------- Videos ----------


class VideoQualityOut(BaseModel):
    quality: str
    label: str
    stream_url: str
    width: int | None = None
    height: int | None = None
    size_bytes: int | None = None


class VideoOut(BaseModel):
    id: int
    title: str
    description: str
    visibility: Visibility
    status: VideoStatus
    thumbnail_url: str
    stream_url: str
    qualities: list[VideoQualityOut] = Field(default_factory=list)
    duration_seconds: float | None = None
    size_bytes: int
    original_filename: str
    created_at: datetime
    updated_at: datetime
    views_count: int
    likes_count: int
    dislikes_count: int
    comments_count: int
    access_count: int
    owner: UserPublic
    is_owner: bool = False
    can_manage: bool = False
    my_reaction: int | None = None
    is_subscribed: bool = False


class VideoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    visibility: Visibility | None = None


class ReactionIn(BaseModel):
    value: int = Field(ge=-1, le=1)


class ReactionOut(BaseModel):
    likes_count: int
    dislikes_count: int
    my_reaction: int | None = None


class ViewIn(BaseModel):
    position_seconds: float = Field(default=0, ge=0)


class ViewOut(BaseModel):
    views_count: int


class AccessIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)


class AccessOut(BaseModel):
    users: list[UserPublic]


# ---------- Comments ----------


class CommentIn(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    parent_id: int | None = None


class CommentOut(BaseModel):
    id: int
    video_id: int
    parent_id: int | None
    text: str
    created_at: datetime
    user: UserPublic
    can_delete: bool = False


# ---------- Playlists ----------


class PlaylistIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    visibility: Visibility = Visibility.public


class PlaylistUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    visibility: Visibility | None = None


class PlaylistItemOut(BaseModel):
    id: int
    position: int
    video: VideoOut


class PlaylistOut(BaseModel):
    id: int
    title: str
    description: str
    visibility: Visibility
    created_at: datetime
    updated_at: datetime
    owner: UserPublic
    items_count: int
    cover_url: str | None = None
    is_owner: bool = False


class PlaylistDetail(PlaylistOut):
    items: list[PlaylistItemOut]


class PlaylistItemIn(BaseModel):
    video_id: int


class PlaylistOrderIn(BaseModel):
    item_ids: list[int]


# ---------- Reports / moderation ----------


class ReportIn(BaseModel):
    category: ReportCategory = ReportCategory.other
    reason: str | None = Field(default=None, max_length=2000)


class ReportOut(BaseModel):
    id: int
    category: ReportCategory
    reason: str | None
    status: ReportStatus
    created_at: datetime
    resolved_at: datetime | None
    resolution_note: str | None
    video: VideoOut
    reporter: UserPublic
    resolved_by: UserPublic | None = None


class ReportResolveIn(BaseModel):
    action: ReportAction
    note: str | None = Field(default=None, max_length=2000)


class HideVideoIn(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


# ---------- Admin ----------


class AdminUserOut(UserPublic):
    email: str
    is_active: bool
    videos_count: int
    subscribers_count: int
    subscriptions_count: int


class AdminUserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class AdminStats(BaseModel):
    users_count: int
    videos_count: int
    public_videos_count: int
    hidden_videos_count: int
    private_videos_count: int
    views_total: int
    comments_count: int
    likes_count: int
    reports_open: int
    subscriptions_count: int


# ---------- History / pagination ----------


class HistoryOut(BaseModel):
    video: VideoOut
    watched_at: datetime
    position_seconds: float


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class VideoPage(Page[VideoOut]):
    pass


class ChannelPage(Page[ChannelOut]):
    pass


class PlaylistPage(Page[PlaylistOut]):
    pass


class ReportPage(Page[ReportOut]):
    pass


class AdminUserPage(Page[AdminUserOut]):
    pass


class MessageOut(BaseModel):
    message: str
