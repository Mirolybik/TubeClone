from __future__ import annotations

import io

import pytest
from app.models import Playlist, Role, User, Video, Visibility
from app.permissions import AccessPolicy
from app.services.media import MediaService
from app.services.streaming import VideoStreamer
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile
from starlette.requests import Request

from tests.conftest import PASSWORD_HASH


def make_upload(content: bytes, filename: str = "clip.mp4", content_type: str = "video/mp4") -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_video_extension_detection():
    media = MediaService()
    assert media.video_extension("clip.MP4", None) == ".mp4"
    assert media.video_extension("clip.webm", "video/webm") == ".webm"
    assert media.video_extension("clip.mov", None) == ".mov"
    assert media.video_extension("clip.m4v", None) == ".m4v"
    assert media.video_extension("clip.txt", "video/mp4") == ".mp4"
    assert media.video_extension("clip.txt", "text/plain") is None
    assert media.video_extension(None, None) is None


def test_image_extension_detection():
    media = MediaService()
    assert media.image_extension("photo.JPEG", None) == ".jpg"
    assert media.image_extension("photo.png", None) == ".png"
    assert media.image_extension("photo.webp", None) == ".webp"
    assert media.image_extension("photo.gif", "image/png") == ".png"
    assert media.image_extension("photo.gif", "image/gif") is None


def test_placeholder_thumbnail_escapes_html():
    svg = MediaService().placeholder_thumbnail("<script>alert(1)</script>")
    assert b"<script>" not in svg
    assert b"&lt;script&gt;" in svg


def test_save_upload_and_limits(tmp_path):
    media = MediaService(tmp_path)
    destination = tmp_path / "videos" / "clip.mp4"

    size = media.save_upload(make_upload(b"abcdef"), destination, max_bytes=100)
    assert size == 6
    assert destination.read_bytes() == b"abcdef"

    too_big = tmp_path / "videos" / "big.mp4"
    with pytest.raises(HTTPException) as exc:
        media.save_upload(make_upload(b"0123456789"), too_big, max_bytes=4)
    assert exc.value.status_code == 413
    assert not too_big.exists()

    empty = tmp_path / "videos" / "empty.mp4"
    with pytest.raises(HTTPException) as exc:
        media.save_upload(make_upload(b""), empty, max_bytes=100)
    assert exc.value.status_code == 400
    assert not empty.exists()


def test_ensure_dirs_and_delete_file(tmp_path):
    media = MediaService(tmp_path)
    media.ensure_dirs()
    assert (tmp_path / "videos").is_dir()
    assert (tmp_path / "thumbnails").is_dir()

    target = tmp_path / "videos" / "delete-me.mp4"
    target.write_bytes(b"x")
    media.delete_file("videos/delete-me.mp4")
    assert not target.exists()
    media.delete_file(None)
    media.delete_file("videos/does-not-exist.mp4")


def test_cache_headers():
    private = Video(visibility=Visibility.private)
    public = Video(visibility=Visibility.public)
    assert VideoStreamer.cache_header(private) == "private, no-store"
    assert VideoStreamer.cache_header(public) == "public, max-age=3600"


def test_parse_range_variants():
    assert VideoStreamer._parse_range("bytes=0-99", 1000) == (0, 99)
    assert VideoStreamer._parse_range("bytes=100-", 1000) == (100, 999)
    assert VideoStreamer._parse_range("bytes=-100", 1000) == (900, 999)
    assert VideoStreamer._parse_range("bytes=0-5000", 1000) == (0, 999)


@pytest.mark.parametrize("header", ["bytes=abc", "bytes=1000-", "bytes=500-400", "items=0-1"])
def test_parse_range_rejects_invalid(header):
    with pytest.raises(HTTPException) as exc:
        VideoStreamer._parse_range(header, 1000)
    assert exc.value.status_code == 416


def test_stream_missing_file_returns_404():
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }
    )
    video = Video(storage_path="videos/missing.mp4", content_type="video/mp4")
    with pytest.raises(HTTPException) as exc:
        VideoStreamer().stream(video, request)
    assert exc.value.status_code == 404


def test_access_policy_video_rules(world, db):
    creator = db.get(User, world.users["creator"])
    user = db.get(User, world.users["user"])
    moderator = db.get(User, world.users["moderator"])
    admin = db.get(User, world.users["admin"])
    public = db.get(Video, world.videos["public1"])
    private = db.get(Video, world.videos["private"])
    hidden = db.get(Video, world.videos["hidden"])

    stranger = User(
        username="stranger",
        email="stranger@example.com",
        password_hash=PASSWORD_HASH,
        role=Role.user,
    )
    db.add(stranger)
    db.commit()
    db.refresh(stranger)

    policy = AccessPolicy(db)
    assert policy.can_view_video(public, None) is True
    assert policy.can_view_video(private, None) is False
    assert policy.can_view_video(private, user) is True
    assert policy.can_view_video(private, stranger) is False
    assert policy.can_view_video(hidden, None) is False
    assert policy.can_view_video(hidden, creator) is True
    assert policy.can_view_video(hidden, moderator) is True
    assert policy.can_view_video(hidden, admin) is True

    assert policy.can_manage_video(public, creator) is True
    assert policy.can_manage_video(public, user) is False
    assert policy.can_manage_video(public, admin) is True

    assert policy.is_subscribed(user, creator.id) is True
    assert policy.is_subscribed(user, admin.id) is False
    assert policy.is_subscribed(None, creator.id) is False

    public_playlist = db.get(Playlist, world.playlists["public"])
    assert policy.can_manage_playlist(public_playlist, creator) is True
    assert policy.can_manage_playlist(public_playlist, user) is False
    assert policy.can_manage_playlist(public_playlist, admin) is True
