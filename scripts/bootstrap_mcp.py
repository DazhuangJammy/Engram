#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from engram_server.bootstrap import DEFAULT_PACKS_DIR, ensure_project_mcp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap engram-server MCP config")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root where .mcp.json should be created if needed",
    )
    parser.add_argument(
        "--repo-root",
        default=REPO_ROOT,
        help="Engram repository root used by the MCP command",
    )
    parser.add_argument(
        "--packs-dir",
        default=DEFAULT_PACKS_DIR,
        help="packs dir argument passed to engram-server",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Write project .mcp.json even if a global configuration already exists",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = ensure_project_mcp(
        project_root=Path(args.project_root),
        repo_root=Path(args.repo_root),
        packs_dir=args.packs_dir,
        force=args.force,
    )
    print(result.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
