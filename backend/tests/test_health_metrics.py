from __future__ import annotations

from tests.helpers import metric_sum, metric_value

EXPECTED_METRICS = [
    "tubeclone_app_info",
    "tubeclone_http_requests_total",
    "tubeclone_http_request_duration_seconds",
    "tubeclone_http_requests_in_progress",
    "tubeclone_videos_uploaded_total",
    "tubeclone_video_views_total",
    "tubeclone_user_logins_total",
    "tubeclone_user_registrations_total",
    "tubeclone_reports_created_total",
    "tubeclone_upload_bytes_total",
]


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "TubeClone"}


def test_metrics_endpoint_exposes_prometheus_format(client):
    client.get("/api/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    for name in EXPECTED_METRICS:
        assert name in body, f"нет метрики {name}"
    assert 'path="/api/health"' in body
    assert 'method="GET"' in body


def test_http_metrics_count_requests(client):
    before = metric_sum(client.get("/metrics").text, "tubeclone_http_requests_total")
    client.get("/api/health")
    after = metric_sum(client.get("/metrics").text, "tubeclone_http_requests_total")
    assert after >= before + 1


def test_business_metrics_are_incremented(world, login, client):
    before = client.get("/metrics").text

    user = login("user")
    assert user.post(
        f"/api/videos/{world.videos['public1']}/view",
        json={"position_seconds": 3},
    ).status_code == 200
    assert user.post(
        f"/api/videos/{world.videos['public2']}/report",
        json={"category": "spam", "reason": "Метрики"},
    ).status_code == 200
    assert user.post(
        "/api/videos",
        data={"title": "Видео для метрик", "description": "", "visibility": "public"},
        files={"file": ("clip.mp4", b"\x00\x01" * 512, "video/mp4")},
    ).status_code == 201
    assert client.post(
        "/api/auth/register",
        json={
            "email": "metrics@example.com",
            "username": "metricsuser",
            "password": "Metrics123!",
        },
    ).status_code == 201

    after = client.get("/metrics").text

    assert metric_sum(after, "tubeclone_video_views_total") > metric_sum(
        before, "tubeclone_video_views_total"
    )
    assert metric_sum(after, "tubeclone_videos_uploaded_total") > metric_sum(
        before, "tubeclone_videos_uploaded_total"
    )
    assert metric_sum(after, "tubeclone_upload_bytes_total") > metric_sum(
        before, "tubeclone_upload_bytes_total"
    )
    assert metric_sum(after, "tubeclone_user_registrations_total") > metric_sum(
        before, "tubeclone_user_registrations_total"
    )
    assert metric_value(after, 'tubeclone_user_logins_total{result="success"}') > metric_value(
        before, 'tubeclone_user_logins_total{result="success"}'
    )
    assert metric_value(after, 'tubeclone_reports_created_total{category="spam"}') > metric_value(
        before, 'tubeclone_reports_created_total{category="spam"}'
    )
