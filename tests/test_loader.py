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
