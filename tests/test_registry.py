from __future__ import annotations

import json
from pathlib import Path

import pytest

from engram_server import registry
from engram_server.server import main


class _FakeResponse:
    def __init__(self, payload: str):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload.encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args) -> None:
        return None


def test_fetch_registry_success(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps([{"name": "fitness-coach", "source": "https://example.com/a.git"}])
    monkeypatch.setattr(registry, "urlopen", lambda *_args, **_kwargs: _FakeResponse(payload))

    entries = registry.fetch_registry()
    assert len(entries) == 1
    assert entries[0]["name"] == "fitness-coach"


def test_search_registry_fuzzy_match() -> None:
    entries = [
        {
            "name": "fitness-coach",
            "description": "训练计划与营养建议",
            "tags": ["fitness", "增肌"],
        },
        {
            "name": "language-partner",
            "description": "English and Japanese speaking practice",
            "tags": ["language", "conversation"],
        },
    ]

    zh_result = registry.search_registry("营养", entries)
    en_result = registry.search_registry("english", entries)
    tag_result = registry.search_registry("conversation", entries)

    assert [item["name"] for item in zh_result] == ["fitness-coach"]
    assert [item["name"] for item in en_result] == ["language-partner"]
    assert [item["name"] for item in tag_result] == ["language-partner"]


def test_resolve_name_exact_and_missing() -> None:
    entries = [{"name": "fitness-coach", "source": "https://example.com/fitness.git"}]

    assert registry.resolve_name("fitness-coach", entries) == "https://example.com/fitness.git"
    assert registry.resolve_name("unknown", entries) is None


def test_install_subcommand_uses_registry_for_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "engram_server.server._load_registry_entries",
        lambda: [{"name": "demo-pack", "source": "https://example.com/demo.git"}],
    )
    monkeypatch.setattr(
        "engram_server.server.install_engram_from_source",
        lambda source, _packs_dir: {"ok": True, "message": f"source={source}"},
    )

    main(["install", "demo-pack", "--packs-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert "source=https://example.com/demo.git" in out


def test_install_subcommand_keeps_url_branch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "engram_server.server._load_registry_entries",
        lambda: (_ for _ in ()).throw(AssertionError("registry should not be used")),
    )
    monkeypatch.setattr(
        "engram_server.server.install_engram_from_source",
        lambda source, _packs_dir: {"ok": True, "message": f"source={source}"},
    )

    main(["install", "https://example.com/direct.git", "--packs-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert "source=https://example.com/direct.git" in out


def test_search_subcommand_formats_matches(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "engram_server.server._load_registry_entries",
        lambda: [
            {
                "name": "fitness-coach",
                "description": "训练专家",
                "tags": ["fitness", "rehab"],
                "author": "engram-team",
            }
        ],
    )

    main(["search", "fit"])
    out = capsys.readouterr().out
    assert "fitness-coach - 训练专家 [fitness, rehab] (engram-team)" in out
