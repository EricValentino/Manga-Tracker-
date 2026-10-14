"""Thin client for the AniList GraphQL API (https://anilist.gitbook.io/anilist-apiv2-docs)."""

from typing import Any

import httpx

ANILIST_URL = "https://graphql.anilist.co"
TIMEOUT_SECONDS = 10.0


class AniListError(RuntimeError):
    """AniList could not be reached or returned an unusable response."""


_MEDIA_FIELDS = """
    id
    title { romaji english }
    genres
    chapters
    episodes
    description
    coverImage { large }
    averageScore
"""

SEARCH_QUERY = f"""
query ($search: String, $type: MediaType) {{
  Media(search: $search, type: $type) {{ {_MEDIA_FIELDS} }}
}}
"""

DETAILS_QUERY = f"""
query ($id: Int, $type: MediaType) {{
  Media(id: $id, type: $type) {{ {_MEDIA_FIELDS} }}
}}
"""

LIST_QUERY = """
query ($sort: [MediaSort], $type: MediaType, $country: CountryCode) {
  Page(perPage: 10) {
    media(type: $type, sort: $sort, countryOfOrigin: $country) {
      id
      title { romaji english }
      coverImage { large }
      averageScore
    }
  }
}
"""


def _post(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Run a GraphQL query and return its ``data`` object.

    AniList answers "no match" with HTTP 404 and ``data.Media = null``; that case is
    returned as data (so callers can map it to their own 404), while network
    failures, rate limiting and malformed responses raise ``AniListError``.
    """
    try:
        response = httpx.post(
            ANILIST_URL,
            json={"query": query, "variables": variables},
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise AniListError(f"AniList request failed: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise AniListError(f"AniList returned non-JSON (HTTP {response.status_code})") from exc

    data = payload.get("data") if isinstance(payload, dict) else None
    if data is None:
        raise AniListError(f"AniList returned no data (HTTP {response.status_code})")
    if response.status_code >= 500 or response.status_code == 429:
        raise AniListError(f"AniList unavailable (HTTP {response.status_code})")
    return data


def search_media(search_term: str, media_type: str = "MANGA") -> dict[str, Any] | None:
    """Best match for ``search_term``, or ``None`` when AniList has no match."""
    return _post(SEARCH_QUERY, {"search": search_term, "type": media_type}).get("Media")


def search_manga(search_term: str) -> dict[str, Any] | None:
    return search_media(search_term, "MANGA")


def search_anime(search_term: str) -> dict[str, Any] | None:
    return search_media(search_term, "ANIME")


def get_media_list(sort: str, media_type: str = "MANGA", country: str | None = None) -> list:
    variables: dict[str, Any] = {"sort": [sort], "type": media_type}
    if country:
        variables["country"] = country
    page = _post(LIST_QUERY, variables).get("Page") or {}
    return page.get("media") or []


def get_manga_list(sort: str, country: str | None = None) -> list:
    return get_media_list(sort, "MANGA", country)


def get_anime_list(sort: str) -> list:
    return get_media_list(sort, "ANIME")


def get_details(media_id: int, media_type: str) -> dict[str, Any] | None:
    return _post(DETAILS_QUERY, {"id": media_id, "type": media_type}).get("Media")
