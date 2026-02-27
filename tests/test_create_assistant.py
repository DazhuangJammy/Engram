from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


REPO_ROOT = Path(__file__).resolve().parents[1]


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
async def test_create_assistant_guided_auto_fill_and_finalize(tmp_path: Path) -> None:
    session = await _open_session(tmp_path)
    try:
        draft_raw = _result_text(
            await session.call_tool(
                "create_engram_assistant",
                {
                    "mode": "guided",
                    "topic": "健身康复教练",
                    "name": "rehab-coach",
                    "style": "你来",
                    "constraints": "你来",
                },
            )
        )
        payload = json.loads(draft_raw)
        draft_json = json.dumps(payload["draft"], ensure_ascii=False)

        finalized = _result_text(
            await session.call_tool(
                "finalize_engram_draft",
                {
                    "draft_json": draft_json,
                    "confirm": True,
                    "nested": True,
                },
            )
        )
    finally:
        await _close_session(session)

    assert payload["requires_confirmation"] is True
    assert "style" in payload["draft"]["auto_filled_fields"]
    assert "constraints" in payload["draft"]["auto_filled_fields"]
    assert "创建完成：rehab-coach" in finalized
    assert "草稿已通过 lint 校验" in finalized

    target = tmp_path / "rehab-coach"
    assert (target / "knowledge" / "_index.md").is_file()
    assert (target / "examples" / "典型场景.md").is_file()
    assert (target / "memory" / "_index.md").is_file()


@pytest.mark.asyncio
async def test_create_assistant_from_conversation_and_cancel(tmp_path: Path) -> None:
    session = await _open_session(tmp_path)
    try:
        draft_raw = _result_text(
            await session.call_tool(
                "create_engram_assistant",
                {
                    "mode": "from_conversation",
                    "name": "ops-coach",
                    "topic": "上线运维顾问",
                    "conversation": (
                        "我们讨论了发布前检查清单和回滚预案。"
                        "还明确了异常时先止血再定位。"
                    ),
                },
            )
        )
        payload = json.loads(draft_raw)
        draft_json = json.dumps(payload, ensure_ascii=False)

        canceled = _result_text(
            await session.call_tool(
                "finalize_engram_draft",
                {
                    "draft_json": draft_json,
                    "confirm": False,
                },
            )
        )
    finally:
        await _close_session(session)

    knowledge_text = payload["draft"]["knowledge"][0]["content"]
    assert "发布前检查清单" in knowledge_text
    assert "已取消创建" in canceled
    assert not (tmp_path / "ops-coach").exists()
