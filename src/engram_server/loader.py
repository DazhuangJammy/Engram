from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_BASE_SECTIONS = {
    "role": "role.md",
    "workflow": "workflow.md",
    "rules": "rules.md",
}

_HOT_INDEX_LIMIT = 50


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

        rules_content = self.load_file(name, "rules.md") or ""
        rules = self._render_section(name, "规则", "rules")
        if rules:
            sections.append(rules)

        # Engram 继承：合并父 Engram 的 knowledge index
        meta = self.get_engram_info(name) or {}
        parent_name = meta.get("extends")
        if parent_name and self._resolve_engram_dir(parent_name):
            parent_knowledge = self.load_file(parent_name, "knowledge/_index.md")
            if parent_knowledge and parent_knowledge.strip():
                sections.append(
                    f"## 继承知识索引（来自 {parent_name}）\n{parent_knowledge.strip()}"
                )

        knowledge_index = self.load_file(name, "knowledge/_index.md")
        if knowledge_index and knowledge_index.strip():
            sections.append(f"## 知识索引\n{knowledge_index.strip()}")

        examples_index = self.load_file(name, "examples/_index.md")
        if examples_index and examples_index.strip():
            sections.append(f"## 案例索引\n{examples_index.strip()}")

        # 动态记忆：过滤已过期条目
        memory_index = self.load_file(name, "memory/_index.md")
        if memory_index and memory_index.strip():
            active_lines = [
                l for l in memory_index.splitlines(keepends=True)
                if not self._is_expired(l)
            ]
            active_content = "".join(active_lines).strip()
            if active_content:
                entry_count = sum(
                    1 for l in active_lines if l.strip().startswith("- `memory/")
                )
                hint = (
                    f"\n💡 当前共 {entry_count} 条记忆，建议对条目较多的 category"
                    " 调用 consolidate_memory 压缩。"
                    if entry_count >= 30 else ""
                )
                sections.append(
                    f"## 动态记忆\n<memory>\n{active_content}\n</memory>{hint}"
                )

        # 全局用户记忆
        global_index_file = self._global_memory_dir() / "_index.md"
        if global_index_file.is_file():
            try:
                global_index = global_index_file.read_text(encoding="utf-8")
            except OSError:
                global_index = ""
            if global_index.strip():
                active_global = [
                    l for l in global_index.splitlines(keepends=True)
                    if not self._is_expired(l)
                ]
                if active_global:
                    sections.append(
                        f"## 全局用户记忆\n<global_memory>\n"
                        f"{''.join(active_global).strip()}\n</global_memory>"
                    )

        # 冷启动引导
        onboarding = self._get_onboarding_prompt(name, rules_content)
        if onboarding:
            sections.append(onboarding)

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
        expires: str | None = None,
        is_global: bool = False,
        throttle_seconds: int = 30,
    ) -> bool:
        """Capture a memory entry and update the memory index.

        Duplicate content within throttle_seconds is silently skipped (returns True).
        When is_global=True, writes to the shared _global/memory/ directory.
        """
        throttle_key = f"{name}:{category}:{content[:120]}"
        now = time.monotonic()
        if throttle_key in self._throttle_cache:
            if now - self._throttle_cache[throttle_key] < throttle_seconds:
                return True
        self._throttle_cache[throttle_key] = now

        if is_global:
            memory_dir = self._global_memory_dir()
        else:
            engram_dir = self._resolve_engram_dir(name)
            if engram_dir is None:
                return False
            memory_dir = engram_dir / "memory"
            memory_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        meta_parts = [f"[{ts}]", f"type:{memory_type}"]
        if expires:
            meta_parts.append(f"expires:{expires}")
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

        # 首次记忆写入后标记 onboarding 完成
        if not is_global:
            onboarded_marker = memory_dir / "_onboarded"
            if not onboarded_marker.exists():
                try:
                    onboarded_marker.touch()
                except OSError:
                    pass

        expires_str = f" expires:{expires}" if expires else ""
        tag_str = f" [{','.join(tags)}]" if tags else ""
        index_line = (
            f"- `memory/{category}.md` [{ts}] [{memory_type}]{expires_str}{tag_str}"
            f" {summary.strip()}\n"
        )

        # 分层 index：追加到 _index_full.md，重建 _index.md（热层）
        full_index = memory_dir / "_index_full.md"
        hot_index = memory_dir / "_index.md"

        # 迁移：若 _index_full.md 不存在但 _index.md 存在，以其为初始内容
        if not full_index.is_file() and hot_index.is_file():
            try:
                full_index.write_text(hot_index.read_text(encoding="utf-8"), encoding="utf-8")
            except OSError:
                pass

        try:
            with full_index.open("a", encoding="utf-8") as f:
                f.write(index_line)
        except OSError:
            return False

        self._rebuild_hot_index(memory_dir)
        return True

    def consolidate_memory(
        self,
        name: str,
        category: str,
        consolidated_content: str,
        summary: str,
    ) -> bool:
        """Replace raw memory entries with a consolidated summary, archiving originals."""
        engram_dir = self._resolve_engram_dir(name)
        if engram_dir is None:
            return False

        memory_dir = engram_dir / "memory"
        category_file = memory_dir / f"{category}.md"
        archive_file = memory_dir / f"{category}-archive.md"
        full_index = memory_dir / "_index_full.md"
        hot_index = memory_dir / "_index.md"

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        # 1. Archive existing raw entries
        if category_file.is_file():
            try:
                existing = category_file.read_text(encoding="utf-8")
                with archive_file.open("a", encoding="utf-8") as f:
                    f.write(f"\n\n# 归档于 {ts}\n{existing}")
            except OSError:
                return False

        # 2. Write consolidated content
        try:
            category_file.write_text(
                f"\n---\n[{ts}] type:consolidated\n{consolidated_content.strip()}\n",
                encoding="utf-8",
            )
        except OSError:
            return False

        # 3. Update _index_full.md（迁移兼容）
        new_line = f"- `memory/{category}.md` [{ts}] [consolidated] {summary.strip()}\n"
        if not full_index.is_file() and hot_index.is_file():
            try:
                full_index.write_text(hot_index.read_text(encoding="utf-8"), encoding="utf-8")
            except OSError:
                pass

        if full_index.is_file():
            try:
                lines = full_index.read_text(encoding="utf-8").splitlines(keepends=True)
            except OSError:
                return False
            filtered = [l for l in lines if f"`memory/{category}.md`" not in l]
            filtered.append(new_line)
            try:
                full_index.write_text("".join(filtered), encoding="utf-8")
            except OSError:
                return False
        else:
            try:
                memory_dir.mkdir(parents=True, exist_ok=True)
                full_index.write_text(new_line, encoding="utf-8")
            except OSError:
                return False

        self._rebuild_hot_index(memory_dir)
        return True

    def delete_memory(self, name: str, category: str, summary: str) -> bool:
        """Delete a specific memory entry by matching its summary in the index.

        Removes the matching line from _index.md and the corresponding entry
        from memory/{category}.md (matched by timestamp).
        """
        engram_dir = self._resolve_engram_dir(name)
        if engram_dir is None:
            return False

        memory_dir = engram_dir / "memory"
        index_file = memory_dir / "_index.md"
        category_file = memory_dir / f"{category}.md"

        if not index_file.is_file():
            return False

        try:
            index_lines = index_file.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError:
            return False

        target_line = None
        target_ts = None
        for line in index_lines:
            if f"`memory/{category}.md`" in line and summary.strip() in line:
                target_line = line
                m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]", line)
                if m:
                    target_ts = m.group(1)
                break

        if target_line is None:
            return False

        new_lines = [l for l in index_lines if l != target_line]
        try:
            index_file.write_text("".join(new_lines), encoding="utf-8")
        except OSError:
            return False

        if target_ts and category_file.is_file():
            try:
                content = category_file.read_text(encoding="utf-8")
                parts = content.split("\n---\n")
                new_parts = [p for p in parts if target_ts not in p]
                category_file.write_text("\n---\n".join(new_parts), encoding="utf-8")
            except OSError:
                pass  # index already updated; best-effort on category file

        return True

    def correct_memory(
        self,
        name: str,
        category: str,
        old_summary: str,
        new_content: str,
        new_summary: str,
        *,
        memory_type: str = "general",
        tags: list[str] | None = None,
    ) -> bool:
        """Replace an existing memory entry with corrected content.

        Finds the entry by old_summary in _index.md, updates the index line
        and replaces the raw content in memory/{category}.md.
        """
        engram_dir = self._resolve_engram_dir(name)
        if engram_dir is None:
            return False

        memory_dir = engram_dir / "memory"
        index_file = memory_dir / "_index.md"
        category_file = memory_dir / f"{category}.md"

        if not index_file.is_file():
            return False

        try:
            index_lines = index_file.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError:
            return False

        target_line = None
        target_ts = None
        for line in index_lines:
            if f"`memory/{category}.md`" in line and old_summary.strip() in line:
                target_line = line
                m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]", line)
                if m:
                    target_ts = m.group(1)
                break

        if target_line is None:
            return False

        ts = target_ts or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        tag_str = f" [{','.join(tags)}]" if tags else ""
        new_index_line = (
            f"- `memory/{category}.md` [{ts}] [{memory_type}]{tag_str} {new_summary.strip()}\n"
        )
        new_index_lines = [
            new_index_line if l == target_line else l for l in index_lines
        ]
        try:
            index_file.write_text("".join(new_index_lines), encoding="utf-8")
        except OSError:
            return False

        if target_ts and category_file.is_file():
            try:
                content = category_file.read_text(encoding="utf-8")
                parts = content.split("\n---\n")
                new_parts = []
                for part in parts:
                    if target_ts in part:
                        meta_parts = [f"[{ts}]", f"type:{memory_type}"]
                        if tags:
                            meta_parts.append(f"tags:{','.join(tags)}")
                        meta_line = " ".join(meta_parts)
                        new_parts.append(f"\n{meta_line}\n{new_content.strip()}\n")
                    else:
                        new_parts.append(part)
                category_file.write_text("\n---\n".join(new_parts), encoding="utf-8")
            except OSError:
                pass  # index already updated; best-effort on category file

        return True

    def add_knowledge(
        self, name: str, filename: str, content: str, summary: str
    ) -> bool:
        """Add a new knowledge file and append an entry to knowledge/_index.md.

        filename may omit the .md extension — it will be added automatically.
        """
        engram_dir = self._resolve_engram_dir(name)
        if engram_dir is None:
            return False

        if not filename.endswith(".md"):
            filename = f"{filename}.md"

        knowledge_path = f"knowledge/{filename}"
        target = self._resolve_file(name, knowledge_path)
        if target is None:
            return False

        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(content, encoding="utf-8")
        except OSError:
            return False

        index_file = engram_dir / "knowledge" / "_index.md"
        index_line = f"- `{knowledge_path}` - {summary.strip()}\n"
        try:
            with index_file.open("a", encoding="utf-8") as f:
                f.write(index_line)
        except OSError:
            return False

        return True

    def count_memory_entries(self, name: str, category: str) -> int:
        """Count raw (non-consolidated) entries in a memory category file."""
        content = self.load_file(name, f"memory/{category}.md")
        if not content:
            return 0
        return content.count("\n---\n")

    def _global_memory_dir(self) -> Path:
        """Return the shared global memory directory, creating it if needed."""
        d = self.packs_dir / "_global" / "memory"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _rebuild_hot_index(self, memory_dir: Path) -> None:
        """Rebuild _index.md (hot layer, last N entries) from _index_full.md."""
        full_index = memory_dir / "_index_full.md"
        hot_index = memory_dir / "_index.md"
        if not full_index.is_file():
            return
        try:
            lines = full_index.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError:
            return
        entry_lines = [l for l in lines if l.strip().startswith("- `memory/")]
        hot_lines = entry_lines[-_HOT_INDEX_LIMIT:]
        try:
            hot_index.write_text("".join(hot_lines), encoding="utf-8")
        except OSError:
            pass

    @staticmethod
    def _is_expired(line: str) -> bool:
        """Return True if the index line has an expires field that has passed."""
        m = re.search(r"expires:(\d{4}-\d{2}-\d{2})", line)
        if not m:
            return False
        try:
            exp_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            return exp_date < datetime.now(timezone.utc).date()
        except ValueError:
            return False

    def _get_onboarding_prompt(self, name: str, rules_content: str) -> str:
        """Return onboarding prompt if this is the user's first session, else empty string."""
        engram_dir = self._resolve_engram_dir(name)
        if engram_dir is None:
            return ""

        memory_dir = engram_dir / "memory"

        # Already onboarded?
        if (memory_dir / "_onboarded").exists():
            return ""

        # Has any category files already?
        if memory_dir.is_dir():
            skip_names = {"_index.md", "_index_full.md", "_onboarded"}
            has_entries = any(
                f.is_file() and f.name not in skip_names
                for f in memory_dir.iterdir()
            )
            if has_entries:
                return ""

        # Parse ## Onboarding section from rules.md
        if not rules_content:
            return ""
        m = re.search(r"##\s+Onboarding\s*\n(.*?)(?=\n##|\Z)", rules_content, re.DOTALL)
        if not m:
            return ""
        onboarding_text = m.group(1).strip()
        if not onboarding_text:
            return ""

        return (
            "## 首次引导\n"
            "> 这是用户首次使用此专家，请在对话中自然地了解以下信息并记录：\n\n"
            f"{onboarding_text}"
        )

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
