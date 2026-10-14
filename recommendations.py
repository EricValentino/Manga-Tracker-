"""LLM-backed recommendations built from the user's saved list."""

import json
import os
from collections.abc import Sequence
from typing import Any, Protocol

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_RECOMMENDATIONS = 4


class RecommendationError(RuntimeError):
    """The recommendation service is not configured or returned an unusable answer."""


class _HasTitleGenre(Protocol):
    title: str
    genre: str


_client: Any | None = None


def _get_client():
    """Create the OpenAI client lazily so the app (and tests) start without an API key."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RecommendationError("OPENAI_API_KEY is not set")
        from openai import OpenAI

        _client = OpenAI(api_key=api_key)
    return _client


def build_prompt(manga_list: Sequence[_HasTitleGenre]) -> str:
    summary = "\n".join(f"- {m.title} ({m.genre})" for m in manga_list)
    return (
        "Here is a user's manga reading list:\n"
        f"{summary}\n\n"
        f"Recommend {MAX_RECOMMENDATIONS} manga they have not already read that they would "
        "likely enjoy. Respond with a JSON object of this exact shape:\n"
        '{"recommendations": [{"title": "string", "genre": "string", '
        '"reason": "one sentence why they would like it"}]}'
    )


def parse_recommendations(raw_text: str, already_saved: Sequence[str] = ()) -> list[dict[str, str]]:
    """Validate the model's JSON and drop malformed items or titles already on the list."""
    try:
        data = json.loads(raw_text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RecommendationError("Model did not return valid JSON") from exc

    items = data.get("recommendations") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise RecommendationError("Model response is missing 'recommendations'")

    saved = {t.strip().casefold() for t in already_saved}
    cleaned: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("title"), str):
            continue
        title = item["title"].strip()
        if not title or title.casefold() in saved:
            continue
        cleaned.append(
            {
                "title": title,
                "genre": str(item.get("genre", "")),
                "reason": str(item.get("reason", "")),
            }
        )
    return cleaned[:MAX_RECOMMENDATIONS]


def get_recommendations(manga_list: Sequence[_HasTitleGenre]) -> list[dict[str, str]]:
    if not manga_list:
        return []

    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": build_prompt(manga_list)}],
        response_format={"type": "json_object"},
    )
    return parse_recommendations(
        response.choices[0].message.content, already_saved=[m.title for m in manga_list]
    )
