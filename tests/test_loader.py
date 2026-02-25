from pathlib import Path

from engram_server.loader import EngramLoader


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_list_engrams_returns_expected_items() -> None:
    loader = EngramLoader(FIXTURES_DIR)

    items = loader.list_engrams()
    names = {item["name"] for item in items}

    assert {"fitness-coach", "contract-lawyer"}.issubset(names)


def test_get_engram_info_returns_meta() -> None:
    loader = EngramLoader(FIXTURES_DIR)

    info = loader.get_engram_info("fitness-coach")

    assert info is not None
    assert info["name"] == "fitness-coach"
    assert "10年教练经验" in info["description"]
    assert info["knowledge_count"] == 5
    assert info["examples_count"] == 3


def test_load_file_supports_nested_paths() -> None:
    loader = EngramLoader(FIXTURES_DIR)

    role = loader.load_file("fitness-coach", "role.md")
    knowledge = loader.load_file("fitness-coach", "knowledge/增肌训练基础.md")

    assert role is not None
    assert "专业健身教练" in role
    assert knowledge is not None
    assert "渐进超负荷" in knowledge


def test_load_file_returns_none_for_invalid_or_missing_file() -> None:
    loader = EngramLoader(FIXTURES_DIR)

    missing = loader.load_file("fitness-coach", "knowledge/不存在.md")
    escaped = loader.load_file("fitness-coach", "../contract-lawyer/meta.json")

    assert missing is None
    assert escaped is None


def test_list_files_returns_markdown_in_subdir() -> None:
    loader = EngramLoader(FIXTURES_DIR)

    files = loader.list_files("fitness-coach", "knowledge")

    assert files
    assert files[0] == "knowledge/_index.md"
    assert "knowledge/增肌训练基础.md" in files


def test_load_engram_base_returns_role_workflow_rules_and_indexes() -> None:
    loader = EngramLoader(FIXTURES_DIR)

    content = loader.load_engram_base("fitness-coach")

    assert content is not None
    assert "## 角色" in content
    assert "专业健身教练" in content
    assert "## 工作流程" in content
    assert "明确目标与限制条件" in content
    assert "## 规则" in content
    assert "常见错误" in content
    assert "## 知识索引" in content
    assert "knowledge/膝关节损伤训练.md" in content
    assert "摘要：" in content
    assert "## 案例索引" in content
    assert "examples/膝盖疼的上班族.md" in content
    assert "uses:" in content


def test_empty_directory_does_not_raise(tmp_path: Path) -> None:
    loader = EngramLoader(tmp_path)

    assert loader.list_engrams() == []


def test_missing_meta_directory_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "no-meta").mkdir(parents=True)
    (tmp_path / "has-meta").mkdir(parents=True)
    (tmp_path / "has-meta" / "meta.json").write_text(
        '{"name": "has-meta", "description": "ok"}', encoding="utf-8"
    )

    loader = EngramLoader(tmp_path)
    items = loader.list_engrams()

    assert len(items) == 1
    assert items[0]["name"] == "has-meta"


def _make_engram(tmp_path: Path, name: str = "test-expert") -> EngramLoader:
    """Helper to create a minimal engram for write/memory tests."""
    engram_dir = tmp_path / name
    engram_dir.mkdir()
    (engram_dir / "meta.json").write_text(
        f'{{"name": "{name}", "description": "test"}}', encoding="utf-8"
    )
    (engram_dir / "role.md").write_text("# test role", encoding="utf-8")
    return EngramLoader(tmp_path)


def test_write_file_creates_and_overwrites(tmp_path: Path) -> None:
    loader = _make_engram(tmp_path)

    assert loader.write_file("test-expert", "knowledge/topic.md", "v1")
    assert (tmp_path / "test-expert" / "knowledge" / "topic.md").read_text() == "v1"

    assert loader.write_file("test-expert", "knowledge/topic.md", "v2")
    assert (tmp_path / "test-expert" / "knowledge" / "topic.md").read_text() == "v2"


def test_write_file_append_mode(tmp_path: Path) -> None:
    loader = _make_engram(tmp_path)

    loader.write_file("test-expert", "notes.md", "line1\n")
    loader.write_file("test-expert", "notes.md", "line2\n", append=True)

    content = (tmp_path / "test-expert" / "notes.md").read_text()
    assert "line1" in content
    assert "line2" in content


def test_write_file_blocks_path_traversal(tmp_path: Path) -> None:
    loader = _make_engram(tmp_path)

    assert loader.write_file("test-expert", "../escape.md", "bad") is False


def test_capture_memory_creates_entry_and_index(tmp_path: Path) -> None:
    loader = _make_engram(tmp_path)

    ok = loader.capture_memory(
        "test-expert", "用户膝盖有旧伤", "user-profile", "膝关节活动度受限"
    )
    assert ok is True

    memory_dir = tmp_path / "test-expert" / "memory"
    assert memory_dir.is_dir()

    category_file = memory_dir / "user-profile.md"
    assert category_file.is_file()
    text = category_file.read_text()
    assert "用户膝盖有旧伤" in text
    assert "type:general" in text

    index_file = memory_dir / "_index.md"
    assert index_file.is_file()
    index_content = index_file.read_text()
    assert "膝关节活动度受限" in index_content
    assert "memory/user-profile.md" in index_content
    assert "[general]" in index_content


def test_capture_memory_with_type_and_tags(tmp_path: Path) -> None:
    loader = _make_engram(tmp_path)

    ok = loader.capture_memory(
        "test-expert",
        "用户偏好晨练，不喜欢夜间训练",
        "preferences",
        "偏好晨练",
        memory_type="preference",
        tags=["fitness", "schedule"],
    )
    assert ok is True

    category_file = tmp_path / "test-expert" / "memory" / "preferences.md"
    text = category_file.read_text()
    assert "type:preference" in text
    assert "tags:fitness,schedule" in text

    index_content = (tmp_path / "test-expert" / "memory" / "_index.md").read_text()
    assert "[preference]" in index_content
    assert "[fitness,schedule]" in index_content


def test_capture_memory_with_conversation_id(tmp_path: Path) -> None:
    loader = _make_engram(tmp_path)

    ok = loader.capture_memory(
        "test-expert",
        "本次对话决定从3x/week开始",
        "decisions",
        "初始训练频率3次/周",
        memory_type="decision",
        conversation_id="session-abc123",
    )
    assert ok is True

    text = (tmp_path / "test-expert" / "memory" / "decisions.md").read_text()
    assert "conv:session-abc123" in text
    assert "type:decision" in text


def test_capture_memory_throttle(tmp_path: Path) -> None:
    loader = _make_engram(tmp_path)
    content = "用户膝盖有旧伤"

    loader.capture_memory("test-expert", content, "user-profile", "膝关节活动度受限")
    loader.capture_memory("test-expert", content, "user-profile", "膝关节活动度受限")

    text = (tmp_path / "test-expert" / "memory" / "user-profile.md").read_text()
    # Only one entry should exist (second call throttled)
    assert text.count("用户膝盖有旧伤") == 1


def test_load_engram_base_includes_memory(tmp_path: Path) -> None:
    loader = _make_engram(tmp_path)

    loader.capture_memory(
        "test-expert", "喜欢早上训练", "preferences", "偏好晨练"
    )

    base = loader.load_engram_base("test-expert")
    assert base is not None
    assert "## 动态记忆" in base
    assert "偏好晨练" in base
