from __future__ import annotations

import json
from pathlib import Path

from engram_server.bootstrap_state import (
    load_state,
    record_plugin_declined,
    reset_plugin_prompt,
    should_prompt_plugin,
)
from engram_server.plugin_install import (
    CLAUDE_PLUGIN_KEY,
    PLUGIN_NAME,
    SKILL_NAME,
    install_strong_load,
    install_claude_plugin,
    install_codex_plugin,
    install_openclaw_strong_load,
    sync_plugin_bundle,
)


SKILL_TEXT = (
    "---\nname: engram\ndescription: test\n---\n\n"
    "# Test\nUse <skill-base>/scripts/bootstrap_mcp.py\n"
)


def test_sync_plugin_bundle_materializes_manifests_and_skill(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    bundle_dir = tmp_path / "bundle"
    repo_root.mkdir()

    sync_plugin_bundle(
        bundle_dir=bundle_dir,
        repo_root=repo_root,
        skill_text=SKILL_TEXT,
        packs_dir="~/.engram",
    )

    plugin_skill = (bundle_dir / "skills" / SKILL_NAME / "SKILL.md").read_text(encoding="utf-8")
    assert str(repo_root.resolve()) in plugin_skill
    assert "<skill-base>" not in plugin_skill
    mcp_payload = json.loads((bundle_dir / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp_payload["mcpServers"]["engram-server"]["args"][2] == str(repo_root.resolve())
    assert (bundle_dir / ".codex-plugin" / "plugin.json").is_file()
    assert (bundle_dir / ".claude-plugin" / "plugin.json").is_file()


def test_install_codex_plugin_updates_home_marketplace(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    bundle_dir = tmp_path / "bundle"
    home = tmp_path / "home"
    repo_root.mkdir()
    home.mkdir()
    sync_plugin_bundle(
        bundle_dir=bundle_dir,
        repo_root=repo_root,
        skill_text=SKILL_TEXT,
        packs_dir="~/.engram",
    )

    target = install_codex_plugin(bundle_dir=bundle_dir, home=home)

    assert (target / ".codex-plugin" / "plugin.json").is_file()
    marketplace = json.loads(
        (home / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
    )
    assert marketplace["plugins"][0]["name"] == PLUGIN_NAME
    assert marketplace["plugins"][0]["policy"]["installation"] == "INSTALLED_BY_DEFAULT"


def test_install_claude_plugin_updates_local_registry(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    bundle_dir = tmp_path / "bundle"
    home = tmp_path / "home"
    repo_root.mkdir()
    home.mkdir()
    sync_plugin_bundle(
        bundle_dir=bundle_dir,
        repo_root=repo_root,
        skill_text=SKILL_TEXT,
        packs_dir="~/.engram",
    )

    target = install_claude_plugin(bundle_dir=bundle_dir, home=home)

    assert (target / ".claude-plugin" / "plugin.json").is_file()
    settings = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"][CLAUDE_PLUGIN_KEY] is True
    installed = json.loads(
        (home / ".claude" / "plugins" / "installed_plugins.json").read_text(encoding="utf-8")
    )
    assert installed["plugins"][CLAUDE_PLUGIN_KEY][0]["installPath"] == str(target)


def test_install_openclaw_strong_load_updates_workspace(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    home = tmp_path / "home"
    repo_root.mkdir()
    (home / ".openclaw" / "workspace").mkdir(parents=True)
    agents_path = home / ".openclaw" / "workspace" / "AGENTS.md"
    agents_path.write_text("# Workspace\n", encoding="utf-8")

    skill_path = install_openclaw_strong_load(
        skill_text=SKILL_TEXT,
        repo_root=repo_root,
        home=home,
    )

    assert skill_path.read_text(encoding="utf-8") == SKILL_TEXT
    agents_content = agents_path.read_text(encoding="utf-8")
    assert "## Engram" in agents_content
    assert "skills/engram/SKILL.md" in agents_content


def test_install_strong_load_records_plugin_acceptance_once(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    bundle_dir = tmp_path / "bundle"
    home = tmp_path / "home"
    skill_source = tmp_path / "SKILL.md"
    repo_root.mkdir()
    home.mkdir()
    skill_source.write_text(SKILL_TEXT, encoding="utf-8")

    installed = install_strong_load(
        host="all",
        repo_root=repo_root,
        bundle_dir=bundle_dir,
        skill_source=skill_source,
        packs_dir="~/.engram",
        home=home,
    )

    assert set(installed) == {"claude", "codex", "openclaw"}
    state = load_state(home=home)
    assert state["pluginPrompt"]["asked"] is True
    assert state["pluginPrompt"]["choice"] == "accepted"
    assert set(state["pluginPrompt"]["installedHosts"]) == {"claude", "codex", "openclaw"}


def test_plugin_prompt_state_can_be_declined_and_reset(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()

    assert should_prompt_plugin(home=home) is True

    declined = record_plugin_declined(home=home)
    assert declined["choice"] == "declined"
    assert declined["shouldAsk"] is False
    assert should_prompt_plugin(home=home) is False

    reset = reset_plugin_prompt(home=home)
    assert reset["choice"] == "unknown"
    assert reset["shouldAsk"] is True
    assert should_prompt_plugin(home=home) is True
