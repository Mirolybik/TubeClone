from __future__ import annotations

import re
from pathlib import Path

from fastapi import HTTPException, Request, status
from fastapi.responses import FileResponse, Response, StreamingResponse

from ..models import Video, Visibility
from .media import MediaService, media_service

IMAGE_MEDIA_TYPES = {
    ".png": "image/png",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class VideoStreamer:
    """Формирует ответы для Range-стриминга и превью видео."""

    def __init__(self, media: MediaService | None = None) -> None:
        self.media = media or media_service

    @staticmethod
    def cache_header(video: Video) -> str:
        if video.visibility == Visibility.private:
            return "private, no-store"
        return "public, max-age=3600"

    def stream(
        self,
        video: Video,
        request: Request,
        storage_path: str | None = None,
        content_type: str | None = None,
    ) -> Response:
        path = self.media.path(storage_path or video.storage_path)
        if not path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл видео не найден")

        file_size = path.stat().st_size
        media_type = content_type or video.content_type or "video/mp4"
        headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": self.cache_header(video),
            "Content-Disposition": f'inline; filename="video-{video.id}"',
        }
        range_header = request.headers.get("range")
        if range_header:
            start, end = self._parse_range(range_header, file_size)
            length = end - start + 1
            headers.update(
                {
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Length": str(length),
                }
            )
            return StreamingResponse(
                self._iter_file(path, start, length),
                status_code=status.HTTP_206_PARTIAL_CONTENT,
                media_type=media_type,
                headers=headers,
            )

        headers["Content-Length"] = str(file_size)
        return FileResponse(path, media_type=media_type, headers=headers)

    def thumbnail(self, video: Video) -> Response:
        if video.thumbnail_path:
            path = self.media.path(video.thumbnail_path)
            if path.is_file():
                media_type = IMAGE_MEDIA_TYPES.get(path.suffix.lower(), "image/jpeg")
                return FileResponse(
                    path,
                    media_type=media_type,
                    headers={"Cache-Control": self.cache_header(video)},
                )
        return Response(
            content=self.media.placeholder_thumbnail(video.title),
            media_type="image/svg+xml",
            headers={"Cache-Control": self.cache_header(video)},
        )

    @staticmethod
    def _parse_range(range_header: str, file_size: int) -> tuple[int, int]:
        match = re.match(r"bytes=(\d*)-(\d*)", range_header.strip())
        if not match:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="Некорректный Range",
                headers={"Content-Range": f"bytes */{file_size}"},
            )
        start_raw, end_raw = match.groups()
        if start_raw:
            start = int(start_raw)
            end = int(end_raw) if end_raw else file_size - 1
        else:
            length = int(end_raw or 0)
            start = max(0, file_size - length)
            end = file_size - 1
        if start >= file_size or end < start:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="Диапазон вне файла",
                headers={"Content-Range": f"bytes */{file_size}"},
            )
        return start, min(end, file_size - 1)

    @staticmethod
    def _iter_file(path: Path, start: int, length: int, chunk_size: int = 1024 * 1024):
        with path.open("rb") as file_obj:
            file_obj.seek(start)
            remaining = length
            while remaining > 0:
                data = file_obj.read(min(chunk_size, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data


streamer = VideoStreamer()
