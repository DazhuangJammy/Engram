from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_BASE_SECTIONS = {
    "role": "role.md",
    "workflow": "workflow.md",
    "rules": "rules.md",
}


class EngramLoader:
    """Load Engram packs from a directory."""

    def __init__(self, packs_dir: Path):
        self.packs_dir = Path(packs_dir).expanduser()

    def list_engrams(self) -> list[dict[str, Any]]:
        if not self.packs_dir.exists():
            return []

        engrams: list[dict[str, Any]] = []
        for entry in sorted(self.packs_dir.iterdir()):
            if not entry.is_dir():
                continue
            meta = self._read_meta(entry / "meta.json")
            if meta is None:
                continue
            engrams.append(
                {
                    "name": meta.get("name", entry.name),
                    "description": meta.get("description", ""),
                    "tags": meta.get("tags", []),
                    "version": meta.get("version", ""),
                    "author": meta.get("author", ""),
                    "knowledge_count": meta.get("knowledge_count", 0),
                    "examples_count": meta.get("examples_count", 0),
                }
            )
        return engrams

    def get_engram_info(self, name: str) -> dict[str, Any] | None:
        engram_dir = self._resolve_engram_dir(name)
        if engram_dir is None:
            return None
        return self._read_meta(engram_dir / "meta.json")

    def load_file(self, name: str, filepath: str) -> str | None:
        target = self._resolve_file(name, filepath)
        if target is None or not target.is_file():
            return None

        try:
            return target.read_text(encoding="utf-8")
        except OSError:
            return None

    def list_files(self, name: str, subdir: str) -> list[str]:
        target = self._resolve_file(name, subdir)
        if target is None or not target.is_dir():
            return []

        base = Path(subdir)
        names = [
            str((base / path.name).as_posix())
            for path in sorted(target.iterdir(), key=lambda p: p.name)
            if path.is_file() and path.suffix == ".md"
        ]
        return names

    def load_engram_base(self, name: str) -> str | None:
        if self._resolve_engram_dir(name) is None:
            return None

        sections: list[str] = []

        role = self._render_section(name, "角色", "role")
        if role:
            sections.append(role)

        workflow = self._render_section(name, "工作流程", "workflow")
        if workflow:
            sections.append(workflow)

        rules = self._render_section(name, "规则", "rules")
        if rules:
            sections.append(rules)

        knowledge_index = self.load_file(name, "knowledge/_index.md")
        if knowledge_index and knowledge_index.strip():
            sections.append(f"## 知识索引\n{knowledge_index.strip()}")

        examples_index = self.load_file(name, "examples/_index.md")
        if examples_index and examples_index.strip():
            sections.append(f"## 案例索引\n{examples_index.strip()}")

        if not sections:
            return ""

        return "\n\n".join(sections)

    def _render_section(self, name: str, title: str, subdir: str) -> str:
        filename = _BASE_SECTIONS.get(subdir, f"{subdir}.md")
        content = self.load_file(name, filename)
        if not content or not content.strip():
            return ""
        return f"## {title}\n{content.strip()}"

    def _resolve_engram_dir(self, name: str) -> Path | None:
        packs_root = self.packs_dir.resolve()
        engram_dir = (packs_root / name).resolve()

        try:
            engram_dir.relative_to(packs_root)
        except ValueError:
            return None

        if not engram_dir.is_dir():
            return None
        return engram_dir

    def _resolve_file(self, name: str, relative_path: str) -> Path | None:
        engram_dir = self._resolve_engram_dir(name)
        if engram_dir is None:
            return None

        target = (engram_dir / relative_path).resolve()
        try:
            target.relative_to(engram_dir)
        except ValueError:
            return None
        return target

    @staticmethod
    def _read_meta(meta_path: Path) -> dict[str, Any] | None:
        if not meta_path.is_file():
            return None
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
