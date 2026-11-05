from __future__ import annotations


def test_feed_and_popular_sort(world, client):
    feed = client.get("/api/feed")
    assert feed.status_code == 200
    assert feed.json()["total"] == 4

    popular = client.get("/api/feed?sort=popular")
    views = [item["views_count"] for item in popular.json()["items"]]
    assert views == sorted(views, reverse=True)


def test_feed_pagination(world, client):
    page = client.get("/api/feed?page=1&page_size=2")
    payload = page.json()
    assert len(payload["items"]) == 2
    assert payload["total"] == 4
    assert payload["pages"] == 2


def test_search_is_case_insensitive_and_public_only(world, client):
    response = client.get("/api/search", params={"q": "пасту"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == world.videos["public2"]

    hidden = client.get("/api/search", params={"q": "Скрытый"})
    assert hidden.json()["total"] == 0


def test_subscriptions_feed_and_channels(world, login, client):
    user = login("user")
    feed = user.get("/api/feed/subscriptions")
    assert feed.status_code == 200
    assert feed.json()["total"] == 4

    subscriptions = user.get("/api/me/subscriptions")
    assert subscriptions.status_code == 200
    assert {item["username"] for item in subscriptions.json()} == {"creator", "maria"}

    channel = user.get("/api/channels/creator")
    assert channel.status_code == 200
    assert channel.json()["is_subscribed"] is True
    assert channel.json()["videos_count"] == 2

    videos = user.get("/api/channels/creator/videos")
    assert videos.status_code == 200
    assert videos.json()["total"] == 2

    playlists = client.get("/api/channels/creator/playlists")
    assert playlists.status_code == 200
    assert playlists.json()["total"] == 1


def test_subscribe_and_unsubscribe(world, login):
    admin = login("admin")

    subscribed = admin.post("/api/channels/creator/subscribe")
    assert subscribed.status_code == 200
    assert subscribed.json()["is_subscribed"] is True

    unsubscribed = admin.delete("/api/channels/creator/subscribe")
    assert unsubscribed.status_code == 200
    assert unsubscribed.json()["is_subscribed"] is False

    assert admin.post("/api/channels/admin/subscribe").status_code == 400


def test_comments_flow(world, login, client):
    public_comments = client.get(f"/api/videos/{world.videos['public1']}/comments")
    assert public_comments.status_code == 200
    assert len(public_comments.json()) == 2

    user = login("user")
    created = user.post(
        f"/api/videos/{world.videos['public1']}/comments",
        json={"text": "Новый комментарий"},
    )
    assert created.status_code == 201
    comment_id = created.json()["id"]

    maria = login("maria")
    reply = maria.post(
        f"/api/videos/{world.videos['public1']}/comments",
        json={"text": "Ответ", "parent_id": comment_id},
    )
    assert reply.status_code == 201
    assert reply.json()["parent_id"] == comment_id

    maria_comment = next(
        item for item in public_comments.json() if item["user"]["username"] == "maria"
    )
    assert user.delete(f"/api/comments/{maria_comment['id']}").status_code == 403

    owner = login("creator")
    assert owner.delete(f"/api/comments/{comment_id}").status_code == 200


def test_comment_requires_video_access(world, client):
    assert client.post(
        f"/api/videos/{world.videos['private']}/comments",
        json={"text": "Без доступа"},
    ).status_code == 401

    assert client.get(f"/api/videos/{world.videos['private']}/comments").status_code == 403


def test_playlists_crud_and_access(world, login, client):
    assert client.get(f"/api/playlists/{world.playlists['public']}").status_code == 200
    assert client.get(f"/api/playlists/{world.playlists['private']}").status_code == 403

    user = login("user")
    assert user.get(f"/api/playlists/{world.playlists['private']}").status_code == 200

    created = user.post(
        "/api/playlists",
        json={"title": "Новый плейлист", "description": "Описание", "visibility": "public"},
    )
    assert created.status_code == 201
    playlist_id = created.json()["id"]

    first = user.post(
        f"/api/playlists/{playlist_id}/items",
        json={"video_id": world.videos["public1"]},
    )
    assert first.status_code == 200
    first_item = first.json()["items"][0]["id"]

    duplicate = user.post(
        f"/api/playlists/{playlist_id}/items",
        json={"video_id": world.videos["public1"]},
    )
    assert duplicate.status_code == 409

    second = user.post(
        f"/api/playlists/{playlist_id}/items",
        json={"video_id": world.videos["public2"]},
    )
    assert second.status_code == 200
    item_ids = [item["id"] for item in second.json()["items"]]
    assert len(item_ids) == 2

    reordered = user.put(
        f"/api/playlists/{playlist_id}/order",
        json={"item_ids": list(reversed(item_ids))},
    )
    assert reordered.status_code == 200
    assert [item["id"] for item in reordered.json()["items"]] == list(reversed(item_ids))

    updated = user.patch(
        f"/api/playlists/{playlist_id}",
        json={"title": "Обновлённый плейлист", "visibility": "private"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Обновлённый плейлист"
    assert updated.json()["visibility"] == "private"

    removed = user.delete(f"/api/playlists/{playlist_id}/items/{first_item}")
    assert removed.status_code == 200
    assert len(removed.json()["items"]) == 1

    assert user.delete(f"/api/playlists/{playlist_id}").status_code == 200
    assert user.get(f"/api/playlists/{playlist_id}").status_code == 404


def test_playlist_rejects_video_without_access(world, login, client):
    response = client.post(
        "/api/auth/register",
        json={"email": "stranger@example.com", "username": "stranger", "password": "Stranger123!"},
    )
    assert response.status_code == 201
    stranger = client

    playlist = stranger.post("/api/playlists", json={"title": "Чужое"})
    assert playlist.status_code == 201
    playlist_id = playlist.json()["id"]

    denied = stranger.post(
        f"/api/playlists/{playlist_id}/items",
        json={"video_id": world.videos["private"]},
    )
    assert denied.status_code == 403


def test_playlist_owner_only(world, login):
    user = login("user")
    response = user.patch(
        f"/api/playlists/{world.playlists['public']}",
        json={"title": "Чужая подборка"},
    )
    assert response.status_code == 403


def test_history_and_clear(world, login):
    user = login("user")

    history = user.get("/api/history")
    assert history.status_code == 200
    assert len(history.json()) == 1

    assert user.delete(f"/api/history/{world.videos['public1']}").status_code == 200
    assert user.get("/api/history").json() == []

    user.post(f"/api/videos/{world.videos['public2']}/view", json={"position_seconds": 1})
    assert len(user.get("/api/history").json()) == 1

    assert user.delete("/api/history").status_code == 200
    assert user.get("/api/history").json() == []
