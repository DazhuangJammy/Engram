#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from engram_server.plugin_install import (
    install_strong_load,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Engram strong-load plugin")
    parser.add_argument(
        "--host",
        choices=["auto", "all", "claude", "codex", "openclaw"],
        default="auto",
        help="Host to install the strong-load plugin into",
    )
    parser.add_argument(
        "--repo-root",
        default=REPO_ROOT,
        help="Engram repository root",
    )
    parser.add_argument(
        "--bundle-dir",
        default=REPO_ROOT / "plugins" / "engram-strong-load",
        help="Plugin bundle directory inside the repo",
    )
    parser.add_argument(
        "--skill-source",
        default=REPO_ROOT / "SKILL.md",
        help="Root SKILL.md used as the single source of truth",
    )
    parser.add_argument(
        "--packs-dir",
        default="~/.engram",
        help="packs dir embedded into the bundled .mcp.json",
    )
    parser.add_argument(
        "--home",
        default=Path.home(),
        help="Home directory override for testing",
    )
    parser.add_argument(
        "--install-policy",
        choices=["AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"],
        default="INSTALLED_BY_DEFAULT",
        help="Codex marketplace install policy",
    )
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    home = Path(args.home).expanduser().resolve()
    installed = install_strong_load(
        host=args.host,
        repo_root=Path(args.repo_root),
        bundle_dir=Path(args.bundle_dir),
        skill_source=Path(args.skill_source),
        packs_dir=args.packs_dir,
        home=home,
        install_policy=args.install_policy,
    )
    for host, target in installed.items():
        print(f"[{host}] installed: {target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
