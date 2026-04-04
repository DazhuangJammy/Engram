# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added
- Added `SKILL.md` as the Engram routing source of truth for Codex/OpenClaw style skill loading.
- Added bootstrap helpers in `scripts/bootstrap_mcp.py` and `scripts/bootstrap_state.py` plus persisted state handling in `src/engram_server/bootstrap.py` and `src/engram_server/bootstrap_state.py`.
- Added strong-load plugin installation support for Claude, Codex, and OpenClaw in `scripts/install_strong_load.py` and `src/engram_server/plugin_install.py`.
- Added tests covering MCP bootstrap flow and plugin installation in `tests/test_bootstrap.py` and `tests/test_plugin_install.py`.

### Changed
- Renamed the main docs title from `Engram MCP Server` to `Engram` in `README.md` and `README_en.md`.
- Moved the routing reference doc from `CLAUDE.MD` to `CLAUDE参考.MD`, and updated auto-routing tests to follow the new source files.
