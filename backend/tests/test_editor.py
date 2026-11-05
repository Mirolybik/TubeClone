from __future__ import annotations

import shutil
import subprocess

import pytest

from app.config import settings
from app.models import Video


@pytest.fixture(scope="module")
def sample_video(tmp_path_factory) -> bytes:
    if not shutil.which("ffmpeg"):
        pytest.skip("Для тестов редактора нужен ffmpeg")
    path = tmp_path_factory.mktemp("editor") / "sample.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x120:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(path),
        ],
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return path.read_bytes()


@pytest.fixture(scope="module")
def hd_video(tmp_path_factory) -> bytes:
    if not shutil.which("ffmpeg"):
        pytest.skip("Для тестов качества нужен ffmpeg")
    path = tmp_path_factory.mktemp("quality") / "hd.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=1920x1080:rate=5",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(path),
        ],
        capture_output=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return path.read_bytes()


def upload_editor(client, video_bytes: bytes, **fields):
    data = {"title": "Видео с правками", "visibility": "public"}
    for key, value in fields.items():
        if isinstance(value, bool):
            data[key] = "true" if value else "false"
        else:
            data[key] = str(value)
    return client.post(
        "/api/videos",
        data=data,
        files={"file": ("sample.mp4", video_bytes, "video/mp4")},
    )


def test_editor_rejects_invalid_options(world, login, sample_video):
    creator = login("creator")

    bad_rotate = upload_editor(creator, sample_video, rotate=45)
    assert bad_rotate.status_code == 400

    bad_crop = upload_editor(creator, sample_video, crop_aspect="21:9")
    assert bad_crop.status_code == 400

    bad_filter = upload_editor(creator, sample_video, video_filter="unknown")
    assert bad_filter.status_code == 400

    bad_speed = upload_editor(creator, sample_video, speed=3)
    assert bad_speed.status_code == 400

    bad_trim = upload_editor(creator, sample_video, trim_start=0.8, trim_end=0.2)
    assert bad_trim.status_code == 400

    beyond = upload_editor(creator, sample_video, trim_start=5)
    assert beyond.status_code == 400


def test_editor_applies_edits_and_replaces_upload(world, login, sample_video, db):
    creator = login("creator")
    response = upload_editor(
        creator,
        sample_video,
        trim_start=0.2,
        trim_end=0.8,
        rotate=90,
        flip_horizontal=True,
        crop_aspect="16:9",
        video_filter="grayscale",
        speed=1.5,
        volume=0.5,
        thumbnail_timestamp=0.2,
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["duration_seconds"] is not None
    assert abs(payload["duration_seconds"] - 0.4) < 0.3

    video = db.get(Video, payload["id"])
    assert video is not None
    assert video.storage_path.endswith(".mp4")
    stored = settings.media_dir / video.storage_path
    assert stored.is_file()
    assert video.size_bytes == stored.stat().st_size
    assert video.content_type == "video/mp4"

    edited_leftovers = list((settings.media_dir / "videos").glob(f"{stored.stem}-edited*"))
    assert edited_leftovers == []

    stream = creator.get(f"/api/videos/{payload['id']}/stream", headers={"Range": "bytes=0-99"})
    assert stream.status_code == 206
    assert len(stream.content) == 100

    thumbnail = creator.get(f"/api/videos/{payload['id']}/thumbnail")
    assert thumbnail.status_code == 200
    assert thumbnail.headers["content-type"].startswith("image/jpeg")
    assert thumbnail.content.startswith(b"\xff\xd8")


def test_frame_thumbnail_without_edits(world, login, sample_video):
    creator = login("creator")
    response = upload_editor(creator, sample_video, thumbnail_timestamp=0.5)
    assert response.status_code == 201, response.text
    video_id = response.json()["id"]

    thumbnail = creator.get(f"/api/videos/{video_id}/thumbnail")
    assert thumbnail.status_code == 200
    assert thumbnail.headers["content-type"].startswith("image/jpeg")
    assert thumbnail.content.startswith(b"\xff\xd8")


def test_editor_keeps_original_when_no_options(world, login, sample_video, db):
    creator = login("creator")
    response = upload_editor(creator, sample_video)
    assert response.status_code == 201, response.text

    video = db.get(Video, response.json()["id"])
    assert video is not None
    stored = settings.media_dir / video.storage_path
    assert stored.read_bytes() == sample_video


def test_upload_rejects_invalid_quality(world, login, sample_video):
    creator = login("creator")
    response = upload_editor(creator, sample_video, qualities="1440p")
    assert response.status_code == 400


def test_upload_generates_quality_variants(world, login, hd_video, db):
    creator = login("creator")
    response = upload_editor(creator, hd_video, qualities="1080p,720p,480p")
    assert response.status_code == 201, response.text
    payload = response.json()
    video_id = payload["id"]

    qualities = {item["quality"]: item for item in payload["qualities"]}
    # Исходник уже 1080p, поэтому отдельная версия 1080p не создаётся.
    assert set(qualities) == {"original", "720p", "480p"}
    assert qualities["720p"]["height"] == 720
    assert qualities["480p"]["height"] == 480
    assert qualities["original"]["stream_url"] == f"/api/videos/{video_id}/stream"

    for quality in ("720p", "480p"):
        stream = creator.get(
            f"/api/videos/{video_id}/stream?quality={quality}",
            headers={"Range": "bytes=0-99"},
        )
        assert stream.status_code == 206, stream.text
        assert len(stream.content) == 100

    assert creator.get(f"/api/videos/{video_id}/stream?quality=1080p").status_code == 404

    video = db.get(Video, video_id)
    assert video is not None
    assert {item.quality for item in video.renditions} == {"720p", "480p"}
    rendition_paths = [settings.media_dir / item.storage_path for item in video.renditions]
    assert all(path.is_file() for path in rendition_paths)

    assert creator.delete(f"/api/videos/{video_id}").status_code == 200
    assert all(not path.exists() for path in rendition_paths)
