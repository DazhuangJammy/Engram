#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from engram_server.bootstrap_state import (
    load_state,
    plugin_status,
    record_plugin_declined,
    reset_plugin_prompt,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read or update Engram bootstrap state")
    parser.add_argument(
        "--home",
        default=Path.home(),
        help="Home directory override for testing",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show", help="Print the full persisted bootstrap state")
    subparsers.add_parser("plugin-status", help="Print the strong-load plugin prompt status")
    subparsers.add_parser(
        "mark-plugin-declined",
        help="Persist that the user declined strong-load mode",
    )
    subparsers.add_parser(
        "reset-plugin-prompt",
        help="Clear the remembered strong-load prompt decision",
    )
    return parser.parse_args()


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    args = parse_args()
    home = Path(args.home).expanduser().resolve()

    if args.command == "show":
        _print_json(load_state(home=home))
    elif args.command == "plugin-status":
        _print_json(plugin_status(home=home))
    elif args.command == "mark-plugin-declined":
        _print_json(record_plugin_declined(home=home))
    else:
        _print_json(reset_plugin_prompt(home=home))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
