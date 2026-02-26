from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from engram_server.server import _build_loader_roots


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


def _result_text(result) -> str:
    return "\n".join(
        item.text for item in result.content if hasattr(item, "text") and item.text
    )


async def _open_session(packs_dir: Path) -> ClientSession:
    server = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "engram_server.server",
            "serve",
            "--packs-dir",
            str(packs_dir),
        ],
        cwd=str(REPO_ROOT),
    )

    stdio = stdio_client(server)
    read_stream, write_stream = await stdio.__aenter__()
    session_ctx = ClientSession(read_stream, write_stream)
    session = await session_ctx.__aenter__()
    await session.initialize()

    session._test_stdio_ctx = stdio  # type: ignore[attr-defined]
    session._test_session_ctx = session_ctx  # type: ignore[attr-defined]
    return session


async def _close_session(session: ClientSession) -> None:
    await session._test_session_ctx.__aexit__(None, None, None)  # type: ignore[attr-defined]
    await session._test_stdio_ctx.__aexit__(None, None, None)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mcp_connectivity_and_basic_tools() -> None:
    session = await _open_session(FIXTURES)
    try:
        ping = _result_text(await session.call_tool("ping"))
        listed = _result_text(await session.call_tool("list_engrams"))
        info = _result_text(
            await session.call_tool("get_engram_info", {"name": "fitness-coach"})
        )
    finally:
        await _close_session(session)

    assert ping == "pong"
    assert "fitness-coach" in listed
    assert "contract-lawyer" in listed
    parsed = json.loads(info)
    assert parsed["name"] == "fitness-coach"
    assert parsed["knowledge_count"] == 5


@pytest.mark.asyncio
async def test_load_engram_returns_base_and_indexes() -> None:
    session = await _open_session(FIXTURES)
    try:
        loaded = _result_text(
            await session.call_tool(
                "load_engram",
                {"name": "fitness-coach", "query": "膝盖疼能做深蹲吗"},
            )
        )
    finally:
        await _close_session(session)

    assert "# 已加载 Engram: fitness-coach" in loaded
    assert "## 用户关注方向\n膝盖疼能做深蹲吗" in loaded
    assert "## 角色" in loaded
    assert "专业健身教练" in loaded
    assert "## 工作流程" in loaded
    assert "## 规则" in loaded
    assert "knowledge/膝关节损伤训练.md" in loaded
    assert "摘要：" in loaded
    assert "uses:" in loaded
    assert "examples/膝盖疼的上班族.md" in loaded


@pytest.mark.asyncio
async def test_read_engram_file_reads_knowledge_file() -> None:
    session = await _open_session(FIXTURES)
    try:
        content = _result_text(
            await session.call_tool(
                "read_engram_file",
                {"name": "fitness-coach", "path": "knowledge/膝关节损伤训练.md"},
            )
        )
    finally:
        await _close_session(session)

    assert "## knowledge/膝关节损伤训练.md" in content
    assert "疼痛不超过3/10" in content


@pytest.mark.asyncio
async def test_read_engram_file_path_traversal_is_blocked() -> None:
    session = await _open_session(FIXTURES)
    try:
        escaped = _result_text(
            await session.call_tool(
                "read_engram_file",
                {"name": "fitness-coach", "path": "../contract-lawyer/meta.json"},
            )
        )
    finally:
        await _close_session(session)

    assert "未找到文件" in escaped


@pytest.mark.asyncio
async def test_missing_engram_and_file_errors() -> None:
    session = await _open_session(FIXTURES)
    try:
        not_exist = _result_text(
            await session.call_tool(
                "load_engram", {"name": "not-exist", "query": "你好"}
            )
        )
        missing_file = _result_text(
            await session.call_tool(
                "read_engram_file",
                {"name": "fitness-coach", "path": "knowledge/不存在.md"},
            )
        )
    finally:
        await _close_session(session)

    assert "未找到 Engram: not-exist" in not_exist
    assert "未找到文件: knowledge/不存在.md" in missing_file


@pytest.mark.asyncio
async def test_multi_engram_switching() -> None:
    session = await _open_session(FIXTURES)
    try:
        fitness = _result_text(
            await session.call_tool(
                "load_engram", {"name": "fitness-coach", "query": "膝盖疼"}
            )
        )
        contract = _result_text(
            await session.call_tool(
                "load_engram", {"name": "contract-lawyer", "query": "合同违约"}
            )
        )
    finally:
        await _close_session(session)

    assert "knowledge/膝关节损伤训练.md" in fitness
    assert "knowledge/合同违约责任.md" in contract
    assert "examples/" not in contract
    assert fitness != contract


@pytest.mark.asyncio
async def test_write_engram_file_and_read_back(tmp_path: Path) -> None:
    """write_engram_file creates a file that can be read back."""
    _setup_tmp_engram(tmp_path, "test-expert")
    session = await _open_session(tmp_path)
    try:
        write_result = _result_text(
            await session.call_tool(
                "write_engram_file",
                {"name": "test-expert", "path": "knowledge/topic.md", "content": "# Topic\nsome content"},
            )
        )
        read_result = _result_text(
            await session.call_tool(
                "read_engram_file",
                {"name": "test-expert", "path": "knowledge/topic.md"},
            )
        )
    finally:
        await _close_session(session)

    assert "已写入" in write_result
    assert "some content" in read_result


@pytest.mark.asyncio
async def test_capture_memory_and_load(tmp_path: Path) -> None:
    """capture_memory stores data that appears in load_engram."""
    _setup_tmp_engram(tmp_path, "test-expert")
    session = await _open_session(tmp_path)
    try:
        cap_result = _result_text(
            await session.call_tool(
                "capture_memory",
                {
                    "name": "test-expert",
                    "content": "用户偏好晨练",
                    "category": "preferences",
                    "summary": "喜欢早上训练",
                    "memory_type": "preference",
                    "tags": ["fitness"],
                },
            )
        )
        loaded = _result_text(
            await session.call_tool(
                "load_engram",
                {"name": "test-expert", "query": "训练偏好"},
            )
        )
    finally:
        await _close_session(session)

    assert "已记录" in cap_result
    assert "喜欢早上训练" in cap_result
    assert "[preference]" in cap_result
    assert "## 动态记忆" in loaded
    assert "喜欢早上训练" in loaded
    assert "<memory>" in loaded


@pytest.mark.asyncio
async def test_consolidate_memory(tmp_path: Path) -> None:
    """consolidate_memory archives raw entries and updates index."""
    _setup_tmp_engram(tmp_path, "test-expert")
    session = await _open_session(tmp_path)
    try:
        # Capture two raw entries
        await session.call_tool("capture_memory", {
            "name": "test-expert", "content": "偏好晨练",
            "category": "preferences", "summary": "喜欢早上训练",
            "memory_type": "preference",
        })
        await session.call_tool("capture_memory", {
            "name": "test-expert", "content": "家有哑铃",
            "category": "preferences", "summary": "居家训练设备",
            "memory_type": "preference",
        })
        # Consolidate
        result = _result_text(await session.call_tool("consolidate_memory", {
            "name": "test-expert",
            "category": "preferences",
            "consolidated_content": "【训练时间】偏好晨练。【设备】家有哑铃。",
            "summary": "训练偏好摘要",
        }))
        # Load and verify index shows consolidated entry
        loaded = _result_text(await session.call_tool(
            "load_engram", {"name": "test-expert", "query": "训练偏好"}
        ))
    finally:
        await _close_session(session)

    assert "已压缩" in result
    assert "preferences-archive.md" in result
    assert "[consolidated]" in loaded
    assert "训练偏好摘要" in loaded


def _setup_tmp_engram(tmp_path: Path, name: str) -> None:
    """Create a minimal engram in tmp_path for MCP tests."""
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(
        json.dumps({"name": name, "description": "test engram"}),
        encoding="utf-8",
    )
    (d / "role.md").write_text("# Test Role\nA test expert.", encoding="utf-8")


def test_build_loader_roots_prefers_project_claude_engram(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project_packs = workspace / ".claude" / "engram"
    project_packs.mkdir(parents=True)
    global_packs = tmp_path / "global-engram"
    global_packs.mkdir()

    monkeypatch.chdir(workspace)
    roots = _build_loader_roots(global_packs)

    assert roots == [project_packs.resolve(), global_packs.resolve()]


def test_build_loader_roots_fallback_to_configured_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    global_packs = tmp_path / "global-engram"
    global_packs.mkdir()

    monkeypatch.chdir(workspace)
    roots = _build_loader_roots(global_packs)

    assert roots == [global_packs.resolve()]
