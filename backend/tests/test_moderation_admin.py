from __future__ import annotations

from tests.conftest import PASSWORD


def test_moderation_requires_moderator(world, login, client):
    assert client.get("/api/moderation/reports").status_code == 401

    user = login("user")
    assert user.get("/api/moderation/reports").status_code == 403


def test_moderator_sees_and_dismisses_report(world, login):
    moderator = login("moderator")
    reports = moderator.get("/api/moderation/reports?status=open")
    assert reports.status_code == 200
    assert reports.json()["total"] == 1

    report = reports.json()["items"][0]
    resolved = moderator.post(
        f"/api/moderation/reports/{report['id']}/resolve",
        json={"action": "dismiss", "note": "Нарушений нет"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "dismissed"
    assert resolved.json()["resolution_note"] == "Нарушений нет"


def test_hide_and_unhide_video(world, login, client):
    moderator = login("moderator")
    video_id = world.videos["public2"]

    hidden = moderator.post(f"/api/moderation/videos/{video_id}/hide", json={"reason": "Тест"})
    assert hidden.status_code == 200
    assert hidden.json()["status"] == "hidden"
    assert client.get(f"/api/videos/{video_id}").status_code == 403

    hidden_list = moderator.get("/api/moderation/videos?status=hidden")
    assert hidden_list.status_code == 200
    assert hidden_list.json()["total"] == 2

    restored = moderator.post(f"/api/moderation/videos/{video_id}/unhide")
    assert restored.status_code == 200
    assert restored.json()["status"] == "published"
    assert client.get(f"/api/videos/{video_id}").status_code == 200


def test_resolve_report_with_hide(world, login, client):
    user = login("user")
    video_id = world.videos["public2"]
    assert user.post(
        f"/api/videos/{video_id}/report",
        json={"category": "inappropriate", "reason": "Скрыть это видео"},
    ).status_code == 200

    moderator = login("moderator")
    reports = moderator.get("/api/moderation/reports?status=open").json()["items"]
    report = next(item for item in reports if item["reason"] == "Скрыть это видео")

    resolved = moderator.post(
        f"/api/moderation/reports/{report['id']}/resolve",
        json={"action": "hide", "note": "Скрыто"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["video"]["status"] == "hidden"
    assert client.get(f"/api/videos/{video_id}").status_code == 403


def test_admin_stats(world, login):
    admin = login("admin")
    response = admin.get("/api/admin/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["users_count"] == 5
    assert stats["videos_count"] == 7
    assert stats["public_videos_count"] == 4
    assert stats["hidden_videos_count"] == 1
    assert stats["private_videos_count"] == 1
    assert stats["views_total"] == 441
    assert stats["comments_count"] == 2
    assert stats["reports_open"] == 1
    assert stats["subscriptions_count"] == 2


def test_admin_user_management(world, login, client):
    admin = login("admin")

    users = admin.get("/api/admin/users?page_size=10")
    assert users.status_code == 200
    assert users.json()["total"] == 5

    maria = next(item for item in users.json()["items"] if item["username"] == "maria")
    promoted = admin.patch(f"/api/admin/users/{maria['id']}", json={"role": "moderator"})
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "moderator"

    user = next(item for item in users.json()["items"] if item["username"] == "user")
    blocked = admin.patch(f"/api/admin/users/{user['id']}", json={"is_active": False})
    assert blocked.status_code == 200
    assert blocked.json()["is_active"] is False

    blocked_login = client.post(
        "/api/auth/login",
        json={"login": "user", "password": PASSWORD},
    )
    assert blocked_login.status_code == 403


def test_admin_cannot_change_own_role(world, login):
    admin = login("admin")
    response = admin.patch(
        f"/api/admin/users/{world.users['admin']}",
        json={"role": "user"},
    )
    assert response.status_code == 400


def test_admin_endpoints_forbidden_for_regular_user(world, login):
    user = login("user")
    assert user.get("/api/admin/stats").status_code == 403
    assert user.get("/api/admin/users").status_code == 403
