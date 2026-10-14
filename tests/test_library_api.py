"""CRUD behaviour of the manga, anime and progress endpoints."""


def test_health(client):
    assert client.get("/").json() == {"message": "Manga tracker API is alive"}


def test_create_and_list_manga(client, saved_manga):
    assert saved_manga["id"] is not None
    assert [m["title"] for m in client.get("/manga").json()] == ["Vagabond"]


def test_client_cannot_choose_manga_id(client):
    response = client.post("/manga", json={"id": 999, "title": "Berserk", "genre": "Dark Fantasy"})
    assert response.status_code == 201
    assert response.json()["id"] != 999


def test_create_manga_requires_title(client):
    assert client.post("/manga", json={"genre": "Drama"}).status_code == 422


def test_patch_manga_updates_only_known_fields(client, saved_manga):
    response = client.patch(
        f"/manga/{saved_manga['id']}", json={"genre": "Seinen", "id": 42, "is_admin": True}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["genre"] == "Seinen"
    assert body["id"] == saved_manga["id"]
    assert "is_admin" not in body


def test_missing_manga_returns_404(client):
    assert client.patch("/manga/123", json={"genre": "x"}).status_code == 404
    assert client.delete("/manga/123").status_code == 404


def test_progress_lifecycle(client, saved_manga):
    created = client.post(
        "/progress", json={"manga_id": saved_manga["id"], "chapter": 3, "status": "reading"}
    )
    assert created.status_code == 201
    progress_id = created.json()["id"]

    updated = client.patch(f"/progress/{progress_id}", json={"chapter": 10, "rating": 9})
    assert updated.status_code == 200
    assert updated.json()["chapter"] == 10
    assert updated.json()["rating"] == 9
    assert updated.json()["status"] == "reading"

    assert client.delete(f"/progress/{progress_id}").status_code == 200
    assert client.get("/progress").json() == []


def test_progress_validation(client, saved_manga):
    base = {"manga_id": saved_manga["id"], "chapter": 1}
    assert client.post("/progress", json={**base, "rating": 11}).status_code == 422
    assert client.post("/progress", json={**base, "rating": 0}).status_code == 422
    assert client.post("/progress", json={**base, "chapter": -1}).status_code == 422
    assert client.post("/progress", json={**base, "status": "dropped??"}).status_code == 422


def test_progress_requires_existing_manga(client):
    assert client.post("/progress", json={"manga_id": 77, "chapter": 1}).status_code == 404


def test_only_one_progress_record_per_manga(client, saved_manga):
    body = {"manga_id": saved_manga["id"], "chapter": 1}
    assert client.post("/progress", json=body).status_code == 201
    assert client.post("/progress", json=body).status_code == 409


def test_deleting_manga_removes_its_progress(client, saved_manga):
    client.post("/progress", json={"manga_id": saved_manga["id"], "chapter": 5})
    assert client.delete(f"/manga/{saved_manga['id']}").status_code == 200
    assert client.get("/progress").json() == []


def test_create_and_list_anime(client):
    response = client.post("/anime", json={"title": "Mushishi", "genre": "Slice of Life"})
    assert response.status_code == 201
    assert [a["title"] for a in client.get("/anime").json()] == ["Mushishi"]
