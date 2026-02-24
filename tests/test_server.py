from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


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
