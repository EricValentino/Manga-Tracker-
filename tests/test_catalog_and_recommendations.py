"""Endpoints that call AniList or OpenAI; both services are replaced with fakes."""

import pytest

import anilist
import recommendations as recs_service

COVER = {"large": "https://img.example/cover.jpg"}


def test_search_returns_match(client, monkeypatch):
    def fake_search(title, kind):
        return {"id": 1, "title": {"romaji": title}}

    monkeypatch.setattr(anilist, "search_media", fake_search)
    response = client.get("/search", params={"title": "Monster"})
    assert response.status_code == 200
    assert response.json()["title"]["romaji"] == "Monster"


def test_search_no_match_is_404(client, monkeypatch):
    monkeypatch.setattr(anilist, "search_media", lambda title, kind: None)
    assert client.get("/search", params={"title": "zzzz"}).status_code == 404


def test_search_upstream_failure_is_502(client, monkeypatch):
    def boom(*_args):
        raise anilist.AniListError("timeout")

    monkeypatch.setattr(anilist, "search_media", boom)
    assert client.get("/search", params={"title": "Monster"}).status_code == 502


def test_search_requires_title(client):
    assert client.get("/search", params={"title": ""}).status_code == 422


@pytest.mark.parametrize("path", ["/discover", "/discover-anime"])
def test_discover_rejects_unknown_sort(client, path):
    assert client.get(path, params={"sort": "DROP TABLE"}).status_code == 422


def test_discover_passes_country(client, monkeypatch):
    seen = {}

    def fake_list(sort, country=None):
        seen.update(sort=sort, country=country)
        return [{"id": 1}]

    monkeypatch.setattr(anilist, "get_manga_list", fake_list)
    response = client.get("/discover", params={"sort": "POPULARITY_DESC", "country": "KR"})
    assert response.status_code == 200
    assert seen == {"sort": "POPULARITY_DESC", "country": "KR"}


def test_details_validates_type(client):
    assert client.get("/details", params={"id": 1, "type": "BOOK"}).status_code == 422


def test_recommendations_enriched_with_covers(client, saved_manga, monkeypatch):
    monkeypatch.setattr(
        recs_service,
        "get_recommendations",
        lambda manga: [
            {"title": "Real", "genre": "Sports", "reason": "Inoue again"},
            {"title": "Unknown Title", "genre": "?", "reason": "?"},
        ],
    )
    monkeypatch.setattr(
        anilist, "search_manga", lambda title: {"coverImage": COVER} if title == "Real" else None
    )
    recs = client.get("/recommendations").json()
    assert recs[0]["cover_image"] == COVER["large"]
    assert recs[1]["cover_image"] is None


def test_recommendations_survive_cover_lookup_outage(client, saved_manga, monkeypatch):
    one_rec = [{"title": "Real", "genre": "", "reason": ""}]
    monkeypatch.setattr(recs_service, "get_recommendations", lambda manga: one_rec)

    def boom(_title):
        raise anilist.AniListError("down")

    monkeypatch.setattr(anilist, "search_manga", boom)
    response = client.get("/recommendations")
    assert response.status_code == 200
    assert response.json()[0]["cover_image"] is None


def test_recommendations_without_api_key_is_503(client, saved_manga, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(recs_service, "_client", None)
    assert client.get("/recommendations").status_code == 503


def test_recommendations_empty_library_skips_llm(client, monkeypatch):
    def must_not_call():
        pytest.fail("LLM should not be called for an empty library")

    monkeypatch.setattr(recs_service, "_get_client", must_not_call)
    assert client.get("/recommendations").json() == []
