from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_SCHEMA_VERSION = 1
STATE_RELATIVE_PATH = Path(".engram/plugin-state.json")
PLUGIN_CHOICES = {"unknown", "accepted", "declined"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def state_file_path(home: Path | None = None) -> Path:
    return ((home or Path.home()).expanduser().resolve() / STATE_RELATIVE_PATH).resolve()


def _default_state() -> dict[str, Any]:
    return {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "pluginPrompt": {
            "asked": False,
            "choice": "unknown",
            "updatedAt": None,
            "installedHosts": [],
        },
        "projects": {},
    }


def _normalize_hosts(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    hosts: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        host = item.strip()
        if not host or host in seen:
            continue
        seen.add(host)
        hosts.append(host)
    return hosts


def _normalize_project_entry(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    mcp_payload = value.get("mcp")
    mcp: dict[str, Any] = {
        "configured": False,
        "source": "unknown",
        "location": None,
        "wroteProjectConfig": False,
    }
    if isinstance(mcp_payload, dict):
        if isinstance(mcp_payload.get("configured"), bool):
            mcp["configured"] = mcp_payload["configured"]
        if isinstance(mcp_payload.get("source"), str):
            mcp["source"] = mcp_payload["source"]
        location = mcp_payload.get("location")
        if isinstance(location, str) or location is None:
            mcp["location"] = location
        if isinstance(mcp_payload.get("wroteProjectConfig"), bool):
            mcp["wroteProjectConfig"] = mcp_payload["wroteProjectConfig"]

    entry: dict[str, Any] = {
        "lastCheckedAt": None,
        "mcp": mcp,
    }
    last_checked_at = value.get("lastCheckedAt")
    if isinstance(last_checked_at, str) or last_checked_at is None:
        entry["lastCheckedAt"] = last_checked_at
    return entry


def _normalize_state(payload: Any) -> dict[str, Any]:
    state = _default_state()
    if not isinstance(payload, dict):
        return state

    if isinstance(payload.get("schemaVersion"), int):
        state["schemaVersion"] = payload["schemaVersion"]

    plugin_prompt = payload.get("pluginPrompt")
    if isinstance(plugin_prompt, dict):
        if isinstance(plugin_prompt.get("asked"), bool):
            state["pluginPrompt"]["asked"] = plugin_prompt["asked"]
        choice = plugin_prompt.get("choice")
        if isinstance(choice, str) and choice in PLUGIN_CHOICES:
            state["pluginPrompt"]["choice"] = choice
        updated_at = plugin_prompt.get("updatedAt")
        if isinstance(updated_at, str) or updated_at is None:
            state["pluginPrompt"]["updatedAt"] = updated_at
        state["pluginPrompt"]["installedHosts"] = _normalize_hosts(
            plugin_prompt.get("installedHosts")
        )

    projects = payload.get("projects")
    if isinstance(projects, dict):
        normalized_projects: dict[str, dict[str, Any]] = {}
        for key, value in projects.items():
            if not isinstance(key, str):
                continue
            entry = _normalize_project_entry(value)
            if entry is not None:
                normalized_projects[key] = entry
        state["projects"] = normalized_projects

    return state


def load_state(home: Path | None = None) -> dict[str, Any]:
    path = state_file_path(home=home)
    if not path.is_file():
        return _default_state()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_state()
    return _normalize_state(payload)


def write_state(state: dict[str, Any], home: Path | None = None) -> Path:
    path = state_file_path(home=home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_normalize_state(state), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def plugin_status(home: Path | None = None) -> dict[str, Any]:
    status = load_state(home=home)["pluginPrompt"]
    return {
        "asked": status["asked"],
        "choice": status["choice"],
        "updatedAt": status["updatedAt"],
        "installedHosts": list(status["installedHosts"]),
        "shouldAsk": should_prompt_plugin(home=home),
        "statePath": str(state_file_path(home=home)),
    }


def should_prompt_plugin(home: Path | None = None) -> bool:
    status = load_state(home=home)["pluginPrompt"]
    return not status["asked"] or status["choice"] == "unknown"


def record_project_mcp_status(
    *,
    project_root: Path,
    configured: bool,
    source: str,
    location: Path | None,
    wrote_project_config: bool,
    home: Path | None = None,
) -> dict[str, Any]:
    state = load_state(home=home)
    key = str(project_root.expanduser().resolve())
    state["projects"][key] = {
        "lastCheckedAt": _now_iso(),
        "mcp": {
            "configured": configured,
            "source": source,
            "location": str(location.expanduser().resolve()) if location is not None else None,
            "wroteProjectConfig": wrote_project_config,
        },
    }
    write_state(state, home=home)
    return state["projects"][key]


def record_plugin_choice(
    *,
    choice: str,
    installed_hosts: list[str] | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    if choice not in PLUGIN_CHOICES - {"unknown"}:
        raise ValueError(f"Unsupported plugin choice: {choice}")

    state = load_state(home=home)
    plugin_prompt = state["pluginPrompt"]
    plugin_prompt["asked"] = True
    plugin_prompt["choice"] = choice
    plugin_prompt["updatedAt"] = _now_iso()
    if installed_hosts is not None:
        plugin_prompt["installedHosts"] = _normalize_hosts(installed_hosts)
    write_state(state, home=home)
    return plugin_status(home=home)


def record_plugin_declined(home: Path | None = None) -> dict[str, Any]:
    return record_plugin_choice(choice="declined", installed_hosts=[], home=home)


def record_plugin_accepted(
    *,
    installed_hosts: list[str],
    home: Path | None = None,
) -> dict[str, Any]:
    return record_plugin_choice(choice="accepted", installed_hosts=installed_hosts, home=home)


def reset_plugin_prompt(home: Path | None = None) -> dict[str, Any]:
    state = load_state(home=home)
    state["pluginPrompt"] = _default_state()["pluginPrompt"]
    write_state(state, home=home)
    return plugin_status(home=home)
