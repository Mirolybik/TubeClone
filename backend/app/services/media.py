from __future__ import annotations

import html
import shutil
import subprocess
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from ..config import settings

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

VIDEO_CONTENT_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-m4v": ".m4v",
    "application/octet-stream": None,
}

IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class MediaService:
    """Операции с медиатекой: проверка форматов, сохранение, превью и удаление файлов."""

    def __init__(self, media_dir: Path | None = None) -> None:
        self.media_dir = Path(media_dir) if media_dir is not None else settings.media_dir

    @property
    def videos_dir(self) -> Path:
        return self.media_dir / "videos"

    @property
    def thumbnails_dir(self) -> Path:
        return self.media_dir / "thumbnails"

    def path(self, relative_path: str) -> Path:
        return self.media_dir / relative_path

    def ensure_dirs(self) -> None:
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

    def video_extension(self, filename: str | None, content_type: str | None) -> str | None:
        suffix = Path(filename or "").suffix.lower()
        if suffix in ALLOWED_VIDEO_EXTENSIONS:
            return suffix
        if content_type in VIDEO_CONTENT_TYPES:
            return VIDEO_CONTENT_TYPES[content_type]
        return None

    def image_extension(self, filename: str | None, content_type: str | None) -> str | None:
        suffix = Path(filename or "").suffix.lower()
        if suffix in ALLOWED_IMAGE_EXTENSIONS:
            return ".jpg" if suffix == ".jpeg" else suffix
        return IMAGE_CONTENT_TYPES.get(content_type or "")

    def save_upload(self, upload: UploadFile, destination: Path, max_bytes: int) -> int:
        destination.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        try:
            with destination.open("wb") as output:
                while True:
                    chunk = upload.file.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Файл больше допустимого размера ({settings.max_upload_mb} МБ)",
                        )
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            try:
                upload.file.close()
            except Exception:
                pass

        if total == 0:
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Загружен пустой файл")
        return total

    def probe_duration(self, path: Path) -> float | None:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return None
            return round(float(result.stdout.strip()), 2)
        except (OSError, ValueError, subprocess.SubprocessError):
            return None

    def generate_thumbnail(
        self,
        video_path: Path,
        thumbnail_path: Path,
        duration: float | None = None,
    ) -> bool:
        seek = 0.5
        if duration and duration > 2:
            seek = min(2.0, duration / 3)
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    f"{seek:.2f}",
                    "-i",
                    str(video_path),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=640:-2",
                    "-q:v",
                    "3",
                    str(thumbnail_path),
                ],
                capture_output=True,
                timeout=60,
            )
            return result.returncode == 0 and thumbnail_path.exists()
        except (OSError, subprocess.SubprocessError):
            return False

    def delete_file(self, relative_path: str | None) -> None:
        if not relative_path:
            return
        try:
            self.path(relative_path).unlink(missing_ok=True)
        except OSError:
            pass

    def remove_tree(self, path: Path) -> None:
        shutil.rmtree(path, ignore_errors=True)

    def placeholder_thumbnail(self, title: str) -> bytes:
        safe_title = html.escape(title[:42])
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
  <rect width="640" height="360" fill="#212121"/>
  <circle cx="320" cy="164" r="48" fill="#ff0000"/>
  <path d="M307 140 L347 164 L307 188 Z" fill="#ffffff"/>
  <text x="320" y="268" font-family="Roboto, Arial, sans-serif" font-size="24" fill="#f1f1f1" text-anchor="middle">{safe_title}</text>
  <text x="320" y="306" font-family="Roboto, Arial, sans-serif" font-size="15" fill="#aaaaaa" text-anchor="middle">TubeClone</text>
</svg>"""
        return svg.encode("utf-8")


media_service = MediaService()
