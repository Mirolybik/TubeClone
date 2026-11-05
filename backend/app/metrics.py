from __future__ import annotations

import time

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)


class AppMetrics:
    """Метрики приложения для Prometheus и дашборда Grafana."""

    def __init__(self) -> None:
        self.app_info = Info("tubeclone_app", "TubeClone application info")
        self.app_info.info({"version": "1.0.0", "service": "tubeclone"})

        self.http_requests_total = Counter(
            "tubeclone_http_requests_total",
            "HTTP-запросы к API",
            ["method", "path", "status"],
        )
        self.http_request_duration = Histogram(
            "tubeclone_http_request_duration_seconds",
            "Длительность HTTP-запросов к API",
            ["method", "path"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
        self.http_requests_in_progress = Gauge(
            "tubeclone_http_requests_in_progress",
            "HTTP-запросы, выполняющиеся прямо сейчас",
        )
        self.videos_uploaded_total = Counter(
            "tubeclone_videos_uploaded_total",
            "Успешные загрузки видео",
        )
        self.video_views_total = Counter(
            "tubeclone_video_views_total",
            "Отмеченные просмотры видео",
        )
        self.user_logins_total = Counter(
            "tubeclone_user_logins_total",
            "Попытки входа в аккаунт",
            ["result"],
        )
        self.user_registrations_total = Counter(
            "tubeclone_user_registrations_total",
            "Регистрации новых пользователей",
        )
        self.reports_created_total = Counter(
            "tubeclone_reports_created_total",
            "Созданные жалобы на видео",
            ["category"],
        )
        self.upload_bytes_total = Counter(
            "tubeclone_upload_bytes_total",
            "Объём загруженных видеофайлов в байтах",
        )

    def observe_http(self, method: str, path: str, status_code: int, duration: float) -> None:
        self.http_requests_total.labels(method=method, path=path, status=str(status_code)).inc()
        self.http_request_duration.labels(method=method, path=path).observe(duration)

    def record_upload(self, size_bytes: int) -> None:
        self.videos_uploaded_total.inc()
        self.upload_bytes_total.inc(size_bytes)

    def record_view(self) -> None:
        self.video_views_total.inc()

    def record_login(self, success: bool) -> None:
        self.user_logins_total.labels(result="success" if success else "failure").inc()

    def record_registration(self) -> None:
        self.user_registrations_total.inc()

    def record_report(self, category: str) -> None:
        self.reports_created_total.labels(category=category).inc()


metrics = AppMetrics()


async def metrics_middleware(request: Request, call_next):
    """Собирает HTTP-метрики только для API, чтобы не засорять графики статикой."""
    if not request.url.path.startswith("/api"):
        return await call_next(request)

    started = time.perf_counter()
    metrics.http_requests_in_progress.inc()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        metrics.http_requests_in_progress.dec()
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        metrics.observe_http(request.method, path, status_code, time.perf_counter() - started)


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
