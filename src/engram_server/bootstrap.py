from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engram_server.bootstrap_state import record_project_mcp_status


SERVER_NAME = "engram-server"
DEFAULT_PACKS_DIR = "~/.engram"
CLAUDE_SETTINGS_RELATIVE = Path(".claude/settings.json")
CLAUDE_DESKTOP_CONFIG_MAC = Path(
    "Library/Application Support/Claude/claude_desktop_config.json"
)
PROJECT_MCP_FILENAME = ".mcp.json"


@dataclass(slots=True)
class BootstrapResult:
    already_configured: bool
    wrote_project_config: bool
    location: Path | None
    source: str
    message: str


def _normalize_json_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {}


def load_json_file(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_mcp_server_entry(repo_root: Path, packs_dir: str = DEFAULT_PACKS_DIR) -> dict[str, Any]:
    return {
        "command": "uv",
        "args": [
            "run",
            "--directory",
            str(repo_root.resolve()),
            SERVER_NAME,
            "--packs-dir",
            packs_dir,
        ],
    }


def build_mcp_payload(repo_root: Path, packs_dir: str = DEFAULT_PACKS_DIR) -> dict[str, Any]:
    return {
        "mcpServers": {
            SERVER_NAME: build_mcp_server_entry(repo_root=repo_root, packs_dir=packs_dir)
        }
    }


def has_engram_server(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    servers = payload.get("mcpServers")
    return isinstance(servers, dict) and SERVER_NAME in servers


def detect_existing_mcp(
    *,
    project_root: Path,
    home: Path | None = None,
) -> tuple[str, Path] | None:
    user_home = (home or Path.home()).expanduser().resolve()
    project_config = project_root / PROJECT_MCP_FILENAME
    project_payload = load_json_file(project_config)
    if has_engram_server(project_payload):
        return ("project", project_config)

    claude_settings = user_home / CLAUDE_SETTINGS_RELATIVE
    claude_payload = load_json_file(claude_settings)
    if has_engram_server(claude_payload):
        return ("claude-settings", claude_settings)

    claude_desktop = user_home / CLAUDE_DESKTOP_CONFIG_MAC
    claude_desktop_payload = load_json_file(claude_desktop)
    if has_engram_server(claude_desktop_payload):
        return ("claude-desktop", claude_desktop)

    return None


def ensure_project_mcp(
    *,
    project_root: Path,
    repo_root: Path,
    packs_dir: str = DEFAULT_PACKS_DIR,
    home: Path | None = None,
    force: bool = False,
) -> BootstrapResult:
    project_root = project_root.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()

    existing = detect_existing_mcp(project_root=project_root, home=home)
    if existing and not force:
        source, location = existing
        result = BootstrapResult(
            already_configured=True,
            wrote_project_config=False,
            location=location,
            source=source,
            message=f"已检测到 {SERVER_NAME} MCP 配置：{location}",
        )
        record_project_mcp_status(
            project_root=project_root,
            configured=True,
            source=result.source,
            location=result.location,
            wrote_project_config=result.wrote_project_config,
            home=home,
        )
        return result

    config_path = project_root / PROJECT_MCP_FILENAME
    payload = _normalize_json_payload(load_json_file(config_path))
    servers = payload.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    servers[SERVER_NAME] = build_mcp_server_entry(repo_root=repo_root, packs_dir=packs_dir)
    payload["mcpServers"] = servers
    write_json_file(config_path, payload)

    result = BootstrapResult(
        already_configured=False,
        wrote_project_config=True,
        location=config_path,
        source="project-created",
        message=f"已写入项目级 MCP 配置：{config_path}",
    )
    record_project_mcp_status(
        project_root=project_root,
        configured=True,
        source=result.source,
        location=result.location,
        wrote_project_config=result.wrote_project_config,
        home=home,
    )
    return result
