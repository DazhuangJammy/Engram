# Engram MCP Server

[中文](./README.md) | English

> Engram — In neuroscience, the ensemble of neurons that stores a specific memory trace.

## The Vision

Memory as a shareable, loadable resource that flows between agents, enabling the stacking and fusion of capabilities.

"Memory" here isn't simple data exchange — it's a complete, causally-linked experience system:

- A person's personality traits and thinking patterns
- Life experiences and personal trajectory
- The motivations that drove them to specialize and become an expert
- The professional knowledge and judgment accumulated in their field

Package this memory and share it — anyone's AI agent can load it. When memories from diverse backgrounds and specializations converge on a single agent, that agent gains cross-domain cognitive depth, becoming a "super agent."

**In short: everyone contributes their "life save file," and the more an agent loads, the stronger it gets.**

---

Inject switchable expert memory into AI — not just knowledge retrieval, but a complete persona: **"who they are + what they know + how they think."** A set of Markdown files gives any AI expert-level memory. Zero vector dependencies, plug and play.

```
Engram      = Who the expert is + What they know + How they think
Skills/Tools = What actions they can perform
```

RAG can retrieve knowledge, but has no persona, no decision-making workflow — Engram solves this. Human-curated + model-driven retrieval is more precise than RAG for small-scale, high-quality knowledge — not because the tech is better, but because human curation is inherently higher quality than automatic chunking. Share your memory with others, and their AI instantly becomes the same expert. In the future, what people share won't be Skills — it'll be Memory.

Works with all MCP-compatible clients: Claude Desktop / Claude Code, Cursor, Windsurf, Codex, etc.

## Features

- Zero vector dependencies: no chromadb / litellm, only depends on `mcp`
- MCP tools: `ping`, `list_engrams`, `get_engram_info`, `load_engram`, `read_engram_file`, `write_engram_file`, `capture_memory`, `consolidate_memory`, `delete_memory`, `correct_memory`, `add_knowledge`, `install_engram`, `init_engram`, `lint_engrams`, `search_engrams`, `stats_engrams`, `create_engram_assistant`, `finalize_engram_draft`
- Index-driven loading:
  - `load_engram` returns role/workflow/rules + knowledge index + examples index + dynamic memory index + global user memory
  - `read_engram_file` reads full knowledge or example files on demand
- Dynamic memory: automatically captures user preferences and key information during conversation, loaded on next session
- Global user memory: cross-Engram shared user info (age, city, etc.) auto-attached to every `load_engram`
- Memory TTL: `expires` archives stale memories to `{category}-expired.md` and hides them from loads
- Tiered index: `_index.md` keeps last 50 entries (hot layer); full history in `_index_full.md` (cold layer)
- Engram inheritance: `meta.json` supports `extends` field to merge parent knowledge index
- Cold-start onboarding: `## Onboarding` block in `rules.md` triggers first-session info collection
- CLI commands: `serve` / `list` / `search` / `install` / `init` / `lint` / `stats`
- Stats dashboard: `engram-server stats` supports plain text / `--json` / `--csv` / `--tui`

## Design Philosophy: Index-Driven Layered Lazy Loading

### Why Not RAG

Problems with pure RAG (vector search for top-k chunks):
- Semantic similarity ≠ logical completeness — context gets lost
- Fragmented retrieval drops details
- Persona and decision workflows may be missed entirely
- Requires extra dependencies (vector DB, embedding models), adding deployment complexity

### Current Approach

After an Engram is loaded, content isn't dumped all at once — it's loaded in layers on demand:

```
Layer 1: Always loaded (returned by load_engram in one call)
  ├── role.md              Full text  ← Persona (background + communication style + principles)
  ├── workflow.md          Full text  ← Decision workflow (step-by-step process)
  ├── rules.md             Full text  ← Operating rules + common mistakes + Onboarding block
  ├── knowledge/_index.md  ← Knowledge index (+ inherited parent knowledge if extends is set)
  ├── examples/_index.md   ← Examples index (file list + one-line descriptions + uses references)
  ├── memory/_index.md     ← Dynamic memory hot layer (last 50 entries, TTL-filtered)
  └── <packs-dir>/_global/memory/_index.md  ← Global user memory (shared across all Engrams)

Layer 2: Loaded on demand (LLM reads index summaries, then proactively calls)
  └── read_engram_file(name, path)  ← Read any file, including memory/_index_full.md for full history

Layer 3: Written during conversation (LLM captures important info proactively)
  └── capture_memory(name, content, category, summary, memory_type, tags, conversation_id, expires, is_global)
```

The skeleton stays loaded at all times. Knowledge is controlled via "index with inline summaries + full text on demand." No matter how large an Engram gets, the injected content per turn stays manageable.

## Grouped Indexes (Nested Index)

When your knowledge base grows, use nested folders:

```text
knowledge/
  _index.md
  training-basics/
    _index.md
    squat-pattern.md
  nutrition-strategy/
    _index.md
    bulking-meal-plan.md
```

Top-level `_index.md` can reference grouped indexes like `→ 详见 knowledge/training-basics/_index.md`. `add_knowledge` supports `"subdir/filename"` and appends to the sub-index when `_index.md` exists in that subdirectory.

LLM 3-step workflow:
1. Use `load_engram` to read top-level `knowledge/_index.md`
2. If a grouped entry appears, call `read_engram_file(name, "knowledge/xxx/_index.md")`
3. Then read concrete files on demand, e.g. `knowledge/xxx/topic.md`

## Installation

### Prerequisites

Install [uv](https://docs.astral.sh/uv/) (an extremely fast Python package manager):

```bash
# macOS / Linux
brew install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### One-Command Install

Run a single command in your terminal to install and configure the MCP server:

```bash
claude mcp add --scope user engram-server -- uvx --from git+https://github.com/DazhuangJammy/Engram engram-server
```

This command will:
- Write the MCP config globally (available in all projects)
- On first run inside a project, automatically create `./.claude/engram/`
- Bootstrap two starter packs: `starter-complete` (fully runnable) and `starter-template` (instruction/template)
- Each time Claude Code starts, it automatically pulls the latest version from GitHub
- `~/.engram` can still be used as a shared/fallback directory (via `--packs-dir`)

After installation, **restart Claude Code** to start using it.

### One-Command Uninstall

```bash
claude mcp remove --scope user engram-server
```

> Uninstalling only removes the MCP config. It does not delete Engram data in either `./.claude/engram/` (project-level) or optional `~/.engram/`.

## Quick Start

### Add System Prompt (Recommended)

Add the following prompt to the beginning of your project's `CLAUDE.md` (Claude Code) or `AGENTS.md` (Codex) to let AI automatically discover and use Engrams:

```text
你有一个专家记忆系统可用。对话开始时先调用 engram-server 这个 MCP 中的 list_engrams() 查看可用专家。

# 自动执行规则（傻瓜式）
- 默认原则：能由模型直接完成的事，不让用户手动执行命令；优先直接调用 MCP 工具。
- 除非环境/权限阻塞，否则不要让用户“自己去终端跑命令”。
- 如果调用了 MCP，回复时要告诉用户调用了什么 MCP 和哪个专家。
- 首次进入新项目时，默认检查并使用 `./.claude/engram`。
- 目录策略统一为“项目级优先，`~/.engram` 为共享/回退目录”。

## 自然语言意图 -> MCP 自动映射
- 用户说“找/查/推荐某类 Engram” -> 自动调用 search_engrams(query)
- 用户说“安装某个 Engram” -> 自动调用 install_engram(source-or-name)
- 安装默认写入当前项目 `./.claude/engram`，不是默认全局目录。
- 用户说“初始化当前项目 engram” -> 优先检查 `starter-complete` / `starter-template` 是否存在。
- install_engram(name/source) 失败时，不中断用户：自动调用 search_engrams(query) 找候选后重试 install_engram。
- 用户说“看统计/导出报表” -> 自动调用 stats_engrams(format=plain/json/csv)
- 用户说“创建 Engram” -> 自动进入创建助手流程（create_engram_assistant + finalize_engram_draft）

## 专家加载与知识读取
- 用户问题匹配某个专家时，调用 load_engram(name, query)。
- load_engram 后优先看知识索引/案例索引；索引不足再 read_engram_file(name, "knowledge/xxx.md")。
- 若 workflow 明确写了 Skill 调用节点，按节点提示主动调用对应 Skills。
- load_engram 返回“继承知识索引”区块时，可 read_engram_file(父专家名, "knowledge/xxx.md") 读取父知识。
- 在 load_engram 后优先读取案例 frontmatter 的 id/title/uses/tags/updated_at，再决定要不要读具体 knowledge 文件。

## 记忆写入规则
- 发现跨专家通用信息（年龄、城市、职业、语言偏好等） -> capture_memory(..., is_global=True)
- 状态性信息（如“用户正在备考”）要加 expires（YYYY-MM-DD），到期自动归档隐藏。
- load_engram 出现“首次引导”区块时，自然收集并 capture_memory。
- 发现用户偏好/关键事实/关键决定时，及时 capture_memory(name, content, category, summary, memory_type, tags, conversation_id, expires, is_global)。
- 记忆条目较多出现“💡 当前共 N 条记忆”时，先 read_engram_file(name, "memory/{category}.md")，再 consolidate_memory(...)。
- 用户要求删除记忆 -> delete_memory(name, category, summary)
- 用户纠正记忆 -> correct_memory(name, category, old_summary, new_content, new_summary, memory_type, tags)
- 记忆较多查历史 -> read_engram_file(name, "memory/_index_full.md")

## 知识写入规则
- 对话中形成系统性可复用知识（方法论/对比分析/决策框架）时，先询问用户是否写入知识库，确认后 add_knowledge。
- 用户纠正知识库错误时，提议并执行 add_knowledge 更新。
- add_knowledge 支持分组路径：filename 可用 "子目录/文件名"（如 "训练基础/深蹲模式"）。

## 创建 Engram 助手（双模式）
- mode=from_conversation：把当前对话自动整理成 Engram 草稿。
- mode=guided：一步步引导用户填写；用户说“没有/你来”时自动补全。
- 统一流程：
  1) 先调用 create_engram_assistant(...) 生成草稿并回显
  2) 用户确认后调用 finalize_engram_draft(draft_json, confirm=True)
  3) finalize 后必须看 lint 结果（errors 必须先修复）
- 自动生成内容时必须提示：内容可能不完整，建议用户补充。
- 创建阶段不自动生成用户记忆条目；memory 保持空模板。

## 一致性校验
- 只要模型新增/修改了 knowledge/examples/index/meta/rules，完成后自动调用 lint_engrams(name)。
- 解释规则：
  - error > 0：阻断，先修复再交付。
  - 仅 warning：可交付，但需向用户说明风险。

## 其他
- 用户也可以用 @专家名 直接指定专家。
- 用户询问某个 engram 详细信息时，调用 get_engram_info(name)。
- 需要直接改 role.md/workflow.md/rules.md 等非知识库文件时，调用 write_engram_file(name, path, content, mode)。
- 新增/修改案例文件时，确保 frontmatter 字段齐全（id/title/uses/tags/updated_at），id 全局唯一，updated_at 用当天日期。
- 多案例命中时，先按 tags 匹配，再参考 updated_at 选更近的案例。
- 回复中引用案例时优先带 title + id，减少歧义。
- 若发现 frontmatter 缺字段或 uses 指向不存在文件，先修复再继续回答。
```

### 4. Restart Your AI Client and Start Using

On first MCP run in a project, you'll automatically get:
- `./.claude/engram/starter-complete` (complete sample Engram, directly loadable)
- `./.claude/engram/starter-template` (instruction/template Engram for customization)
- Both starter packs include a workflow reminder that Skills can be called at decision nodes.

## CLI Usage

> Note: when running via MCP, the server now prioritizes project-local `./.claude/engram/`. CLI examples below are for manually managing a specific directory (such as shared `~/.engram`).

Start MCP stdio server (default command):

```bash
engram-server serve --packs-dir ~/.engram
```

Equivalent shorthand:

```bash
engram-server --packs-dir ~/.engram
```

List installed Engrams:

```bash
engram-server list --packs-dir ~/.engram
```

Install Engram from git URL or registry name:

```bash
engram-server install <git-url|engram-name> --packs-dir ~/.engram
```

Initialize a new Engram template:

```bash
engram-server init my-expert --packs-dir ~/.engram
```

Initialize a template with nested knowledge indexes:

```bash
engram-server init my-expert --nested --packs-dir ~/.engram
```

Search Engrams in the registry:

```bash
engram-server search fitness --packs-dir ~/.engram
```

Run data consistency checks:

```bash
engram-server lint [name] --packs-dir ~/.engram
```

View memory statistics (plain text):

```bash
uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats
```

View memory statistics (JSON):

```bash
uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats --json
```

View memory statistics (CSV):

```bash
uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats --csv
```

View memory statistics (Rich rendering):

```bash
uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats --tui
```

> If you use a custom `--packs-dir` in MCP config, keep the same directory for all CLI commands here.
>
> Tip: the command is long — set an alias for convenience:
> ```bash
> alias engram='uvx --from git+https://github.com/DazhuangJammy/Engram engram-server'
> # Then just use: engram stats / engram stats --tui / engram list
> ```

### How To Use New Features (v0.9.0 / v1.0.0 / v1.1.0)

1) Data validation (`lint`)

```bash
# Validate all Engrams
engram-server lint --packs-dir ~/.engram

# Validate one Engram
engram-server lint fitness-coach --packs-dir ~/.engram
```

> Exit code: returns 1 if any error exists; returns 0 when only warnings exist.

2) Stats export (JSON / CSV)

```bash
engram-server stats --json --packs-dir ~/.engram
engram-server stats --csv --packs-dir ~/.engram
```

3) Search + install from Registry

```bash
# Search first
engram-server search fitness --packs-dir ~/.engram

# Install by name (resolved to source URL automatically)
engram-server install fitness-coach --packs-dir ~/.engram
```

4) Initialize nested-index template

```bash
engram-server init my-expert --nested --packs-dir ~/.engram
```

5) Write grouped knowledge in conversation (MCP)

When calling `add_knowledge(name, filename, content, summary)`, `filename` can be nested, for example:

```text
filename = "training-basics/squat-pattern"
```

It writes to `knowledge/training-basics/squat-pattern.md`; if `knowledge/training-basics/_index.md` exists, the entry is appended there first.

### Foolproof Engram Creation (Two Modes)

When the user says “create an Engram” in natural language, the model should run this flow automatically:

1) Generate draft  
- Conversation-to-draft: `create_engram_assistant(mode=\"from_conversation\", ...)`
- Guided creation: `create_engram_assistant(mode=\"guided\", ...)`

2) Show summary and confirm  
- Show name, knowledge files, example files, and auto-filled fields
- Clearly state that auto-generated content may be incomplete

3) Finalize after confirmation  
- `finalize_engram_draft(draft_json, confirm=True, nested=True)`
- The tool runs lint automatically and returns errors/warnings
- If errors exist, fix before delivery

Example user intents:
- “Turn our discussion into an Engram” (from_conversation)
- “Create an interviewer Engram and fill details for me” (guided + auto-fill)

## MCP Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `ping` | none | Connectivity test, returns `pong` |
| `list_engrams` | none | List available Engrams (with descriptions and file counts) |
| `get_engram_info` | `name` | Get full `meta.json` |
| `load_engram` | `name`, `query` | Load role/workflow/rules full text + knowledge index (with inline summaries) + examples index (with uses) + dynamic memory hot index + optional global memory/inherited knowledge/onboarding |
| `read_engram_file` | `name`, `path` | Read a single file on demand (with path traversal protection) |
| `write_engram_file` | `name`, `path`, `content`, `mode` | Write or append content to an Engram pack (for auto-packaging) |
| `capture_memory` | `name`, `content`, `category`, `summary`, `memory_type`, `tags`, `conversation_id`, `expires`, `is_global` | Capture user preferences and key info during conversation, supports type labels, tags, TTL expiry, and global write |
| `consolidate_memory` | `name`, `category`, `consolidated_content`, `summary` | Compress raw memory entries into a dense summary, archiving originals to `{category}-archive.md` |
| `delete_memory` | `name`, `category`, `summary` | Delete a specific memory entry by summary, removing it from both the index and category file |
| `correct_memory` | `name`, `category`, `old_summary`, `new_content`, `new_summary`, `memory_type`, `tags` | Correct an existing memory entry, updating both the index and category file |
| `add_knowledge` | `name`, `filename`, `content`, `summary` | Add a new knowledge file to an Engram and update the knowledge index automatically |
| `install_engram` | `source` | Install Engram pack from git URL or registry name |
| `init_engram` | `name`, `nested` | Initialize a new Engram through MCP (optionally with nested knowledge indexes) |
| `lint_engrams` | `name?` | Run consistency checks through MCP and return error/warning details |
| `search_engrams` | `query` | Search registry entries through MCP |
| `stats_engrams` | `format` | Get stats through MCP with `plain/json/csv` formats |
| `create_engram_assistant` | `mode`, `name?`, `topic?`, `audience?`, `style?`, `constraints?`, `language?`, `conversation?` | Generate an Engram draft (from_conversation / guided), with optional auto-fill for missing fields |
| `finalize_engram_draft` | `draft_json`, `name?`, `nested`, `confirm` | Finalize confirmed draft into files and run lint automatically |

### `load_engram` Response Format

```markdown
# Loaded Engram: fitness-coach

## User Focus
{query}

## Role
{role.md full text}

## Workflow
{workflow.md full text}

## Rules
{rules.md full text}

## Knowledge Index
{knowledge/_index.md content, with inline summaries}

## Examples Index
{examples/_index.md content, with uses references}

## Dynamic Memory
{memory/_index.md content, with auto-captured user preferences and key info, wrapped in <memory> tags}

## Global User Memory (optional)
{active entries from <packs-dir>/_global/memory/_index.md, wrapped in <global_memory> tags}

## Onboarding (optional)
{content extracted from ## Onboarding in rules.md}
```

> If `meta.json` includes `extends`, the response also includes an "Inherited Knowledge Index (from parent)" section. Current behavior supports one inheritance level only.

### Memory Types (memory_type)

`capture_memory` supports seven semantic types:

| Type | Description | Example |
|------|-------------|---------|
| `preference` | User preferences | Prefers morning workouts, dislikes running |
| `fact` | Objective facts about the user | Left knee injury, height 175cm |
| `decision` | Key decisions made during conversation | Decided to start with 3x/week |
| `history` | Important conversation milestones | Passed first-round algorithm interview |
| `stated` | Information explicitly stated by the user (high confidence) | "I have an old knee injury" |
| `inferred` | Information inferred by LLM from behavior (low confidence) | Chose morning 3 times → inferred early-riser preference |
| `general` | Default, unclassified | Other information |

`stated` vs `inferred`: when referencing `inferred` memories, add hedging language like "possibly"; `correct_memory` can upgrade `inferred` to `stated`.

`expires` uses `YYYY-MM-DD` (ISO 8601 date part, e.g. `"2026-06-01"`). Expiry is evaluated by UTC date; expired memory is moved to `memory/{category}-expired.md` and hidden from load results. Suited for time-bound states ("user is studying for an exam").

`is_global=True` writes the memory to `<packs-dir>/_global/memory/`, automatically appended to every Engram on load. Suited for cross-expert user basics (age, city, occupation, etc.).

### Global User Memory

**The problem it solves:** You tell the fitness coach "I'm 28, living in Shenzhen" — but the language partner has no idea. Global memory lets you write that once and share it across all experts.

**Storage location:** `<packs-dir>/_global/memory/` — same structure as a regular Engram's `memory/` directory. If `--packs-dir` is the default `~/.engram`, the actual path is `~/.engram/_global/memory/`.

**How to use:**

```
When the user mentions basic personal info for the first time:
  → AI calls capture_memory(
        name="fitness-coach",   ← current expert name (used as throttle key, doesn't affect write location)
        content="User's name is Jammy, 28 years old, lives in Shenzhen, indie developer",
        category="user-profile",
        summary="Jammy, 28, Shenzhen, indie developer",
        memory_type="fact",
        is_global=True           ← write to global, not the current Engram
    )
  → Next time any Engram is loaded, load_engram appends at the end:
    ## Global User Memory
    <global_memory>
    - `memory/user-profile.md` [2026-02-25] [fact] Jammy, 28, Shenzhen, indie developer
    </global_memory>
```

**What belongs in global memory:**
- Name, age, city
- Occupation and work background
- Language preference (Chinese/English)
- Long-term health conditions (chronic illness, allergies)

**What does NOT belong in global memory:**
- Expert-specific preferences (training plan preferences → write to the fitness coach's own memory)
- Time-bound states (currently studying for an exam → use the `expires` parameter)

**Directory structure (see `examples/_global/`):**

```
<packs-dir>/_global/
└── memory/
    ├── _index.md          ← hot-layer index (last 50 entries)
    ├── _index_full.md     ← cold-layer index (full history)
    └── user-profile.md    ← user basic info
```

`tags` supports multiple labels for topic-based filtering, e.g. `["injury", "knee"]`.

`conversation_id` is optional — binds a memory to a specific conversation for future scoped retrieval.

### Memory Consolidation (consolidate_memory)

As conversations accumulate, raw entries in a category keep growing. `consolidate_memory` solves this:

```
Raw entries keep appending (append-only)
         ↓
A category exceeds 30 entries
         ↓
AI calls read_engram_file to read raw content
         ↓
AI writes a dense, deduplicated summary
         ↓
Call consolidate_memory → originals archived, summary replaces them
```

**Different memory types, different consolidation strategies:**

| Type | Characteristic | Strategy |
|------|---------------|----------|
| `fact` | Stable, rarely changes | Keep permanently, no consolidation needed |
| `preference` | Semi-stable, occasionally updated | Merge and compress, always loaded |
| `decision` | Time-sensitive | Keep recent, compress old |
| `history` | Newer = more relevant | Consolidate periodically, archive old |

After consolidation, `_index.md` holds a single `[consolidated]` entry — context injection stays manageable forever.
Originals are archived to `memory/{category}-archive.md`, still readable via `read_engram_file`.

### Memory Deletion (delete_memory)

Use this when the user explicitly says a memory is wrong or outdated. Read the index first to get the exact summary text, then call delete:

```
User: "I don't live in Beijing anymore, please remove that record"
  → AI calls read_engram_file("name", "memory/_index.md") to find the entry
  → Confirms summary text → calls delete_memory("name", "user-profile", "Lives in Beijing")
  → Entry removed from both the index and the category file
```

> The `summary` parameter must exactly match the text in the index — read the index before calling.

### Memory Correction (correct_memory)

Use this when the user says a captured memory is inaccurate. The original timestamp is preserved; only content and summary are updated:

```
User: "I'm not 80kg anymore, I'm 75kg now"
  → AI reads memory/_index.md, finds summary "Weight 80kg"
  → calls correct_memory("name", "user-profile", "Weight 80kg",
      "User weight 75kg (lost weight)", "Weight 75kg", memory_type="fact")
  → Entry content and index updated in sync, timestamp preserved
```

`memory_type` and `tags` can be updated at the same time — no separate operation needed.

### Dynamic Knowledge Expansion (add_knowledge)

Use this when a new knowledge topic comes up during conversation. Suited for occasional additions, not bulk imports:

```
User: "Please save the running technique tips we just discussed to the knowledge base"
  → AI organizes the content
  → calls add_knowledge("name", "running-technique", "# Running Technique\n\nLanding...", "Landing form and cadence optimization")
  → New file written to knowledge/running-technique.md, knowledge/_index.md updated automatically
```

> When the knowledge index exceeds 15 entries, consider manually organizing `_index.md` with `###` group headings to help the model navigate quickly.



### Automatic Mode

The agent sees summaries from `list_engrams`, determines if the current question matches an expert, and loads automatically:

```
User: "My knee hurts, can I still do squats?"
  → agent calls list_engrams(), sees fitness-coach
  → matches → calls load_engram("fitness-coach", "knee pain squats")
  → reads knowledge index summaries, decides to dig deeper
  → calls read_engram_file("fitness-coach", "knowledge/膝关节损伤训练.md")
  → gets full knowledge → answers as the expert
```

### Manual Mode

User specifies with `@engram-name`, agent skips matching and loads directly:

```
User: "@fitness-coach help me create a muscle-building plan"
  → agent recognizes @ directive → calls load_engram("fitness-coach", "muscle building plan")
```

> @ directive parsing depends on the agent side. The MCP server only provides tools, it doesn't process message formats.

## Engram Pack Structure

```text
<engram-name>/
  meta.json           # supports extends for inheritance
  role.md
  workflow.md
  rules.md            # can include ## Onboarding
  knowledge/
    _index.md
    <topic>.md
  examples/           # optional
    _index.md
    <case>.md
  memory/             # dynamic memory (auto-generated, captured during conversation)
    _index.md         # hot layer: latest 50 entries
    _index_full.md    # cold layer: full history (read on demand)
    <category>.md
```

`meta.json` can include `extends` for Engram inheritance:

```json
{
  "name": "sports-nutritionist",
  "extends": "fitness-coach",
  "description": "Sports nutritionist that builds on fitness-coach knowledge"
}
```

On load, the parent Engram's knowledge index is merged (single-level inheritance); the child Engram's role/workflow/rules/examples/memory stay independent.

`meta.json` example:

```json
{
  "name": "fitness-coach",
  "author": "test",
  "version": "1.0.0",
  "description": "Former rehab facility training director, 10 years coaching experience...",
  "tags": ["fitness", "nutrition", "training plans"],
  "knowledge_count": 5,
  "examples_count": 3
}
```

## Use Cases

Engram isn't just an expert system — it's a universal identity injection framework for any role you want AI to "become."

| Scenario | Description | Example |
|----------|-------------|---------|
| Expert Advisor | Fitness coach, lawyer, nutritionist, etc. | `fitness-coach` |
| Chat Companion | A distant friend or family member, preserving their speech patterns | `old-friend` |
| Language Partner | Native speaker role, natural correction through conversation | `language-partner` |
| Mock Interviewer | Technical interviewer with full interview flow and feedback | `mock-interviewer` |
| User Persona | Target user role for product validation and user research | `user-persona` |
| Brand Support | Unified customer service persona with standard procedures | `brand-support` |
| Role Play | Novel characters, game NPCs for creative or interactive narrative | `novel-character` |
| Historical Figure | Thought pattern reconstruction based on historical records | `historical-figure` |
| Project Context | Team architecture decisions, tech choices, and lessons learned | `project-context` |
| Past Self | Record thoughts from a life stage for future reflection | `past-self` |

## Working with MCP Tools and Skills

Engram handles "who + what they know + how they think." MCP Tools and Skills handle "what they can do."

```
Engram    = Identity + Knowledge + Decision workflow
MCP Tools = Callable external capabilities (databases, monitoring, APIs, etc.)
Skills    = Triggerable action workflows (deploy, rollback, code generation, etc.)
```

In `workflow.md`, you can specify which MCP Tools or Skills to call at specific decision points. After loading an Engram, the model follows the workflow to proactively call these tools at the right moments.
This reminder is already included in both `starter-complete` and `starter-template`, so users can copy it directly.

## Create Your Own Engram

Minimum viable pack:

```text
my-engram/
  meta.json
  role.md
```

Recommended full structure:

- `role.md`: Background, communication style, core beliefs
- `workflow.md`: Decision workflow
- `rules.md`: Operating rules, common mistakes
- `knowledge/_index.md` + topic files: Knowledge index (with inline summaries) + details
- `examples/_index.md` + case files: Examples index (with uses references) + case studies
- `memory/`: Dynamic memory directory (auto-generated during conversation, no manual setup needed)

### Example Metadata (YAML frontmatter)

Each example file should use structured YAML frontmatter with at least `id` / `title` / `uses` / `tags` / `updated_at`:

```markdown
---
id: example_fitness_coach_knee_pain_office_worker
title: Knee Pain Office Worker
uses:
  - knowledge/knee-injury-training.md
  - knowledge/beginner-training-plan.md
tags:
  - fitness-coach
  - example
  - knee-injury-training
  - beginner-training-plan
updated_at: 2026-02-26
---

Problem: 32-year-old office worker, knee discomfort from prolonged sitting...
```

`uses` defines example-to-knowledge links; `id` gives stable unique identity; `updated_at` should follow `YYYY-MM-DD`; `tags` enables topic filtering. Knowledge files stay atomic, while examples focus on combination and application.

> When you have more than 10 knowledge files, use `###` headings in `_index.md` to group by topic, helping the model locate relevant entries quickly.

Available templates and examples:

- `examples/template/` — Blank template
- `examples/fitness-coach/` — Expert advisor (fitness coach)
- `examples/sports-nutritionist/` — Inheritance example (extends `fitness-coach`, sports nutritionist)
- `examples/old-friend/` — Chat companion (old friend in San Francisco)
- `examples/language-partner/` — Language partner (Tokyo office worker, Japanese practice)
- `examples/mock-interviewer/` — Mock interviewer (full technical interview flow)
- `examples/user-persona/` — User persona (target user for product validation)
- `examples/brand-support/` — Brand support (unified scripts and service standards)
- `examples/novel-character/` — Fictional character (cyberpunk hacker)
- `examples/historical-figure/` — Historical figure (Wang Yangming, Neo-Confucian dialogue)
- `examples/project-context/` — Project context (team architecture decisions and lessons)
- `examples/past-self/` — Past self (fresh graduate version from 2020)

## Integration with AI Tools

> In all configurations below, replace `/path/to/engram-mcp-server` with your actual project path.

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "engram-server": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/engram-mcp-server",
        "engram-server",
        "--packs-dir", "~/.engram"
      ]
    }
  }
}
```

### Claude Code

Project-level (`.mcp.json` in project root) or global (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "engram-server": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/engram-mcp-server",
        "engram-server",
        "--packs-dir", "~/.engram"
      ]
    }
  }
}
```

### Cursor / Windsurf / Other MCP-Compatible IDEs

Add the same server configuration in your IDE's MCP settings. Refer to each IDE's documentation for the config file location.

### Codex

```json
{
  "mcpServers": {
    "engram-server": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/engram-mcp-server",
        "engram-server",
        "--packs-dir", "~/.engram"
      ]
    }
  }
}
```

## Enable Auto-Loading

### Method A: Add System Prompt (Recommended)

Add the following prompt to the beginning of your AI tool's instruction file:

| AI Tool | Instruction File |
|---------|-----------------|
| Claude Code | `CLAUDE.md` in project root |
| Codex | `AGENTS.md` in project root |
| Others | Your tool's system prompt configuration |

```text
你有一个专家记忆系统可用。对话开始时先调用 engram-server 这个 MCP 中的 list_engrams() 查看可用专家。

# 自动执行规则（傻瓜式）
- 默认原则：能由模型直接完成的事，不让用户手动执行命令；优先直接调用 MCP 工具。
- 除非环境/权限阻塞，否则不要让用户“自己去终端跑命令”。
- 如果调用了 MCP，回复时要告诉用户调用了什么 MCP 和哪个专家。
- 首次进入新项目时，默认检查并使用 `./.claude/engram`。
- 目录策略统一为“项目级优先，`~/.engram` 为共享/回退目录”。

## 自然语言意图 -> MCP 自动映射
- 用户说“找/查/推荐某类 Engram” -> 自动调用 search_engrams(query)
- 用户说“安装某个 Engram” -> 自动调用 install_engram(source-or-name)
- 安装默认写入当前项目 `./.claude/engram`，不是默认全局目录。
- 用户说“初始化当前项目 engram” -> 优先检查 `starter-complete` / `starter-template` 是否存在。
- install_engram(name/source) 失败时，不中断用户：自动调用 search_engrams(query) 找候选后重试 install_engram。
- 用户说“看统计/导出报表” -> 自动调用 stats_engrams(format=plain/json/csv)
- 用户说“创建 Engram” -> 自动进入创建助手流程（create_engram_assistant + finalize_engram_draft）

## 专家加载与知识读取
- 用户问题匹配某个专家时，调用 load_engram(name, query)。
- load_engram 后优先看知识索引/案例索引；索引不足再 read_engram_file(name, "knowledge/xxx.md")。
- 若 workflow 明确写了 Skill 调用节点，按节点提示主动调用对应 Skills。
- load_engram 返回“继承知识索引”区块时，可 read_engram_file(父专家名, "knowledge/xxx.md") 读取父知识。
- 在 load_engram 后优先读取案例 frontmatter 的 id/title/uses/tags/updated_at，再决定要不要读具体 knowledge 文件。

## 记忆写入规则
- 发现跨专家通用信息（年龄、城市、职业、语言偏好等） -> capture_memory(..., is_global=True)
- 状态性信息（如“用户正在备考”）要加 expires（YYYY-MM-DD），到期自动归档隐藏。
- load_engram 出现“首次引导”区块时，自然收集并 capture_memory。
- 发现用户偏好/关键事实/关键决定时，及时 capture_memory(name, content, category, summary, memory_type, tags, conversation_id, expires, is_global)。
- 记忆条目较多出现“💡 当前共 N 条记忆”时，先 read_engram_file(name, "memory/{category}.md")，再 consolidate_memory(...)。
- 用户要求删除记忆 -> delete_memory(name, category, summary)
- 用户纠正记忆 -> correct_memory(name, category, old_summary, new_content, new_summary, memory_type, tags)
- 记忆较多查历史 -> read_engram_file(name, "memory/_index_full.md")

## 知识写入规则
- 对话中形成系统性可复用知识（方法论/对比分析/决策框架）时，先询问用户是否写入知识库，确认后 add_knowledge。
- 用户纠正知识库错误时，提议并执行 add_knowledge 更新。
- add_knowledge 支持分组路径：filename 可用 "子目录/文件名"（如 "训练基础/深蹲模式"）。

## 创建 Engram 助手（双模式）
- mode=from_conversation：把当前对话自动整理成 Engram 草稿。
- mode=guided：一步步引导用户填写；用户说“没有/你来”时自动补全。
- 统一流程：
  1) 先调用 create_engram_assistant(...) 生成草稿并回显
  2) 用户确认后调用 finalize_engram_draft(draft_json, confirm=True)
  3) finalize 后必须看 lint 结果（errors 必须先修复）
- 自动生成内容时必须提示：内容可能不完整，建议用户补充。
- 创建阶段不自动生成用户记忆条目；memory 保持空模板。

## 一致性校验
- 只要模型新增/修改了 knowledge/examples/index/meta/rules，完成后自动调用 lint_engrams(name)。
- 解释规则：
  - error > 0：阻断，先修复再交付。
  - 仅 warning：可交付，但需向用户说明风险。

## 其他
- 用户也可以用 @专家名 直接指定专家。
- 用户询问某个 engram 详细信息时，调用 get_engram_info(name)。
- 需要直接改 role.md/workflow.md/rules.md 等非知识库文件时，调用 write_engram_file(name, path, content, mode)。
- 新增/修改案例文件时，确保 frontmatter 字段齐全（id/title/uses/tags/updated_at），id 全局唯一，updated_at 用当天日期。
- 多案例命中时，先按 tags 匹配，再参考 updated_at 选更近的案例。
- 回复中引用案例时优先带 title + id，减少歧义。
- 若发现 frontmatter 缺字段或 uses 指向不存在文件，先修复再继续回答。
```

### Method B: MCP Prompt

The server exposes `engram-system-prompt`. Clients that support MCP Prompts can inject it automatically.

### Method C: Tool Description Guidance (Zero Config)

The tool descriptions for `list_engrams` / `load_engram` / `read_engram_file` already include usage flow guidance. Some AI clients will trigger automatically without extra configuration.

## Adjusting the Consolidation Threshold

When the total memory entries in `_index.md` reach the threshold, `load_engram` hints the AI to consolidate. The default is **30 entries**, configurable at:

File: `src/engram_server/loader.py`, constant `_CONSOLIDATE_HINT_THRESHOLD`

```python
_CONSOLIDATE_HINT_THRESHOLD = 30
```

Suggested values:
- `20`: Frequent conversations, prefer lean memory
- `30`: Default, suits most use cases (~10-15 conversations per consolidation hint)
- `50`: Light usage, less frequent consolidation

> This is only a hint — the AI won't consolidate automatically. It needs to call `consolidate_memory` explicitly.

---

## Updating the Project

If you used the one-command install (`uvx --from git+...`), clear the cache and restart to get the latest version:

```bash
uv cache clean
```

Then **restart Claude Code** — `uvx` will automatically pull the latest code from GitHub.

> Current behavior: on first run, a project-local `./.claude/engram/` is auto-created (with `starter-complete` and `starter-template`). `~/.engram/` still works as a cross-project shared directory.

## Multi-Device Sync

### Option A: iCloud / Dropbox / OneDrive

Point `--packs-dir` to a synced folder so multiple devices share the same Engram data:

```bash
claude mcp add --scope user engram-server -- \
  uvx --from git+https://github.com/DazhuangJammy/Engram engram-server \
  --packs-dir "$HOME/Library/Mobile Documents/com~apple~CloudDocs/EngramPacks"
```

> On Windows, switch to a OneDrive path such as `C:\\Users\\<your-user>\\OneDrive\\EngramPacks`.

### Option B: Git Sync (`~/.engram` as a git repo)

If you prefer auditable changes, initialize `~/.engram` as a git repository and push to a private remote:

```bash
cd ~/.engram
git init
git remote add origin <your-private-repo-url>
git add .
git commit -m "init engram packs"
git push -u origin main
```

On other devices, pull the same repo and keep the same MCP config.

## Testing

```bash
pytest -q
```

## Roadmap

### Completed (v0.1.0)

- MCP server core: list / load / read_file / install / init
- Layered lazy-loading architecture: base layer + index (with inline summaries) + on-demand full text
- Example-to-knowledge links: structured YAML frontmatter (`id/title/uses/tags/updated_at`)
- Template system: `engram-server init` creates standard structure
- Test coverage: loader / server / install
- 11 complete example Engrams

### Completed (v0.2.0)

- Dynamic memory: `capture_memory` auto-captures user preferences and key info during conversation
- Write capability: `write_engram_file` enables auto-packaging Engrams from conversations
- `load_engram` automatically loads `memory/_index.md`, no need for users to repeat themselves
- All example Engrams now include memory/ samples

### Completed (v0.3.0)

- `capture_memory` adds `memory_type` semantic classification (preference/fact/decision/history/general)
- `capture_memory` adds `tags` parameter for multi-label filtering
- `capture_memory` adds `conversation_id` for conversation-scoped memory binding
- Throttle protection: duplicate content within 30 seconds is silently skipped
- `load_engram` wraps dynamic memory in `<memory>` tags for clear AI distinction from knowledge
- Memory index format upgraded: includes type labels and tag info

### Completed (v0.4.0)

- `consolidate_memory` tool: compress raw entries into a dense summary, archive originals to `{category}-archive.md`
- `_index.md` holds a single `[consolidated]` entry after compression — context stays manageable
- `load_engram` auto-hints consolidation when memory entries ≥ 30
- Per-type consolidation strategy (fact: keep forever / preference: merge / history: archive periodically)
- Example Engrams now include `preferences-archive.md` showing archive format

### Completed (v0.5.0)

- `delete_memory` tool: delete a specific memory entry by summary, removing it from both the index and category file
- `correct_memory` tool: correct an existing memory entry, updating content, type, and tags in both the index and category file
- `add_knowledge` tool: dynamically add new knowledge files to an Engram during conversation, with automatic index update

### Completed (v0.8.0)

- `engram-server stats`: CLI stats command showing memory/knowledge/examples counts, type distribution, recent activity
- `engram-server stats --tui`: Rich-rendered stats dashboard (colored tables + panels)
- `rich>=13.0` as a required dependency, no impact on one-command install experience

### Completed (v0.9.0)

- `engram-server lint`: Validates index consistency, uses references, meta structure, extends links, empty knowledge files, and required files
- `engram-server stats --json / --csv`: Machine-readable export formats
- System prompt and template rules now include proactive knowledge extraction guidance

### Completed (v1.0.0)

- Grouped indexes: `add_knowledge` supports nested paths and updates sub-indexes when available
- `engram-server init --nested`: Generates templates with nested knowledge indexes
- Static Registry: added `registry.json`, `engram-server search`, and name-based `install` resolution
- Added multi-device sync guide in README (cloud folder or Git workflow)

### Completed (v1.1.0)

- Foolproof natural-language routing: users describe intent, model auto-calls MCP tools by default
- Two-mode creation assistant: `create_engram_assistant` supports `from_conversation` and `guided`
- Confirm-then-finalize flow: `finalize_engram_draft` materializes files and runs `lint_engrams`
- Transparent auto-generation notice: drafts mark auto-filled fields and warn that content may be incomplete
- Creation phase keeps `memory` as an empty template (no user memory is auto-written)

### Completed (v1.2.0)

- Project-level auto bootstrap: first run creates `./.claude/engram/`
- Two starter packs are injected automatically: `starter-complete` (fully runnable) + `starter-template` (instruction/template)
- MCP tools (`install_engram` / `init_engram` / `finalize_engram_draft`) now default to writing into the current project directory

### Planned

- `engram-server lint --fix`: Auto-fix orphan files, invalid index entries, and empty files
- `search_engram_knowledge(name, query)`: Server-side keyword scan and paragraph retrieval
- Engram community registry

## License

MIT
