from __future__ import annotations

import base64

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def upload_video(
    client,
    title="Тестовое видео",
    filename="clip.mp4",
    content=b"\x00\x01" * 1024,
    content_type="video/mp4",
):
    return client.post(
        "/api/videos",
        data={"title": title, "description": "Описание", "visibility": "public"},
        files={"file": (filename, content, content_type)},
    )


def test_anonymous_can_view_public_and_unlisted(world, client):
    assert client.get(f"/api/videos/{world.videos['public1']}").status_code == 200
    assert client.get(f"/api/videos/{world.videos['unlisted']}").status_code == 200


def test_anonymous_cannot_view_private_or_hidden(world, client):
    assert client.get(f"/api/videos/{world.videos['private']}").status_code == 403
    assert client.get(f"/api/videos/{world.videos['hidden']}").status_code == 403


def test_private_video_allowlist(world, login, client):
    allowed = login("user")
    assert allowed.get(f"/api/videos/{world.videos['private']}").status_code == 200

    response = client.post(
        "/api/auth/register",
        json={"email": "viewer@example.com", "username": "viewer", "password": "Viewer123!"},
    )
    assert response.status_code == 201
    assert client.get(f"/api/videos/{world.videos['private']}").status_code == 403


def test_moderator_and_owner_see_hidden_video(world, login):
    moderator = login("moderator")
    assert moderator.get(f"/api/videos/{world.videos['hidden']}").status_code == 200

    owner = login("creator")
    assert owner.get(f"/api/videos/{world.videos['hidden']}").status_code == 200


def test_owner_can_edit_and_other_user_cannot(world, login):
    owner = login("creator")
    response = owner.patch(
        f"/api/videos/{world.videos['public1']}",
        json={"title": "Обновлённое название"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Обновлённое название"

    other = login("user")
    response = other.patch(
        f"/api/videos/{world.videos['public1']}",
        json={"title": "Чужая правка"},
    )
    assert response.status_code == 403


def test_stream_full_and_ranges(world, client):
    url = f"/api/videos/{world.videos['public1']}/stream"

    full = client.get(url)
    assert full.status_code == 200
    assert len(full.content) == 8192
    assert full.headers["accept-ranges"] == "bytes"

    first = client.get(url, headers={"Range": "bytes=0-99"})
    assert first.status_code == 206
    assert len(first.content) == 100
    assert first.headers["content-range"] == "bytes 0-99/8192"

    tail = client.get(url, headers={"Range": "bytes=-100"})
    assert tail.status_code == 206
    assert len(tail.content) == 100
    assert tail.headers["content-range"] == "bytes 8092-8191/8192"

    open_range = client.get(url, headers={"Range": "bytes=100-"})
    assert open_range.status_code == 206
    assert len(open_range.content) == 8092


def test_stream_rejects_invalid_range(world, client):
    url = f"/api/videos/{world.videos['public1']}/stream"
    assert client.get(url, headers={"Range": "bytes=99999-"}).status_code == 416
    assert client.get(url, headers={"Range": "bytes=abc"}).status_code == 416


def test_private_stream_requires_access(world, client, login):
    url = f"/api/videos/{world.videos['private']}/stream"
    assert client.get(url).status_code == 403

    allowed = login("user")
    response = allowed.get(url)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"


def test_thumbnail_placeholder_and_cache(world, client):
    response = client.get(f"/api/videos/{world.videos['public1']}/thumbnail")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert b"TubeClone" in response.content


def test_upload_requires_auth(world, client):
    response = upload_video(client)
    assert response.status_code == 401


def test_upload_stream_update_thumbnail_and_delete(world, login):
    creator = login("creator")
    response = upload_video(creator, title="Загруженное видео")
    assert response.status_code == 201, response.text
    video = response.json()
    video_id = video["id"]
    assert video["is_owner"] is True

    stream = creator.get(f"/api/videos/{video_id}/stream", headers={"Range": "bytes=0-9"})
    assert stream.status_code == 206
    assert len(stream.content) == 10

    patch = creator.patch(f"/api/videos/{video_id}", json={"title": "Новое имя"})
    assert patch.status_code == 200
    assert patch.json()["title"] == "Новое имя"

    thumbnail = creator.post(
        f"/api/videos/{video_id}/thumbnail",
        files={"thumbnail": ("pixel.png", PNG_1X1, "image/png")},
    )
    assert thumbnail.status_code == 200
    assert thumbnail.json()["thumbnail_url"] == f"/api/videos/{video_id}/thumbnail"

    image = creator.get(f"/api/videos/{video_id}/thumbnail")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"

    assert creator.delete(f"/api/videos/{video_id}").status_code == 200
    assert creator.get(f"/api/videos/{video_id}").status_code == 404


def test_upload_rejects_bad_format_and_empty_file(world, login):
    creator = login("creator")

    bad = upload_video(creator, filename="clip.txt", content=b"not a video", content_type="text/plain")
    assert bad.status_code == 400

    empty = upload_video(creator, filename="empty.mp4", content=b"")
    assert empty.status_code == 400


def test_reactions(world, login):
    user = login("user")
    url = f"/api/videos/{world.videos['public2']}/reaction"

    liked = user.post(url, json={"value": 1})
    assert liked.status_code == 200
    assert liked.json()["likes_count"] == 1
    assert liked.json()["my_reaction"] == 1

    disliked = user.post(url, json={"value": -1})
    assert disliked.status_code == 200
    assert disliked.json()["dislikes_count"] == 1
    assert disliked.json()["my_reaction"] == -1

    cleared = user.post(url, json={"value": 0})
    assert cleared.status_code == 200
    assert cleared.json()["my_reaction"] is None


def test_view_updates_counter_and_history(world, login):
    user = login("user")
    response = user.post(
        f"/api/videos/{world.videos['public2']}/view",
        json={"position_seconds": 7},
    )
    assert response.status_code == 200
    assert response.json()["views_count"] == 51

    history = user.get("/api/history")
    assert history.status_code == 200
    assert any(item["video"]["id"] == world.videos["public2"] for item in history.json())


def test_report_and_duplicate_report(world, login):
    user = login("user")
    url = f"/api/videos/{world.videos['public1']}/report"

    first = user.post(url, json={"category": "other", "reason": "Проверка"})
    assert first.status_code == 200

    duplicate = user.post(url, json={"category": "other", "reason": "Ещё раз"})
    assert duplicate.status_code == 409


def test_private_access_management(world, login):
    owner = login("creator")
    url = f"/api/videos/{world.videos['private']}/access"

    access = owner.get(url)
    assert access.status_code == 200
    assert {item["username"] for item in access.json()["users"]} == {"user", "maria"}

    added = owner.post(url, json={"username": "moderator"})
    assert added.status_code == 200
    assert "moderator" in {item["username"] for item in added.json()["users"]}

    removed = owner.delete(f"{url}/{world.users['moderator']}")
    assert removed.status_code == 200
    assert "moderator" not in {item["username"] for item in removed.json()["users"]}

    other = login("user")
    assert other.get(url).status_code == 403
