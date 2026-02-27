from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP

from engram_server.creator import (
    build_engram_draft,
    draft_response_payload,
    materialize_draft,
    parse_draft_payload,
)
from engram_server.lint import lint_engram
from engram_server.loader import EngramLoader
from engram_server.registry import fetch_registry, resolve_name, search_registry

DEFAULT_PACKS_DIR = Path("~/.engram").expanduser()
_PROJECT_BOOTSTRAP_COMPLETE_NAME = "starter-complete"
_PROJECT_BOOTSTRAP_TEMPLATE_NAME = "starter-template"


def _format_engrams(engrams: list[dict]) -> str:
    if not engrams:
        return "暂无可用 Engram。"

    lines = []
    for item in engrams:
        name = item.get("name", "")
        description = item.get("description", "")
        knowledge_count = item.get("knowledge_count", 0)
        examples_count = item.get("examples_count", 0)
        lines.append(
            f"- {name}: {description} (knowledge={knowledge_count}, examples={examples_count})"
        )
    return "\n".join(lines)


def _engram_exists(loader: EngramLoader, name: str) -> bool:
    return loader.get_engram_info(name) is not None


def _derive_target_name(source: str) -> str:
    parsed = urlparse(source)
    tail = Path(parsed.path).name if parsed.path else source.rstrip("/").split("/")[-1]
    return tail[:-4] if tail.endswith(".git") else tail


def _is_valid_engram_name(name: str) -> bool:
    if not name or name in {".", ".."}:
        return False
    if "/" in name or "\\" in name:
        return False
    return name.strip() == name


def _find_template_dir() -> Path | None:
    candidates = [
        Path(__file__).resolve().parent / "templates",
        Path(__file__).resolve().parents[2] / "examples" / "template",
    ]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / "meta.json").is_file():
            return candidate
    return None


def _is_url_source(source: str) -> bool:
    return "://" in source or source.endswith(".git")


def _load_registry_entries() -> list[dict]:
    remote = fetch_registry()
    if remote:
        return remote

    local_registry = Path(__file__).resolve().parents[2] / "registry.json"
    if local_registry.is_file():
        try:
            raw = json.loads(local_registry.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return [item for item in raw if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return []
    return []


def _render_search_item(entry: dict) -> str:
    name = str(entry.get("name", "")).strip()
    description = str(entry.get("description", "")).strip()
    author = str(entry.get("author", "")).strip()
    tags = entry.get("tags", [])
    if not isinstance(tags, list):
        tags = [str(tags)]
    tags_str = ", ".join(str(tag) for tag in tags if str(tag).strip())
    return f"{name} - {description} [{tags_str}] ({author})"


def _build_loader_roots(
    packs_dir: Path | str,
    *,
    cwd: Path | None = None,
) -> list[Path]:
    """Build search roots for Engram loading.

    Priority:
    1) project-level .claude/engram (if exists)
    2) configured --packs-dir (global/default)
    """
    configured = Path(packs_dir).expanduser().resolve()
    project_root = (cwd or Path.cwd()).resolve()
    project_engram = (project_root / ".claude" / "engram").resolve()

    roots: list[Path] = []
    if project_engram.is_dir():
        roots.append(project_engram)
    roots.append(configured)

    deduped: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        deduped.append(root)
    return deduped


def _project_engram_dir(*, cwd: Path | None = None) -> Path:
    project_root = (cwd or Path.cwd()).resolve()
    return (project_root / ".claude" / "engram").resolve()


def _has_engram_pack(packs_dir: Path) -> bool:
    if not packs_dir.is_dir():
        return False
    return any(
        entry.is_dir() and (entry / "meta.json").is_file()
        for entry in packs_dir.iterdir()
    )


def _next_available_pack_name(packs_dir: Path, base_name: str) -> str:
    if not (packs_dir / base_name).exists():
        return base_name

    idx = 2
    while (packs_dir / f"{base_name}-{idx}").exists():
        idx += 1
    return f"{base_name}-{idx}"


def _materialize_complete_starter_pack(target_dir: Path, name: str) -> None:
    """Fill a starter pack with complete, runnable sample content."""
    meta = {
        "name": name,
        "author": "engram-team",
        "version": "1.0.0",
        "description": "完整 Engram 示例：可直接加载并参考改造。",
        "tags": ["starter", "complete", "example"],
        "knowledge_count": 2,
        "examples_count": 1,
    }
    (target_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    (target_dir / "role.md").write_text(
        "# 角色定位\n"
        "你是一个「项目教练」型专家，擅长把模糊目标拆成可执行步骤。\n\n"
        "## 沟通风格\n"
        "- 先给结论，再给步骤，再给风险提示。\n"
        "- 每次回答都尽量给出可直接执行的下一步。\n",
        encoding="utf-8",
    )

    (target_dir / "workflow.md").write_text(
        "# 工作流程\n"
        "1. 明确目标、边界和成功标准\n"
        "2. 先交付最小可执行版本（MVP）\n"
        "3. 根据反馈迭代，保持节奏可持续\n"
        "4. 固化有效经验，沉淀为知识\n"
        "5. 遇到工具化节点时，按步骤主动调用对应 MCP 工具或 Skills\n",
        encoding="utf-8",
    )

    (target_dir / "rules.md").write_text(
        "# 运作规则\n"
        "- 信息不完整时先补关键上下文，再给建议\n"
        "- 方案必须包含执行条件与回退条件\n"
        "- 遇到高风险事项时明确提醒边界\n\n"
        "## Onboarding\n"
        "首次对话请自然收集并记录：\n"
        "- 用户当前目标和期望时间\n"
        "- 可投入的时间/资源\n"
        "- 当前最大的阻碍是什么\n",
        encoding="utf-8",
    )

    (target_dir / "knowledge" / "_index.md").write_text(
        "## 知识索引\n\n"
        "- `knowledge/目标拆解法.md` - 如何把模糊目标拆成可执行任务。\n"
        "- `knowledge/周迭代复盘法.md` - 每周复盘与滚动调整的方法。\n",
        encoding="utf-8",
    )
    (target_dir / "knowledge" / "目标拆解法.md").write_text(
        "# 目标拆解法\n\n"
        "1. 定义结果：一句话说清最终状态。\n"
        "2. 定义约束：时间、预算、能力边界。\n"
        "3. 拆里程碑：按周划分阶段性结果。\n"
        "4. 拆行动：每个里程碑拆成 3-5 个动作。\n",
        encoding="utf-8",
    )
    (target_dir / "knowledge" / "周迭代复盘法.md").write_text(
        "# 周迭代复盘法\n\n"
        "- 本周进展：完成了什么、没完成什么。\n"
        "- 关键阻碍：为什么卡住。\n"
        "- 下周调整：保留、删除、替换哪些动作。\n"
        "- 风险控制：触发回退条件时如何降级执行。\n",
        encoding="utf-8",
    )

    (target_dir / "examples" / "_index.md").write_text(
        "## 案例索引\n\n"
        "- `examples/完整案例.md` - 从模糊目标到四周执行计划的完整示例。\n"
        "  uses: knowledge/目标拆解法.md, knowledge/周迭代复盘法.md\n",
        encoding="utf-8",
    )
    (target_dir / "examples" / "完整案例.md").write_text(
        "---\n"
        "id: complete_starter_case\n"
        "title: 四周执行计划示例\n"
        "uses:\n"
        "  - knowledge/目标拆解法.md\n"
        "  - knowledge/周迭代复盘法.md\n"
        "tags:\n"
        "  - starter\n"
        "  - complete\n"
        "updated_at: 2026-02-27\n"
        "---\n\n"
        "# 四周执行计划示例\n\n"
        "## 背景\n"
        "用户目标不清晰，执行三天就中断。\n\n"
        "## 评估过程\n"
        "先明确目标与约束，再识别中断触发点。\n\n"
        "## 最终方案\n"
        "拆成四周里程碑，每周只保留 3 个关键动作。\n\n"
        "## 结果复盘\n"
        "第 2 周开始稳定执行，第 4 周可自主滚动规划。\n",
        encoding="utf-8",
    )


def _ensure_project_engram_workspace(*, cwd: Path | None = None) -> Path:
    """Create .claude/engram in the current project and bootstrap two starter packs."""
    project_engram = _project_engram_dir(cwd=cwd)
    project_engram.mkdir(parents=True, exist_ok=True)

    if _has_engram_pack(project_engram):
        return project_engram

    template_name = _next_available_pack_name(
        project_engram, _PROJECT_BOOTSTRAP_TEMPLATE_NAME
    )
    init_engram_pack(template_name, project_engram)

    complete_name = _next_available_pack_name(
        project_engram, _PROJECT_BOOTSTRAP_COMPLETE_NAME
    )
    result = init_engram_pack(complete_name, project_engram)
    if result.get("ok"):
        _materialize_complete_starter_pack(project_engram / complete_name, complete_name)
    return project_engram


def install_engram_from_source(source: str, packs_dir: Path) -> dict[str, str | bool]:
    packs_dir = packs_dir.expanduser()
    packs_dir.mkdir(parents=True, exist_ok=True)

    target_name = _derive_target_name(source)
    target_dir = packs_dir / target_name
    if target_dir.exists():
        return {
            "ok": False,
            "message": f"安装失败：目标目录已存在 {target_dir.name}",
        }

    try:
        subprocess.run(
            ["git", "clone", source, str(target_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        return {
            "ok": False,
            "message": f"安装失败：git clone 出错。{stderr}",
        }

    meta_path = target_dir / "meta.json"
    if not meta_path.is_file():
        shutil.rmtree(target_dir, ignore_errors=True)
        return {
            "ok": False,
            "message": "安装失败：仓库根目录缺少 meta.json，已回滚。",
        }

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        shutil.rmtree(target_dir, ignore_errors=True)
        return {
            "ok": False,
            "message": "安装失败：meta.json 不是合法 JSON，已回滚。",
        }

    name = meta.get("name", target_dir.name)
    description = meta.get("description", "")
    return {
        "ok": True,
        "message": f"安装成功：{name} - {description}",
    }


def init_engram_pack(
    name: str,
    packs_dir: Path,
    *,
    nested: bool = False,
) -> dict[str, str | bool]:
    if not _is_valid_engram_name(name):
        return {"ok": False, "message": f"初始化失败：非法名称 {name}"}

    packs_dir = packs_dir.expanduser()
    packs_dir.mkdir(parents=True, exist_ok=True)

    target_dir = packs_dir / name
    if target_dir.exists():
        return {"ok": False, "message": f"初始化失败：目标目录已存在 {name}"}

    template_dir = _find_template_dir()
    if template_dir is None:
        return {"ok": False, "message": "初始化失败：未找到模板目录。"}

    shutil.copytree(template_dir, target_dir)

    if nested:
        _apply_nested_template(target_dir)

    meta_path = target_dir / "meta.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        shutil.rmtree(target_dir, ignore_errors=True)
        return {"ok": False, "message": "初始化失败：模板 meta.json 无法解析。"}

    meta["name"] = name
    if not meta.get("description"):
        meta["description"] = f"{name} 专家记忆包"

    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {"ok": True, "message": f"初始化成功：{target_dir}"}


def _apply_nested_template(target_dir: Path) -> None:
    knowledge_dir = target_dir / "knowledge"
    grouped_dir = knowledge_dir / "分组示例"
    grouped_dir.mkdir(parents=True, exist_ok=True)

    top_index = knowledge_dir / "_index.md"
    top_index.write_text(
        "## 知识索引\n\n"
        "### 基础主题\n"
        "- `knowledge/主题A.md` - 主题A基础知识。\n"
        "- `knowledge/主题B.md` - 主题B基础知识。\n\n"
        "### 分组目录\n"
        "- `knowledge/分组示例/_index.md` - 分组索引入口。\n"
        "  → 详见 knowledge/分组示例/_index.md\n",
        encoding="utf-8",
    )

    nested_index = grouped_dir / "_index.md"
    nested_index.write_text(
        "## 分组示例索引\n\n"
        "- `knowledge/分组示例/示例知识.md` - 分组内知识样例。\n",
        encoding="utf-8",
    )

    nested_file = grouped_dir / "示例知识.md"
    if not nested_file.exists():
        nested_file.write_text(
            "# 示例知识\n\n"
            "在这里沉淀该分组下的系统性知识。",
            encoding="utf-8",
        )


def _build_engram_system_prompt(engrams: list[dict]) -> str:
    """Build the dynamic system prompt based on installed Engrams."""
    if not engrams:
        return (
            "# Engram 记忆印记\n\n"
            "暂无可用记忆印记。请使用 install_engram 工具安装专家记忆包。"
        )

    engram_entries = []
    for e in engrams:
        name = e.get("name", "")
        desc = e.get("description", "")
        engram_entries.append(
            f"  <engram>\n"
            f"    <name>{name}</name>\n"
            f"    <description>{desc}</description>\n"
            f"  </engram>"
        )
    engram_xml = "\n".join(engram_entries)

    return (
        "# Engram 记忆印记\n\n"
        "你有一个专家记忆系统可用。你可以加载专家的记忆印记——加载后，你将获得该专家的人格、\n"
        "认知方式和专业知识，以该专家的身份思考和回答问题。\n"
        "记忆印记不会覆盖你的基础能力，只在相关场景下激活。\n\n"
        "## 可用记忆印记\n\n"
        "<engrams>\n"
        f"{engram_xml}\n"
        "</engrams>\n\n"
        "## 使用规则\n\n"
        "1. 对话开始时，调用 list_engrams() 查看可用专家\n"
        "2. 当用户问题匹配某个记忆印记，或用户用 @name 指定时，\n"
        "   调用 load_engram(name, query) 加载角色/工作流程/规则 + 索引\n"
        "3. 根据返回的知识索引（含摘要）和案例索引（含 uses 关联），\n"
        "   判断需要深入哪些主题\n"
        "4. 需要细节时，调用 read_engram_file(name, path) 读取完整知识或案例\n"
        "5. 加载后以该专家的人格回答：保持其沟通风格、判断倾向和价值观\n"
        "6. 对话中发现用户的重要偏好、个人情况或关键决定时，\n"
        "   调用 capture_memory(name, content, category, summary,\n"
        "   memory_type, tags, conversation_id, expires, is_global) 记录下来\n"
        "   memory_type 可选：preference / fact / decision / history / general\n"
        "                     inferred（LLM推断）/ stated（用户明确表达）\n"
        "   expires 可选：ISO日期字符串，如 '2026-06-01'，到期后自动归档到 {category}-expired.md 并隐藏\n"
        "   is_global=True：写入跨专家共享的全局记忆（如用户年龄、城市等基础信息）\n"
        "   tags 可选：用于分类过滤，如 [\"fitness\", \"injury\"]\n"
        "7. 下次加载同一专家时，动态记忆和全局记忆会自动带入，无需用户重复说明\n"
        "8. 当某个 category 的记忆条目超过 30 条时，先用 read_engram_file 读取原始内容，\n"
        "   再调用 consolidate_memory(name, category, consolidated_content, summary)\n"
        "   将多条原始记录压缩为一条密集摘要，原始条目自动归档\n"
        "9. 若加载后看到「首次引导」区块，请在对话中自然地收集所列信息并 capture_memory\n"
        "10. 若 Engram 有「继承知识索引」区块，其知识来自父 Engram，可按需 read_engram_file 读取\n"
    )


def create_mcp_app(loader: EngramLoader, packs_dir: Path) -> FastMCP:
    app = FastMCP(name="engram-server")

    @app.prompt(
        name="engram-system-prompt",
        description="Engram 专家记忆系统提示词。将此注入 system prompt 以启用自动专家加载。",
    )
    def engram_system_prompt() -> str:
        return _build_engram_system_prompt(loader.list_engrams())

    @app.tool()
    def ping() -> str:
        """Connectivity check tool."""
        return "pong"

    @app.tool()
    def list_engrams() -> str:
        """List all available Engram packs.

Call this at the start of every conversation to discover available experts.
When a user's question matches an expert description, call
load_engram(name, query). After that, inspect the knowledge index and
call read_engram_file(name, path) to fetch specific knowledge or case files."""
        return _format_engrams(loader.list_engrams())

    @app.tool()
    def get_engram_info(name: str) -> str:
        """Get one Engram's full meta.json content."""
        info = loader.get_engram_info(name)
        if info is None:
            return f"未找到 Engram: {name}"
        return json.dumps(info, ensure_ascii=False, indent=2)

    @app.tool()
    def load_engram(name: str, query: str) -> str:
        """Load one Engram's base memory and indices.

Returns full role/workflow/rules layers and knowledge/examples indexes.
Use query as a focus hint, then call read_engram_file(name, path) to fetch
specific knowledge or case files selected from the indexes."""
        if not _engram_exists(loader, name):
            return f"未找到 Engram: {name}"

        base = loader.load_engram_base(name)
        if base is None:
            return f"未找到 Engram: {name}"
        if not base.strip():
            return f"Engram {name} 没有可用上下文。"

        return (
            f"# 已加载 Engram: {name}\n\n"
            f"## 用户关注方向\n{query}\n\n"
            f"{base}\n\n"
            "## 下一步\n"
            "请查看知识索引中的摘要，按需调用 read_engram_file(name, path) 读取完整知识或案例。"
        )

    @app.tool()
    def read_engram_file(name: str, path: str) -> str:
        """Read one markdown file from an Engram pack.

Use this after load_engram to read selected files like
knowledge/*.md or examples/*.md. Path traversal outside the Engram directory
is blocked."""
        if not _engram_exists(loader, name):
            return f"未找到 Engram: {name}"

        content = loader.load_file(name, path)
        if content is None:
            return f"未找到文件: {path}"
        if not content.strip():
            return f"文件为空: {path}"

        return f"## {path}\n{content.strip()}"

    @app.tool()
    def install_engram(source: str) -> str:
        """Install an Engram pack from git URL or registry name."""
        if _is_url_source(source):
            install_source = source
        else:
            entries = _load_registry_entries()
            install_source = resolve_name(source, entries)
            if install_source is None:
                return f"安装失败：未在 registry 中找到 {source}"

        result = install_engram_from_source(source=install_source, packs_dir=packs_dir)
        return str(result["message"])

    @app.tool()
    def init_engram(name: str, nested: bool = False) -> str:
        """Initialize a new Engram from template.

If nested=True, generates a template with grouped knowledge indexes."""
        result = init_engram_pack(name, packs_dir, nested=nested)
        return str(result["message"])

    @app.tool()
    def lint_engrams(name: str | None = None) -> str:
        """Run consistency checks for one or all Engrams.

Returns per-Engram error/warning counts and detailed issues."""
        if name:
            targets = [name]
        else:
            targets = [item["name"] for item in loader.list_engrams()]

        if not targets:
            return "暂无可校验 Engram。"

        lines: list[str] = []
        total_errors = 0
        total_warnings = 0

        for target in targets:
            engram_dir = loader._resolve_engram_dir(target)
            if engram_dir is None:
                lines.append(f"{target}: 1 errors, 0 warnings")
                lines.append("  [error] .: 未找到 Engram")
                total_errors += 1
                continue

            messages = lint_engram(engram_dir)
            error_count = sum(1 for m in messages if m.level == "error")
            warning_count = sum(1 for m in messages if m.level == "warning")
            total_errors += error_count
            total_warnings += warning_count

            lines.append(f"{target}: {error_count} errors, {warning_count} warnings")
            for msg in messages:
                lines.append(f"  [{msg.level}] {msg.file_path}: {msg.message}")

        lines.append(
            f"总计: {len(targets)} Engram, {total_errors} errors, {total_warnings} warnings"
        )
        return "\n".join(lines)

    @app.tool()
    def search_engrams(query: str) -> str:
        """Search Engram registry entries by name/description/tags."""
        entries = _load_registry_entries()
        matched = search_registry(query, entries)
        if not matched:
            return "未找到匹配的 Engram"
        return "\n".join(_render_search_item(item) for item in matched)

    @app.tool()
    def stats_engrams(format: str = "plain") -> str:
        """Get Engram statistics in plain/json/csv format."""
        from engram_server.stats import gather_stats, render_csv, render_json, render_plain

        report = gather_stats(loader)
        normalized = format.strip().lower()
        if normalized in {"plain", ""}:
            return render_plain(report)
        if normalized == "json":
            return render_json(report)
        if normalized == "csv":
            return render_csv(report)
        return "不支持的 format。可选：plain/json/csv"

    @app.tool()
    def create_engram_assistant(
        mode: str,
        name: str | None = None,
        topic: str | None = None,
        audience: str | None = None,
        style: str | None = None,
        constraints: str | None = None,
        language: str = "zh-CN",
        conversation: str | None = None,
    ) -> str:
        """Generate an Engram draft from conversation or guided inputs.

mode:
  - "from_conversation": summarize current dialog into a draft
  - "guided": build from user intent fields (auto-fill when missing)"""
        try:
            draft = build_engram_draft(
                mode=mode,
                name=name,
                topic=topic,
                audience=audience,
                style=style,
                constraints=constraints,
                language=language,
                conversation=conversation,
            )
        except ValueError as exc:
            return f"草稿生成失败：{exc}"

        payload = draft_response_payload(draft)
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @app.tool()
    def finalize_engram_draft(
        draft_json: str,
        name: str | None = None,
        nested: bool = True,
        confirm: bool = True,
    ) -> str:
        """Create an Engram pack from a confirmed draft.

Set confirm=False to cancel (no files written)."""
        if not confirm:
            return "已取消创建：未确认落盘。"

        try:
            draft = parse_draft_payload(draft_json)
        except (ValueError, json.JSONDecodeError):
            return "落盘失败：draft_json 不是合法草稿 JSON。"

        draft_name = str(draft.get("meta", {}).get("name", "")).strip()
        target_name = (name or draft_name).strip()
        if not _is_valid_engram_name(target_name):
            return f"落盘失败：非法名称 {target_name}"

        result = init_engram_pack(target_name, packs_dir, nested=nested)
        if not result.get("ok"):
            return str(result.get("message", "落盘失败"))

        engram_dir = loader._resolve_engram_dir(target_name)
        if engram_dir is None:
            return "落盘失败：创建目录后无法定位 Engram。"

        draft.setdefault("meta", {})
        draft["meta"]["name"] = target_name
        draft["meta"].setdefault("description", f"{target_name} 自动生成专家包")
        draft["meta"].setdefault("author", "auto-generated")
        draft["meta"].setdefault("version", "1.0.0")
        draft["meta"].setdefault("tags", [])
        draft["meta"].setdefault("knowledge_count", len(draft.get("knowledge", [])))
        draft["meta"].setdefault("examples_count", len(draft.get("examples", [])))

        try:
            materialize_draft(engram_dir, draft)
        except Exception as exc:  # noqa: BLE001
            shutil.rmtree(engram_dir, ignore_errors=True)
            return f"落盘失败：写入草稿时发生错误：{exc}"

        messages = lint_engram(engram_dir)
        error_count = sum(1 for m in messages if m.level == "error")
        warning_count = sum(1 for m in messages if m.level == "warning")

        lines = [
            f"创建完成：{target_name}",
            f"校验结果：{error_count} errors, {warning_count} warnings",
        ]
        for msg in messages:
            lines.append(f"- [{msg.level}] {msg.file_path}: {msg.message}")

        if error_count > 0:
            lines.append("⚠️ 存在 error，请修复后再投入使用。")
        elif warning_count > 0:
            lines.append("⚠️ 存在 warning，可继续使用，建议后续优化。")
        else:
            lines.append("✅ 草稿已通过 lint 校验。")
        return "\n".join(lines)

    @app.tool()
    def write_engram_file(
        name: str, path: str, content: str, mode: str = "overwrite"
    ) -> str:
        """Write or append content to a file inside an Engram pack.

Use this to create or update role.md, workflow.md, rules.md,
knowledge/*.md, examples/*.md, or any other file.
Set mode to "append" to add content to an existing file.
Path traversal outside the Engram directory is blocked."""
        if not _engram_exists(loader, name):
            return f"未找到 Engram: {name}"

        append = mode == "append"
        ok = loader.write_file(name, path, content, append=append)
        if not ok:
            return f"写入失败: {path}"
        action = "追加" if append else "写入"
        return f"已{action}: {path}"

    @app.tool()
    def capture_memory(
        name: str,
        content: str,
        category: str,
        summary: str,
        memory_type: str = "general",
        tags: list[str] | None = None,
        conversation_id: str | None = None,
        expires: str | None = None,
        is_global: bool = False,
    ) -> str:
        """Capture a memory entry during conversation.

Call this when you identify information worth remembering about the user,
such as preferences, personal context, past decisions, or feedback.
The memory is stored in memory/{category}.md and indexed automatically.
It will be loaded in future conversations with this Engram.
Duplicate content captured within 30 seconds is silently skipped.

Set is_global=True to store in the shared _global/memory/ directory,
making the memory available across ALL Engrams (e.g. user age, location).

Args:
    name: Engram pack name (used for throttle key even when is_global=True)
    content: The memory content to store
    category: File category (e.g. "user-profile", "preferences", "history")
    summary: One-line summary for the memory index
    memory_type: Semantic type — "preference" | "fact" | "decision" | "history"
                 | "general" | "inferred" (LLM-deduced) | "stated" (user explicitly said)
    tags: Optional tags for filtering (e.g. ["fitness", "injury"])
    conversation_id: Optional conversation scope identifier
    expires: Optional expiry date ISO string (e.g. "2026-06-01"). Expired entries
             are moved to memory/{category}-expired.md and hidden from future loads.
    is_global: If True, write to shared _global/memory/ instead of this Engram"""
        if not is_global and not _engram_exists(loader, name):
            return f"未找到 Engram: {name}"

        ok = loader.capture_memory(
            name, content, category, summary,
            memory_type=memory_type,
            tags=tags,
            conversation_id=conversation_id,
            expires=expires,
            is_global=is_global,
        )
        if not ok:
            return f"记忆捕获失败: {category}"
        scope = "[全局] " if is_global else ""
        type_label = f"[{memory_type}] " if memory_type != "general" else ""
        expires_label = f" (expires:{expires})" if expires else ""
        return f"已记录: {scope}{type_label}[{category}] {summary}{expires_label}"

    @app.tool()
    def consolidate_memory(
        name: str,
        category: str,
        consolidated_content: str,
        summary: str,
    ) -> str:
        """Consolidate raw memory entries into a dense summary, archiving originals.

Call this when a memory category has accumulated many entries (30+).
Workflow:
  1. Call read_engram_file(name, "memory/{category}.md") to read all raw entries
  2. Write a dense, deduplicated summary as consolidated_content
  3. Call this tool — originals are archived to memory/{category}-archive.md

The _index.md is updated to a single consolidated entry for this category.

Args:
    name: Engram pack name
    category: Memory category to consolidate (e.g. "preferences", "user-profile")
    consolidated_content: Dense summary replacing all raw entries
    summary: One-line summary for the memory index"""
        if not _engram_exists(loader, name):
            return f"未找到 Engram: {name}"

        ok = loader.consolidate_memory(name, category, consolidated_content, summary)
        if not ok:
            return f"记忆压缩失败: {category}"
        return f"已压缩: [{category}] 原始条目已归档至 memory/{category}-archive.md"

    @app.tool()
    def delete_memory(name: str, category: str, summary: str) -> str:
        """Delete a specific memory entry by its summary.

Use this when the user wants to remove an incorrect or outdated memory.
First read memory/_index.md to find the exact summary text, then call this tool.
The entry is removed from both the index and the category file."""
        if not _engram_exists(loader, name):
            return f"未找到 Engram: {name}"

        ok = loader.delete_memory(name, category, summary)
        if not ok:
            return f"未找到匹配的记忆条目: [{category}] {summary}"
        return f"已删除: [{category}] {summary}"

    @app.tool()
    def correct_memory(
        name: str,
        category: str,
        old_summary: str,
        new_content: str,
        new_summary: str,
        memory_type: str = "general",
        tags: list[str] | None = None,
    ) -> str:
        """Correct an existing memory entry with updated content.

Use this when the user says a captured memory is wrong or outdated.
First read memory/_index.md to find the exact old_summary, then call this
with the corrected content and a new summary.

Args:
    name: Engram pack name
    category: Memory category (e.g. "user-profile", "preferences")
    old_summary: Exact summary text from the index to identify the entry
    new_content: The corrected memory content
    new_summary: Updated one-line summary for the index
    memory_type: Semantic type — "preference" | "fact" | "decision" | "history"
                 | "general" | "inferred" (LLM-deduced) | "stated" (user explicitly said)
    tags: Optional updated tags"""
        if not _engram_exists(loader, name):
            return f"未找到 Engram: {name}"

        ok = loader.correct_memory(
            name, category, old_summary, new_content, new_summary,
            memory_type=memory_type,
            tags=tags,
        )
        if not ok:
            return f"未找到匹配的记忆条目: [{category}] {old_summary}"
        type_label = f"[{memory_type}] " if memory_type != "general" else ""
        return f"已修正: {type_label}[{category}] {new_summary}"

    @app.tool()
    def add_knowledge(
        name: str, filename: str, content: str, summary: str
    ) -> str:
        """Add a new knowledge file to an Engram and update the knowledge index.

Use this when the user wants to expand an Engram's knowledge base during conversation.
The file is written to knowledge/{filename}.md and the index is updated automatically.

Args:
    name: Engram pack name
    filename: Short descriptive filename (with or without .md extension)
    content: Full markdown content for the knowledge file
    summary: One-line description for the knowledge index"""
        if not _engram_exists(loader, name):
            return f"未找到 Engram: {name}"

        ok = loader.add_knowledge(name, filename, content, summary)
        if not ok:
            return f"写入失败: knowledge/{filename}"
        fn = filename if filename.endswith(".md") else f"{filename}.md"
        return f"已添加知识: knowledge/{fn} — {summary}"

    return app


def run_server(packs_dir: Path) -> None:
    packs_dir = packs_dir.expanduser()
    packs_dir.mkdir(parents=True, exist_ok=True)
    project_packs = _ensure_project_engram_workspace()

    loader_roots = _build_loader_roots(packs_dir)
    loader = EngramLoader(
        packs_dir=loader_roots,
        default_packs_dir=packs_dir,
    )
    app = create_mcp_app(loader=loader, packs_dir=project_packs)
    app.run(transport="stdio")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Engram MCP Server")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start MCP stdio server")
    serve_parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR))

    list_parser = subparsers.add_parser("list", help="List installed Engrams")
    list_parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR))

    install_parser = subparsers.add_parser(
        "install",
        help="Install Engram from git URL or registry name",
    )
    install_parser.add_argument("source")
    install_parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR))

    init_parser = subparsers.add_parser("init", help="Create a new Engram from template")
    init_parser.add_argument("name")
    init_parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR))
    init_parser.add_argument(
        "--nested",
        action="store_true",
        help="Create a template with nested knowledge index directories",
    )

    stats_parser = subparsers.add_parser("stats", help="Show Engram statistics")
    stats_parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR))
    stats_group = stats_parser.add_mutually_exclusive_group()
    stats_group.add_argument("--json", action="store_true", help="JSON output")
    stats_group.add_argument("--csv", action="store_true", help="CSV output")
    stats_group.add_argument("--tui", action="store_true", help="Rich TUI output")

    lint_parser = subparsers.add_parser("lint", help="Validate Engram data consistency")
    lint_parser.add_argument("name", nargs="?")
    lint_parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR))

    search_parser = subparsers.add_parser("search", help="Search Engrams from registry")
    search_parser.add_argument("query")
    search_parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR))

    return parser


def main(argv: list[str] | None = None) -> None:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if not args_list or args_list[0].startswith("-"):
        args_list = ["serve", *args_list]

    parser = build_parser()
    args = parser.parse_args(args_list)

    if args.command == "serve":
        run_server(packs_dir=Path(args.packs_dir))
        return

    if args.command == "list":
        packs_dir = Path(args.packs_dir)
        loader = EngramLoader(
            packs_dir=_build_loader_roots(packs_dir),
            default_packs_dir=packs_dir,
        )
        print(_format_engrams(loader.list_engrams()))
        return

    if args.command == "install":
        source = args.source
        if _is_url_source(source):
            install_source = source
        else:
            entries = _load_registry_entries()
            install_source = resolve_name(source, entries)
            if install_source is None:
                print(f"安装失败：未在 registry 中找到 {source}")
                raise SystemExit(1)

        result = install_engram_from_source(install_source, Path(args.packs_dir))
        print(result["message"])
        if not result["ok"]:
            raise SystemExit(1)
        return

    if args.command == "init":
        result = init_engram_pack(
            args.name,
            Path(args.packs_dir),
            nested=args.nested,
        )
        print(result["message"])
        if not result["ok"]:
            raise SystemExit(1)
        return

    if args.command == "stats":
        from engram_server.stats import (
            gather_stats,
            render_csv,
            render_json,
            render_plain,
            render_tui,
        )

        packs_dir = Path(args.packs_dir)
        loader = EngramLoader(
            packs_dir=_build_loader_roots(packs_dir),
            default_packs_dir=packs_dir,
        )
        report = gather_stats(loader)
        if args.tui:
            render_tui(report)
        elif args.json:
            print(render_json(report))
        elif args.csv:
            print(render_csv(report), end="")
        else:
            print(render_plain(report))
        return

    if args.command == "lint":
        packs_dir = Path(args.packs_dir)
        loader = EngramLoader(
            packs_dir=_build_loader_roots(packs_dir),
            default_packs_dir=packs_dir,
        )

        if args.name:
            targets = [args.name]
        else:
            targets = [item["name"] for item in loader.list_engrams()]

        total_errors = 0
        for name in targets:
            engram_dir = loader._resolve_engram_dir(name)
            if engram_dir is None:
                print(f"{name}: 1 errors, 0 warnings")
                print("  [error] .: 未找到 Engram")
                total_errors += 1
                continue

            messages = lint_engram(engram_dir)
            error_count = sum(1 for m in messages if m.level == "error")
            warning_count = sum(1 for m in messages if m.level == "warning")
            print(f"{name}: {error_count} errors, {warning_count} warnings")
            for msg in messages:
                print(f"  [{msg.level}] {msg.file_path}: {msg.message}")
            total_errors += error_count

        if total_errors > 0:
            raise SystemExit(1)
        return

    if args.command == "search":
        _ = args.packs_dir  # kept for CLI interface consistency
        entries = _load_registry_entries()
        matched = search_registry(args.query, entries)
        if not matched:
            print("未找到匹配的 Engram")
            return
        for item in matched:
            print(_render_search_item(item))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
