from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engram_server.bootstrap import build_mcp_payload, write_json_file
from engram_server.bootstrap_state import record_plugin_accepted


PLUGIN_NAME = "engram-strong-load"
SKILL_NAME = "engram"
PLUGIN_VERSION = "0.1.0"
CLAUDE_LOCAL_VERSION = "local-dev"
CLAUDE_PLUGIN_KEY = f"{PLUGIN_NAME}@{PLUGIN_NAME}"
OPENCLAW_MARKER = "## Engram"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        return json.loads(json.dumps(default))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(default))
    if isinstance(payload, dict):
        return payload
    return json.loads(json.dumps(default))


def _plugin_description() -> str:
    return (
        "Always-on strong-load plugin for Engram expert memory routing. "
        "It keeps the full Engram routing skill available at conversation start, "
        "bootstraps engram-server MCP when missing, and then lets the model decide "
        "which expert to load and which memory operations to run."
    )


def _author_block() -> dict[str, str]:
    return {
        "name": "Engram MCP Server Contributors",
        "email": "support@example.com",
        "url": "https://github.com/DazhuangJammy/Engram",
    }


def build_codex_plugin_manifest() -> dict[str, Any]:
    return {
        "name": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "description": _plugin_description(),
        "author": _author_block(),
        "homepage": "https://github.com/DazhuangJammy/Engram",
        "repository": "https://github.com/DazhuangJammy/Engram",
        "license": "MIT",
        "keywords": [
            "engram",
            "mcp",
            "expert-memory",
            "skill",
            "plugin",
            "codex",
            "claude-code",
            "openclaw",
        ],
        "skills": "./skills/",
        "mcpServers": "./.mcp.json",
        "interface": {
            "displayName": "Engram",
            "shortDescription": "Always load Engram routing before expert selection.",
            "longDescription": (
                "Make Engram behave like an always-on expert routing layer. "
                "At chat start it loads the full routing policy, ensures engram-server "
                "MCP exists, then routes to the right expert pack and memory workflow."
            ),
            "developerName": "Engram",
            "category": "Productivity",
            "capabilities": ["Interactive", "Write"],
            "websiteURL": "https://github.com/DazhuangJammy/Engram",
            "privacyPolicyURL": "https://github.com/DazhuangJammy/Engram",
            "termsOfServiceURL": "https://github.com/DazhuangJammy/Engram",
            "defaultPrompt": [
                "Always load Engram before answering in this project.",
                "Bootstrap engram-server MCP if it is missing.",
                "Give me a professional answer using the right Engram expert.",
            ],
            "brandColor": "#1F7A6C",
        },
    }


def build_claude_plugin_manifest() -> dict[str, Any]:
    return {
        "name": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "description": _plugin_description(),
        "author": {
            "name": "Engram MCP Server Contributors",
            "email": "support@example.com",
        },
        "repository": "https://github.com/DazhuangJammy/Engram",
        "license": "MIT",
        "keywords": ["engram", "mcp", "expert-memory", "always-on", "claude-code"],
        "skills": "./skills/",
    }


def build_claude_marketplace_manifest() -> dict[str, Any]:
    return {
        "name": PLUGIN_NAME,
        "owner": {"name": "DazhuangJammy"},
        "metadata": {
            "description": _plugin_description(),
            "version": PLUGIN_VERSION,
        },
        "plugins": [
            {
                "name": PLUGIN_NAME,
                "source": "./",
                "description": _plugin_description(),
                "version": PLUGIN_VERSION,
                "author": {
                    "name": "Engram MCP Server Contributors",
                    "email": "support@example.com",
                },
                "homepage": "https://github.com/DazhuangJammy/Engram",
                "repository": "https://github.com/DazhuangJammy/Engram",
                "license": "MIT",
                "keywords": [
                    "engram",
                    "mcp",
                    "expert-memory",
                    "always-on",
                    "claude-code",
                ],
                "category": "development",
                "tags": ["engram", "mcp", "memory", "routing"],
                "skills": "./skills/",
            }
        ],
    }


def sync_plugin_bundle(
    *,
    bundle_dir: Path,
    repo_root: Path,
    skill_text: str,
    packs_dir: str,
) -> Path:
    bundle_dir = bundle_dir.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()
    bundle_dir.mkdir(parents=True, exist_ok=True)

    skill_root = bundle_dir / "skills"
    if skill_root.exists():
        shutil.rmtree(skill_root)
    skill_dir = skill_root / SKILL_NAME
    skill_dir.mkdir(parents=True, exist_ok=True)
    plugin_skill_text = skill_text.replace("<skill-base>", str(repo_root))
    (skill_dir / "SKILL.md").write_text(plugin_skill_text, encoding="utf-8")

    write_json_file(bundle_dir / ".mcp.json", build_mcp_payload(repo_root, packs_dir))
    write_json_file(bundle_dir / ".codex-plugin" / "plugin.json", build_codex_plugin_manifest())
    write_json_file(bundle_dir / ".claude-plugin" / "plugin.json", build_claude_plugin_manifest())
    write_json_file(
        bundle_dir / ".claude-plugin" / "marketplace.json",
        build_claude_marketplace_manifest(),
    )
    return bundle_dir


def _copy_bundle(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)


def install_codex_plugin(
    *,
    bundle_dir: Path,
    home: Path,
    install_policy: str = "INSTALLED_BY_DEFAULT",
) -> Path:
    home = home.expanduser().resolve()
    bundle_dir = bundle_dir.expanduser().resolve()
    target = home / "plugins" / PLUGIN_NAME
    _copy_bundle(bundle_dir, target)

    marketplace_path = home / ".agents" / "plugins" / "marketplace.json"
    payload = _load_json(
        marketplace_path,
        {
            "name": "engram-local",
            "interface": {"displayName": "Engram"},
            "plugins": [],
        },
    )
    plugins = payload.setdefault("plugins", [])
    if not isinstance(plugins, list):
        plugins = []
        payload["plugins"] = plugins

    entry = {
        "name": PLUGIN_NAME,
        "source": {"source": "local", "path": f"./plugins/{PLUGIN_NAME}"},
        "policy": {
            "installation": install_policy,
            "authentication": "ON_INSTALL",
        },
        "category": "Productivity",
    }

    for index, item in enumerate(plugins):
        if isinstance(item, dict) and item.get("name") == PLUGIN_NAME:
            plugins[index] = entry
            break
    else:
        plugins.append(entry)

    write_json_file(marketplace_path, payload)
    return target


def install_claude_plugin(*, bundle_dir: Path, home: Path) -> Path:
    home = home.expanduser().resolve()
    bundle_dir = bundle_dir.expanduser().resolve()
    install_root = home / ".claude" / "plugins"
    cache_path = install_root / "cache" / PLUGIN_NAME / PLUGIN_NAME / CLAUDE_LOCAL_VERSION
    marketplace_path = install_root / "marketplaces" / PLUGIN_NAME
    _copy_bundle(bundle_dir, cache_path)
    _copy_bundle(bundle_dir, marketplace_path)

    settings_path = home / ".claude" / "settings.json"
    settings = _load_json(settings_path, {"env": {}, "permissions": {"allow": []}})
    enabled = settings.setdefault("enabledPlugins", {})
    if not isinstance(enabled, dict):
        enabled = {}
        settings["enabledPlugins"] = enabled
    enabled[CLAUDE_PLUGIN_KEY] = True
    write_json_file(settings_path, settings)

    installed_path = install_root / "installed_plugins.json"
    installed = _load_json(installed_path, {"version": 2, "plugins": {}})
    plugin_map = installed.setdefault("plugins", {})
    if not isinstance(plugin_map, dict):
        plugin_map = {}
        installed["plugins"] = plugin_map
    now = _now_iso()
    existing = plugin_map.get(CLAUDE_PLUGIN_KEY)
    installed_at = now
    if isinstance(existing, list) and existing:
        first = existing[0]
        if isinstance(first, dict) and isinstance(first.get("installedAt"), str):
            installed_at = first["installedAt"]
    plugin_map[CLAUDE_PLUGIN_KEY] = [
        {
            "scope": "user",
            "installPath": str(cache_path),
            "version": CLAUDE_LOCAL_VERSION,
            "installedAt": installed_at,
            "lastUpdated": now,
            "gitCommitSha": "local-dev",
        }
    ]
    write_json_file(installed_path, installed)

    known_path = install_root / "known_marketplaces.json"
    known = _load_json(known_path, {})
    known[PLUGIN_NAME] = {
        "source": {"source": "local", "path": str(bundle_dir)},
        "installLocation": str(marketplace_path),
        "lastUpdated": now,
    }
    write_json_file(known_path, known)
    return cache_path


def install_openclaw_strong_load(*, skill_text: str, repo_root: Path, home: Path) -> Path:
    home = home.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()
    workspace = home / ".openclaw" / "workspace"
    skill_path = workspace / "skills" / SKILL_NAME / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(skill_text, encoding="utf-8")

    mcp_path = workspace / ".mcp.json"
    write_json_file(mcp_path, build_mcp_payload(repo_root, "~/.engram"))

    agents_path = workspace / "AGENTS.md"
    existing = agents_path.read_text(encoding="utf-8") if agents_path.is_file() else ""
    snippet = (
        f"\n\n{OPENCLAW_MARKER}\n\n"
        "Before handling any user request, read `skills/engram/SKILL.md` and "
        "treat it as mandatory routing policy. If `engram-server` MCP is unavailable, "
        "bootstrap it immediately from the current Engram repository before continuing.\n"
    )
    if OPENCLAW_MARKER not in existing:
        agents_path.write_text(existing.rstrip() + snippet + "\n", encoding="utf-8")
    return skill_path


def resolve_hosts(requested: str, home: Path) -> list[str]:
    if requested == "all":
        return ["claude", "codex", "openclaw"]
    if requested == "auto":
        hosts = detected_hosts(home)
        return hosts or ["claude", "codex", "openclaw"]
    return [requested]


def install_strong_load(
    *,
    host: str,
    repo_root: Path,
    bundle_dir: Path,
    skill_source: Path,
    packs_dir: str,
    home: Path,
    install_policy: str = "INSTALLED_BY_DEFAULT",
) -> dict[str, Path]:
    repo_root = repo_root.expanduser().resolve()
    bundle_dir = bundle_dir.expanduser().resolve()
    skill_source = skill_source.expanduser().resolve()
    home = home.expanduser().resolve()

    skill_text = skill_source.read_text(encoding="utf-8")
    sync_plugin_bundle(
        bundle_dir=bundle_dir,
        repo_root=repo_root,
        skill_text=skill_text,
        packs_dir=packs_dir,
    )

    targets: dict[str, Path] = {}
    resolved_hosts = resolve_hosts(host, home)
    for current_host in resolved_hosts:
        if current_host == "codex":
            target = install_codex_plugin(
                bundle_dir=bundle_dir,
                home=home,
                install_policy=install_policy,
            )
        elif current_host == "claude":
            target = install_claude_plugin(bundle_dir=bundle_dir, home=home)
        else:
            target = install_openclaw_strong_load(
                skill_text=skill_text,
                repo_root=repo_root,
                home=home,
            )
        targets[current_host] = target

    record_plugin_accepted(installed_hosts=resolved_hosts, home=home)
    return targets


def detected_hosts(home: Path) -> list[str]:
    home = home.expanduser().resolve()
    hosts: list[str] = []
    if (home / ".codex").exists():
        hosts.append("codex")
    if (home / ".claude").exists():
        hosts.append("claude")
    if (home / ".openclaw").exists():
        hosts.append("openclaw")
    return hosts
