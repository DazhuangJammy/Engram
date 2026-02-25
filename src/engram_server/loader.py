from __future__ import annotations

import json
import time
from datetime import datetime, timezone
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
        self._throttle_cache: dict[str, float] = {}

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

        memory_index = self.load_file(name, "memory/_index.md")
        if memory_index and memory_index.strip():
            sections.append(
                f"## 动态记忆\n<memory>\n{memory_index.strip()}\n</memory>"
            )

        if not sections:
            return ""

        return "\n\n".join(sections)

    def write_file(
        self, name: str, relative_path: str, content: str, *, append: bool = False
    ) -> bool:
        """Write or append content to a file inside an Engram pack.

        Creates parent directories as needed. Returns True on success.
        """
        engram_dir = self._resolve_engram_dir(name)
        if engram_dir is None:
            return False

        target = (engram_dir / relative_path).resolve()
        try:
            target.relative_to(engram_dir)
        except ValueError:
            return False

        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if append:
                with target.open("a", encoding="utf-8") as f:
                    f.write(content)
            else:
                target.write_text(content, encoding="utf-8")
        except OSError:
            return False
        return True

    def capture_memory(
        self,
        name: str,
        content: str,
        category: str,
        summary: str,
        *,
        memory_type: str = "general",
        tags: list[str] | None = None,
        conversation_id: str | None = None,
        throttle_seconds: int = 30,
    ) -> bool:
        """Capture a memory entry and update the memory index.

        Duplicate content within throttle_seconds is silently skipped (returns True).
        """
        throttle_key = f"{name}:{category}:{content[:120]}"
        now = time.monotonic()
        if throttle_key in self._throttle_cache:
            if now - self._throttle_cache[throttle_key] < throttle_seconds:
                return True  # already captured recently, skip silently
        self._throttle_cache[throttle_key] = now

        engram_dir = self._resolve_engram_dir(name)
        if engram_dir is None:
            return False

        memory_dir = engram_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        meta_parts = [f"[{ts}]", f"type:{memory_type}"]
        if tags:
            meta_parts.append(f"tags:{','.join(tags)}")
        if conversation_id:
            meta_parts.append(f"conv:{conversation_id}")
        meta_line = " ".join(meta_parts)

        entry = f"\n---\n{meta_line}\n{content.strip()}\n"
        category_file = memory_dir / f"{category}.md"
        try:
            with category_file.open("a", encoding="utf-8") as f:
                f.write(entry)
        except OSError:
            return False

        tag_str = f" [{','.join(tags)}]" if tags else ""
        index_line = (
            f"- `memory/{category}.md` [{ts}] [{memory_type}]{tag_str} {summary.strip()}\n"
        )
        index_file = memory_dir / "_index.md"
        try:
            with index_file.open("a", encoding="utf-8") as f:
                f.write(index_line)
        except OSError:
            return False

        return True

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
