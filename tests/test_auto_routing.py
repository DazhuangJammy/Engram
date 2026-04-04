from pathlib import Path


def _load_routing_doc() -> str:
    for candidate in ("CLAUDE参考.MD", "SKILL.md", "CLAUDE.MD"):
        path = Path(candidate)
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError("No routing document found")


def test_claude_md_contains_auto_routing_mapping() -> None:
    content = _load_routing_doc()

    # Natural-language intents should map to MCP tools directly.
    assert "找/查/推荐某类 Engram" in content
    assert "search_engrams" in content
    assert "install_engram" in content
    assert "stats_engrams" in content
    assert "create_engram_assistant" in content


def test_claude_md_does_not_tell_user_to_run_cli_for_stats() -> None:
    content = _load_routing_doc()
    assert "建议用户在终端运行" not in content
