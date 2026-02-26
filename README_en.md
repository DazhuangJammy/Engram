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
- MCP tools: `ping`, `list_engrams`, `get_engram_info`, `load_engram`, `read_engram_file`, `write_engram_file`, `capture_memory`, `consolidate_memory`, `delete_memory`, `correct_memory`, `add_knowledge`, `install_engram`
- Index-driven loading:
  - `load_engram` returns role/workflow/rules + knowledge index + examples index + dynamic memory index + global user memory
  - `read_engram_file` reads full knowledge or example files on demand
- Dynamic memory: automatically captures user preferences and key information during conversation, loaded on next session
- Global user memory: cross-Engram shared user info (age, city, etc.) auto-attached to every `load_engram`
- Memory TTL: `expires` archives stale memories to `{category}-expired.md` and hides them from loads
- Tiered index: `_index.md` keeps last 50 entries (hot layer); full history in `_index_full.md` (cold layer)
- Engram inheritance: `meta.json` supports `extends` field to merge parent knowledge index
- Cold-start onboarding: `## Onboarding` block in `rules.md` triggers first-session info collection
- CLI commands: `serve` / `list` / `install` / `init` / `stats`
- Stats dashboard: `engram-server stats` for memory statistics, `--tui` for rich rendering

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
- No code is added to your project
- Each time Claude Code starts, it automatically pulls the latest version from GitHub
- Engram packs are stored in `~/.engram` by default

After installation, **restart Claude Code** to start using it.

### One-Command Uninstall

```bash
claude mcp remove --scope user engram-server
```

> Uninstalling only removes the MCP config — your Engram data (`~/.engram/`) is preserved. To fully clean up data, run `rm -rf ~/.engram` manually.

## Quick Start

### Add System Prompt (Recommended)

Add the following prompt to the beginning of your project's `CLAUDE.md` (Claude Code) or `AGENTS.md` (Codex) to let AI automatically discover and use Engrams:

```text
You have an expert memory system available. Call list_engrams() from the engram-server MCP at the start of each conversation to see available experts.
- When a user's question matches an expert, call load_engram(name, query) to load its knowledge.
- When you identify cross-expert user info (age, city, job, language preferences, etc.), call capture_memory(..., is_global=True) to write to global memory.
- For time-sensitive memories ("user is studying for an exam", "user is injured"), add an expires param (YYYY-MM-DD, e.g. "2026-06-01"). Expired entries are archived and hidden from future loads.
- If load_engram returns an "Onboarding" section, naturally collect the listed info during conversation and capture_memory.
- When you identify important user preferences or key info during conversation, call capture_memory(name, content, category, summary, memory_type, tags, conversation_id, expires, is_global) to save it. Use memory_type to label the semantic type (preference/fact/decision/history/general/inferred/stated) and tags for filtering.
- If load_engram returns a "💡 N memories total" hint (hot-layer total ≥ 30), first call read_engram_file(name, "memory/{category}.md") to read the busiest category, then call consolidate_memory(name, category, consolidated_content, summary) to compress. You must compose consolidated_content yourself. Only supported for expert memory, not global memory.
- Users can also specify an expert directly with @expert-name.
- When you call any MCP tool, tell the user which MCP and which expert you used.
- After load_engram returns a knowledge index, if the summaries aren't enough to answer, call read_engram_file(name, "knowledge/xxx.md") to read the full file.
- When the user asks to delete a memory, call delete_memory(name, category, summary). Only for expert memory, not global memory.
- When the user corrects a memory, call correct_memory(name, category, old_summary, new_content, new_summary, memory_type, tags). Only for expert memory, not global memory.
- When conversation produces knowledge worth keeping long-term (not personal user info), call add_knowledge(name, filename, content, summary).
- To browse full memory history, call read_engram_file(name, "memory/_index_full.md") to read the cold-layer index.
- If load_engram returns an "Inherited Knowledge Index" section, call read_engram_file(parent_name, "knowledge/xxx.md") to read parent knowledge files.
- When the user asks about an engram's details, call get_engram_info(name).
- When the user wants to install a new engram, call install_engram(source) where source is a git URL.
- To directly edit an engram's role.md / workflow.md / rules.md or other non-knowledge files, call write_engram_file(name, path, content, mode).
- When the user asks about memory statistics or wants to know how many memories exist, suggest running `uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats` or `uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats --tui` in the terminal.
```

### 4. Restart Your AI Client and Start Using

## CLI Usage

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

Install Engram from git:

```bash
engram-server install <git-url> --packs-dir ~/.engram
```

Initialize a new Engram template:

```bash
engram-server init my-expert --packs-dir ~/.engram
```

View memory statistics (plain text):

```bash
uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats
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
| `install_engram` | `source` | Install Engram pack from git URL |

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
You have an expert memory system available. Call list_engrams() from the engram-server MCP at the start of each conversation to see available experts.
- When a user's question matches an expert, call load_engram(name, query) to load its knowledge.
- When you identify cross-expert user info (age, city, job, language preferences, etc.), call capture_memory(..., is_global=True) to write to global memory.
- For time-sensitive memories ("user is studying for an exam", "user is injured"), add an expires param (YYYY-MM-DD, e.g. "2026-06-01"). Expired entries are archived and hidden from future loads.
- If load_engram returns an "Onboarding" section, naturally collect the listed info during conversation and capture_memory.
- When you identify important user preferences or key info during conversation, call capture_memory(name, content, category, summary, memory_type, tags, conversation_id, expires, is_global) to save it. Use memory_type to label the semantic type (preference/fact/decision/history/general/inferred/stated) and tags for filtering.
- If load_engram returns a "💡 N memories total" hint (hot-layer total ≥ 30), first call read_engram_file(name, "memory/{category}.md") to read the busiest category, then call consolidate_memory(name, category, consolidated_content, summary) to compress. You must compose consolidated_content yourself. Only supported for expert memory, not global memory.
- Users can also specify an expert directly with @expert-name.
- When you call any MCP tool, tell the user which MCP and which expert you used.
- After load_engram returns a knowledge index, if the summaries aren't enough to answer, call read_engram_file(name, "knowledge/xxx.md") to read the full file.
- When the user asks to delete a memory, call delete_memory(name, category, summary). Only for expert memory, not global memory.
- When the user corrects a memory, call correct_memory(name, category, old_summary, new_content, new_summary, memory_type, tags). Only for expert memory, not global memory.
- When conversation produces knowledge worth keeping long-term (not personal user info), call add_knowledge(name, filename, content, summary).
- To browse full memory history, call read_engram_file(name, "memory/_index_full.md") to read the cold-layer index.
- If load_engram returns an "Inherited Knowledge Index" section, call read_engram_file(parent_name, "knowledge/xxx.md") to read parent knowledge files.
- When the user asks about an engram's details, call get_engram_info(name).
- When the user wants to install a new engram, call install_engram(source) where source is a git URL.
- To directly edit an engram's role.md / workflow.md / rules.md or other non-knowledge files, call write_engram_file(name, path, content, mode).
- When the user asks about memory statistics or wants to know how many memories exist, suggest running `uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats` or `uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats --tui` in the terminal.
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

> Your Engram data lives in `~/.engram/`, completely separate from the project code. Updating won't affect your existing data.

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

### Planned

- `engram-server lint`: Validate uses paths and index consistency
- Chaptered knowledge directories: Auto-split large documents into subdirectories + chapter indexes
- Engram community registry

## License

MIT
