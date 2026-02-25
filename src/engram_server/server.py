from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP

from engram_server.loader import EngramLoader

DEFAULT_PACKS_DIR = Path("~/.engram").expanduser()


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


def init_engram_pack(name: str, packs_dir: Path) -> dict[str, str | bool]:
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
        "   调用 capture_memory(name, content, category, summary) 记录下来\n"
        "7. 下次加载同一专家时，动态记忆会自动带入，无需用户重复说明\n"
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
        """Install an Engram pack from git URL."""
        result = install_engram_from_source(source=source, packs_dir=packs_dir)
        return str(result["message"])

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
        name: str, content: str, category: str, summary: str
    ) -> str:
        """Capture a memory entry during conversation.

Call this when you identify information worth remembering about the user,
such as preferences, personal context, past decisions, or feedback.
The memory is stored in memory/{category}.md and indexed automatically.
It will be loaded in future conversations with this Engram.

Args:
    name: Engram pack name
    content: The memory content to store
    category: Topic category (e.g. "user-profile", "preferences", "history")
    summary: One-line summary for the memory index"""
        if not _engram_exists(loader, name):
            return f"未找到 Engram: {name}"

        ok = loader.capture_memory(name, content, category, summary)
        if not ok:
            return f"记忆捕获失败: {category}"
        return f"已记录: [{category}] {summary}"

    return app


def run_server(packs_dir: Path) -> None:
    packs_dir = packs_dir.expanduser()
    packs_dir.mkdir(parents=True, exist_ok=True)

    loader = EngramLoader(packs_dir=packs_dir)
    app = create_mcp_app(loader=loader, packs_dir=packs_dir)
    app.run(transport="stdio")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Engram MCP Server")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start MCP stdio server")
    serve_parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR))

    list_parser = subparsers.add_parser("list", help="List installed Engrams")
    list_parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR))

    install_parser = subparsers.add_parser("install", help="Install Engram from git URL")
    install_parser.add_argument("source")
    install_parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR))

    init_parser = subparsers.add_parser("init", help="Create a new Engram from template")
    init_parser.add_argument("name")
    init_parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR))

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
        loader = EngramLoader(Path(args.packs_dir))
        print(_format_engrams(loader.list_engrams()))
        return

    if args.command == "install":
        result = install_engram_from_source(args.source, Path(args.packs_dir))
        print(result["message"])
        if not result["ok"]:
            raise SystemExit(1)
        return

    if args.command == "init":
        result = init_engram_pack(args.name, Path(args.packs_dir))
        print(result["message"])
        if not result["ok"]:
            raise SystemExit(1)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
