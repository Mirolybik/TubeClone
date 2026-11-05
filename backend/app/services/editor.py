from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, status

from .media import MediaService, media_service

ALLOWED_ROTATIONS = {0, 90, 180, 270}
ALLOWED_CROP_ASPECTS = {
    "original": None,
    "16:9": 16 / 9,
    "9:16": 9 / 16,
    "1:1": 1.0,
    "4:3": 4 / 3,
}
ALLOWED_VIDEO_FILTERS = {
    "none": None,
    "grayscale": "hue=s=0",
    "sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
    "contrast": "eq=contrast=1.25",
    "bright": "eq=brightness=0.08",
    "vivid": "eq=saturation=1.3:contrast=1.1",
}
QUALITY_HEIGHTS = {"1080p": 1080, "720p": 720, "480p": 480}
ALLOWED_QUALITY_VARIANTS = set(QUALITY_HEIGHTS)


@dataclass(frozen=True)
class EditOptions:
    """Параметры простого редактора, которые применяются на сервере."""

    trim_start: float = 0.0
    trim_end: float | None = None
    rotate: int = 0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    crop_aspect: str = "original"
    video_filter: str = "none"
    speed: float = 1.0
    mute: bool = False
    volume: float = 1.0

    @property
    def has_edits(self) -> bool:
        return (
            self.trim_start > 0.001
            or self.trim_end is not None
            or self.rotate != 0
            or self.flip_horizontal
            or self.flip_vertical
            or self.crop_aspect != "original"
            or self.video_filter != "none"
            or abs(self.speed - 1.0) > 0.001
            or self.mute
            or abs(self.volume - 1.0) > 0.001
        )

    def validate(self) -> None:
        if not math.isfinite(self.trim_start) or self.trim_start < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Начало обрезки не может быть отрицательным",
            )
        if self.trim_end is not None:
            if not math.isfinite(self.trim_end) or self.trim_end <= self.trim_start:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Конец обрезки должен быть больше начала",
                )
        if self.rotate not in ALLOWED_ROTATIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый угол поворота")
        if self.crop_aspect not in ALLOWED_CROP_ASPECTS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый формат кадра")
        if self.video_filter not in ALLOWED_VIDEO_FILTERS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый фильтр")
        if not 0.5 <= self.speed <= 2.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Скорость должна быть от 0.5x до 2x",
            )
        if not 0.0 <= self.volume <= 2.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Громкость должна быть от 0% до 200%",
            )

    def validate_duration(self, duration: float | None) -> None:
        if duration is None:
            return
        if self.trim_start >= duration - 0.05:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Начало обрезки выходит за пределы видео",
            )
        if self.trim_end is not None and self.trim_end > duration + 0.5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Конец обрезки выходит за пределы видео",
            )


class VideoEditor:
    """Применяет простые правки к видео через ffmpeg."""

    def __init__(self, media: MediaService | None = None) -> None:
        self.media = media or media_service

    def process(self, source: Path, destination: Path, options: EditOptions) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        dimensions = self.probe_dimensions(source)

        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        if options.trim_start > 0:
            command.extend(["-ss", f"{options.trim_start:.3f}"])
        command.extend(["-i", str(source)])

        if options.trim_end is not None:
            # -t задаёт длительность уже после фильтра скорости.
            trim_duration = max(0.1, options.trim_end - options.trim_start)
            command.extend(["-t", f"{trim_duration / options.speed:.3f}"])

        video_filters = self._video_filters(options, dimensions)
        if video_filters:
            command.extend(["-vf", ",".join(video_filters)])

        has_audio = not options.mute and self.has_audio(source)
        if options.mute:
            command.append("-an")
        else:
            audio_filters = self._audio_filters(options)
            if has_audio and audio_filters:
                command.extend(["-af", ",".join(audio_filters)])

        command.extend(["-map", "0:v:0"])
        if has_audio:
            command.extend(["-map", "0:a:0"])

        command.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(destination),
            ]
        )

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        except (OSError, subprocess.SubprocessError) as exc:
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось обработать видео",
            ) from exc

        if result.returncode != 0 or not destination.is_file():
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось обработать видео. Проверьте формат файла.",
            )

    def create_rendition(self, source: Path, destination: Path, height: int) -> None:
        """Создаёт дополнительную версию видео с заданной высотой кадра."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        crf = 23 if height >= 1080 else 24 if height >= 720 else 26
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vf",
            f"scale=-2:{height}",
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(destination),
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        except (OSError, subprocess.SubprocessError) as exc:
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось создать версию видео",
            ) from exc
        if result.returncode != 0 or not destination.is_file():
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось создать версию видео. Проверьте формат файла.",
            )

    def extract_frame(self, video_path: Path, thumbnail_path: Path, timestamp: float) -> bool:
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{max(0.0, timestamp):.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-vf",
            "scale=640:-2",
            "-q:v",
            "3",
            str(thumbnail_path),
        ]
        try:
            result = subprocess.run(command, capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            thumbnail_path.unlink(missing_ok=True)
            return False
        if result.returncode != 0 or not thumbnail_path.is_file():
            thumbnail_path.unlink(missing_ok=True)
            return False
        return True

    def has_audio(self, path: Path) -> bool:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "a:0",
                    "-show_entries",
                    "stream=index",
                    "-of",
                    "csv=p=0",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            return False

    def probe_dimensions(self, path: Path) -> tuple[int, int] | None:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=width,height",
                    "-of",
                    "csv=p=0",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return None
            raw = result.stdout.strip().splitlines()[0]
            width, height = raw.replace(" ", "").split(",")[:2]
            return int(width), int(height)
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            return None

    def _video_filters(self, options: EditOptions, dimensions: tuple[int, int] | None) -> list[str]:
        filters: list[str] = []

        if options.rotate == 90:
            filters.append("transpose=1")
        elif options.rotate == 180:
            filters.extend(["hflip", "vflip"])
        elif options.rotate == 270:
            filters.append("transpose=2")

        if options.flip_horizontal:
            filters.append("hflip")
        if options.flip_vertical:
            filters.append("vflip")

        width, height = dimensions or (0, 0)
        if options.rotate in (90, 270):
            width, height = height, width

        aspect = ALLOWED_CROP_ASPECTS.get(options.crop_aspect)
        if aspect and width > 0 and height > 0:
            if width / height > aspect:
                crop_width = int(height * aspect)
                crop_height = height
                x = (width - crop_width) // 2
                y = 0
            else:
                crop_width = width
                crop_height = int(width / aspect)
                x = 0
                y = (height - crop_height) // 2
            crop_width -= crop_width % 2
            crop_height -= crop_height % 2
            x -= x % 2
            y -= y % 2
            if crop_width > 0 and crop_height > 0 and (crop_width != width or crop_height != height):
                filters.append(f"crop={crop_width}:{crop_height}:{x}:{y}")

        # libx264 требует чётные размеры для yuv420p.
        filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")

        effect = ALLOWED_VIDEO_FILTERS.get(options.video_filter)
        if effect:
            filters.append(effect)

        if abs(options.speed - 1.0) > 0.001:
            filters.append(f"setpts=PTS/{options.speed:.4f}")

        return filters

    def _audio_filters(self, options: EditOptions) -> list[str]:
        filters: list[str] = []
        if abs(options.speed - 1.0) > 0.001:
            filters.append(f"atempo={options.speed:.4f}")
        if abs(options.volume - 1.0) > 0.001:
            filters.append(f"volume={options.volume:.3f}")
        return filters


editor = VideoEditor()
