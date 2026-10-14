"""Pure-function tests for prompt building, LLM output parsing and AniList error mapping."""

from types import SimpleNamespace

import httpx
import pytest

import anilist
from recommendations import RecommendationError, build_prompt, parse_recommendations


def test_build_prompt_lists_titles():
    prompt = build_prompt([SimpleNamespace(title="Monster", genre="Thriller")])
    assert "- Monster (Thriller)" in prompt
    assert '"recommendations"' in prompt


def test_parse_drops_saved_and_malformed_items():
    raw = (
        '{"recommendations": ['
        '{"title": "Monster", "genre": "Thriller", "reason": "dup"},'
        '{"title": "Pluto", "genre": "Sci-fi", "reason": "Same author"},'
        '"not an object",'
        '{"genre": "missing title"}'
        "]}"
    )
    assert parse_recommendations(raw, already_saved=["monster "]) == [
        {"title": "Pluto", "genre": "Sci-fi", "reason": "Same author"}
    ]


def test_parse_caps_number_of_results():
    items = ",".join(f'{{"title": "T{i}"}}' for i in range(10))
    assert len(parse_recommendations(f'{{"recommendations": [{items}]}}')) == 4


@pytest.mark.parametrize("raw", ["not json", "[]", '{"other": 1}', None])
def test_parse_rejects_bad_shapes(raw):
    with pytest.raises(RecommendationError):
        parse_recommendations(raw)


def _fake_post(status, payload=None, exc=None):
    def fake(*_args, **_kwargs):
        if exc:
            raise exc
        request = httpx.Request("POST", anilist.ANILIST_URL)
        if payload is None:
            return httpx.Response(status, text="<html>oops</html>", request=request)
        return httpx.Response(status, json=payload, request=request)

    return fake


def test_anilist_not_found_returns_none(monkeypatch):
    monkeypatch.setattr(httpx, "post", _fake_post(404, {"data": {"Media": None}, "errors": [{}]}))
    assert anilist.search_manga("zzzz") is None


def test_anilist_success(monkeypatch):
    monkeypatch.setattr(httpx, "post", _fake_post(200, {"data": {"Media": {"id": 5}}}))
    assert anilist.get_details(5, "MANGA") == {"id": 5}


@pytest.mark.parametrize(
    "fake",
    [
        _fake_post(200, exc=httpx.ConnectTimeout("slow")),
        _fake_post(502),
        _fake_post(429, {"data": None, "errors": [{"message": "Too Many Requests"}]}),
    ],
)
def test_anilist_failures_raise(monkeypatch, fake):
    monkeypatch.setattr(httpx, "post", fake)
    with pytest.raises(anilist.AniListError):
        anilist.search_manga("Monster")


def test_anilist_list_handles_empty_page(monkeypatch):
    monkeypatch.setattr(httpx, "post", _fake_post(200, {"data": {"Page": None}}))
    assert anilist.get_anime_list("TRENDING_DESC") == []
