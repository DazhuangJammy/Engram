from __future__ import annotations

import json
from pathlib import Path

from engram_server.bootstrap import (
    SERVER_NAME,
    build_mcp_payload,
    ensure_project_mcp,
)
from engram_server.bootstrap_state import load_state


def test_build_mcp_payload_uses_repo_root_and_packs_dir(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    payload = build_mcp_payload(repo_root=repo_root, packs_dir="~/.engram")

    assert payload == {
        "mcpServers": {
            SERVER_NAME: {
                "command": "uv",
                "args": [
                    "run",
                    "--directory",
                    str(repo_root.resolve()),
                    SERVER_NAME,
                    "--packs-dir",
                    "~/.engram",
                ],
            }
        }
    }


def test_ensure_project_mcp_writes_local_config_when_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    project_root = tmp_path / "project"
    home = tmp_path / "home"
    repo_root.mkdir()
    project_root.mkdir()
    home.mkdir()

    result = ensure_project_mcp(
        project_root=project_root,
        repo_root=repo_root,
        home=home,
    )

    assert result.wrote_project_config is True
    config_path = project_root / ".mcp.json"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["mcpServers"][SERVER_NAME]["args"][1] == "--directory"
    assert payload["mcpServers"][SERVER_NAME]["args"][2] == str(repo_root.resolve())
    state = load_state(home=home)
    project_state = state["projects"][str(project_root.resolve())]
    assert project_state["mcp"]["configured"] is True
    assert project_state["mcp"]["source"] == "project-created"
    assert project_state["mcp"]["location"] == str(config_path.resolve())
    assert project_state["mcp"]["wroteProjectConfig"] is True


def test_ensure_project_mcp_skips_when_claude_settings_already_have_server(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    project_root = tmp_path / "project"
    home = tmp_path / "home"
    repo_root.mkdir()
    project_root.mkdir()
    settings_path = home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(build_mcp_payload(repo_root=repo_root), ensure_ascii=False),
        encoding="utf-8",
    )

    result = ensure_project_mcp(
        project_root=project_root,
        repo_root=repo_root,
        home=home,
    )

    assert result.already_configured is True
    assert result.wrote_project_config is False
    assert result.source == "claude-settings"
    assert not (project_root / ".mcp.json").exists()
    state = load_state(home=home)
    project_state = state["projects"][str(project_root.resolve())]
    assert project_state["mcp"]["configured"] is True
    assert project_state["mcp"]["source"] == "claude-settings"
    assert project_state["mcp"]["location"] == str(settings_path.resolve())
    assert project_state["mcp"]["wroteProjectConfig"] is False
