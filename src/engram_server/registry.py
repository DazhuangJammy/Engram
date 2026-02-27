from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import urlopen


REGISTRY_URL = (
    "https://raw.githubusercontent.com/DazhuangJammy/Engram/main/registry.json"
)


def fetch_registry() -> list[dict]:
    try:
        with urlopen(REGISTRY_URL, timeout=30) as response:  # nosec: B310
            payload = response.read().decode("utf-8")
    except (OSError, URLError, TimeoutError):
        return []

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def search_registry(query: str, entries: list[dict]) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []

    results: list[dict] = []
    for entry in entries:
        name = str(entry.get("name", ""))
        description = str(entry.get("description", ""))
        tags = entry.get("tags", [])
        if not isinstance(tags, list):
            tags = [str(tags)]
        tags_text = " ".join(str(tag) for tag in tags)

        haystack = f"{name} {description} {tags_text}".lower()
        if q in haystack:
            results.append(entry)
    return results


def resolve_name(name: str, entries: list[dict]) -> str | None:
    for entry in entries:
        if entry.get("name") == name:
            source = entry.get("source")
            if isinstance(source, str) and source.strip():
                return source
            return None

    lowered = name.strip().lower()
    for entry in entries:
        entry_name = entry.get("name")
        if isinstance(entry_name, str) and entry_name.lower() == lowered:
            source = entry.get("source")
            if isinstance(source, str) and source.strip():
                return source
            return None
    return None
