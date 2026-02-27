# Engram MCP Server

中文 | [English](./README_en.md)

> Engram（记忆印迹）——神经科学中，大脑存储特定记忆的神经元集合。

## 我的想法💡

将人或智能体的"记忆"作为一种可共享、可加载的资源，在不同智能体之间流通，最终实现能力的叠加与融合。

这里的"记忆"不是简单的数据交换，而是一套完整的、有因果链的经验体系：

- 一个人的性格特质与思维方式
- 成长经历与人生轨迹
- 驱动他选择某个专业、成为某个领域专家的动因
- 在该领域积累的专业知识与判断力

将这套记忆封装后共享出来，其他人的智能体可以加载它。当大量不同背景、不同专长的记忆被汇聚并加载到同一个智能体上时，这个智能体就具备了跨领域的认知深度，成为一个"超级智能体"。

**简单说：每个人贡献自己的"人生存档"，智能体加载得越多，就越强。**

---

给 AI 注入可切换的专家记忆——不只是知识检索，而是**"谁 + 知道什么 + 怎么思考"**的完整人设。一套 Markdown 文件就能让任何 AI 获得专家级记忆，零向量依赖，即插即用。

你还能把这些记忆加载到 N 个 subagent 里面让多个智能体干活

```
Engram      = 专家是谁 + 知道什么 + 怎么思考
Skills/Tools = 具体能做什么操作
```

RAG 能检索知识，但没有人设、没有决策流程——Engram 解决这个问题。人工策展 + 模型自主检索，在小规模高质量知识场景下比 RAG 更精准——不是因为技术更强，而是因为人工策展的质量天然高于自动切分。把 memory 分享给别人，对方的 AI 立刻成为同一个专家。未来大家共享的不是 Skills，而是 Memory。

支持所有 MCP 兼容客户端：Claude Desktop / Claude Code、Cursor、Windsurf、Codex 等。

## 功能特性

- 零向量依赖：不使用 chromadb / litellm，只依赖 `mcp`
- MCP 工具：`ping`、`list_engrams`、`get_engram_info`、`load_engram`、`read_engram_file`、`write_engram_file`、`capture_memory`、`consolidate_memory`、`delete_memory`、`correct_memory`、`add_knowledge`、`install_engram`、`init_engram`、`lint_engrams`、`search_engrams`、`stats_engrams`、`create_engram_assistant`、`finalize_engram_draft`
- 索引驱动加载：
  - `load_engram` 返回角色/工作流程/规则 + 知识索引（含内联摘要）+ 案例索引（含 uses）+ 动态记忆索引 + 全局用户记忆
  - `read_engram_file` 按路径按需读取知识或案例全文
- 动态记忆：对话中自动捕获用户偏好和关键信息，下次加载时自动带入
- 全局用户记忆：跨专家共享的用户基础信息（年龄、城市等），所有 Engram 加载时自动附加
- 记忆 TTL：支持 `expires` 字段，到期记忆自动归档到 `{category}-expired.md` 并隐藏
- Index 分层：`_index.md` 只保留最近50条（热层），完整记录写入 `_index_full.md`（冷层）
- Engram 继承：`meta.json` 支持 `extends` 字段，自动合并父 Engram 的 knowledge index
- 冷启动引导：`rules.md` 支持 `## Onboarding` 区块，首次使用时自动触发信息收集
- CLI 命令：`serve` / `list` / `search` / `install` / `init` / `lint` / `stats`
- 统计面板：`engram-server stats` 支持纯文本 / `--json` / `--csv` / `--tui`

## 设计理念：索引驱动的分层懒加载

### 为什么不用 RAG

纯 RAG（向量搜索取 top-k 片段）的问题：
- 语义相近 ≠ 逻辑完整，容易丢失上下文关联
- 碎片化检索会丢细节
- 人设和决策流程可能被漏掉
- 需要额外依赖（向量数据库、embedding 模型），增加部署复杂度

### 当前方案

Engram 被加载后，内容不是全量塞入，而是分层按需加载：

```
第一层：常驻加载（load_engram 时一次性返回）
  ├── role.md              全文  ← 角色人设（背景 + 沟通风格 + 回答原则）
  ├── workflow.md          全文  ← 工作流程（决策步骤）
  ├── rules.md             全文  ← 运作规则 + 常见错误 + Onboarding 区块
  ├── knowledge/_index.md  ← 知识索引（文件列表 + 一句话描述 + 内联摘要，若 extends 会附加父知识索引）
  ├── examples/_index.md   ← 案例索引（文件列表 + 一句话描述 + uses 关联）
  ├── memory/_index.md     ← 动态记忆热层索引（最近50条，TTL过滤）
  └── <packs-dir>/_global/memory/_index.md  ← 全局用户记忆（跨专家共享）

第二层：按需加载（LLM 根据索引摘要判断后主动调用）
  └── read_engram_file(name, path)  ← 读取任意知识、案例或记忆文件（含 memory/_index_full.md）

第三层：对话中写入（LLM 识别到重要信息时主动调用）
  └── capture_memory(name, content, category, summary, memory_type, tags, conversation_id, expires, is_global)  ← 捕获用户偏好、关键决定等
```

骨架常驻不丢，知识通过"索引内联摘要 + 全文按需"控制 token 消耗。不管 Engram 有多大，每次注入的内容都是可控的。

## 分组索引（Nested Index）

当知识文件变多时，建议使用二级目录分组：

```text
knowledge/
  _index.md
  训练基础/
    _index.md
    深蹲模式.md
  营养策略/
    _index.md
    增肌期配餐.md
```

顶层 `_index.md` 可写 `→ 详见 knowledge/训练基础/_index.md` 作为分组入口；`add_knowledge` 支持 `"子目录/文件名"` 写法，并在子目录存在 `_index.md` 时优先追加到子索引。

LLM 三步工作流：
1. `load_engram` 先读取顶层 `knowledge/_index.md`
2. 看到分组入口后，调用 `read_engram_file(name, "knowledge/xxx/_index.md")`
3. 再按需读取具体知识文件 `knowledge/xxx/topic.md`

## 安装

### 前置条件

需要先安装 [uv](https://docs.astral.sh/uv/)（极快的 Python 包管理器）：

```bash
# macOS / Linux
brew install uv
# 或
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 一键安装

在终端输入一条命令，即可完成安装和 MCP 配置：

```bash
claude mcp add --scope user engram-server -- uvx --from git+https://github.com/DazhuangJammy/Engram engram-server
```

这条命令会：
- 将 MCP 配置写入全局（所有项目都能用）
- 首次在某个项目中运行时，自动创建 `./.claude/engram/`
- 自动放入两个起始包：`starter-complete`（完整可加载）和 `starter-template`（说明模板）
- 每次 Claude Code 启动时，自动从 GitHub 拉取最新版本运行
- `~/.engram` 仍可作为共享/回退目录（由 `--packs-dir` 指定）

安装完成后**重启 Claude Code**，即可开始使用。

### 一键卸载

```bash
claude mcp remove --scope user engram-server
```

> 卸载只移除 MCP 配置，不会删除你的 Engram 数据（包括项目内 `./.claude/engram/` 与可选的 `~/.engram/`）。

## 快速开始

### 添加 System Prompt（推荐）

在项目的 `CLAUDE.md`（Claude Code）或 `AGENTS.md`（Codex）文件开头加入以下提示词，让 AI 自动发现和使用 Engram：

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

### 4. 重启 AI 客户端，开始使用

首次在项目里触发 MCP 后，会自动得到：
- `./.claude/engram/starter-complete`（完整示例 Engram，可直接加载）
- `./.claude/engram/starter-template`（说明/模板 Engram，用于改造）
- 两个起始包的 `workflow.md` 都已内置提醒：可在决策节点主动调用 MCP 工具或 Skills

## CLI 用法

> 说明：MCP 运行时默认优先使用当前项目的 `./.claude/engram/`。下面 CLI 示例主要用于手动管理指定目录（如共享目录 `~/.engram`）。

启动 MCP stdio 服务（默认命令）：

```bash
engram-server serve --packs-dir ~/.engram
```

等价写法：

```bash
engram-server --packs-dir ~/.engram
```

列出已安装 Engram：

```bash
engram-server list --packs-dir ~/.engram
```

从 git URL 或 registry 名称安装 Engram：

```bash
engram-server install <git-url|engram-name> --packs-dir ~/.engram
```

初始化一个新 Engram 模板：

```bash
engram-server init my-expert --packs-dir ~/.engram
```

初始化一个带二级知识索引的模板：

```bash
engram-server init my-expert --nested --packs-dir ~/.engram
```

搜索 registry 中的 Engram：

```bash
engram-server search fitness --packs-dir ~/.engram
```

运行数据一致性校验：

```bash
engram-server lint [name] --packs-dir ~/.engram
```

查看记忆统计（纯文本）：

```bash
uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats
```

查看记忆统计（JSON）：

```bash
uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats --json
```

查看记忆统计（CSV）：

```bash
uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats --csv
```

查看记忆统计（Rich 渲染版）：

```bash
uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats --tui
```

> 如果你在 MCP 配置里用了自定义 `--packs-dir`，这里的所有命令也要保持同一个目录。
>
> 小技巧：命令较长，可以设个 alias 简化日常使用：
> ```bash
> alias engram='uvx --from git+https://github.com/DazhuangJammy/Engram engram-server'
> # 之后直接用：engram stats / engram stats --tui / engram list
> ```

### 新功能怎么用（v0.9.0 / v1.0.0 / v1.1.0）

1) 数据校验（lint）

```bash
# 校验全部 Engram
engram-server lint --packs-dir ~/.engram

# 仅校验一个
engram-server lint fitness-coach --packs-dir ~/.engram
```

> 退出码规则：有 error 返回 1；只有 warning 返回 0。

2) 统计导出（JSON / CSV）

```bash
engram-server stats --json --packs-dir ~/.engram
engram-server stats --csv --packs-dir ~/.engram
```

3) 搜索与安装（Registry）

```bash
# 先搜索
engram-server search fitness --packs-dir ~/.engram

# 再按名称安装（install 会自动解析为 source URL）
engram-server install fitness-coach --packs-dir ~/.engram
```

4) 初始化分组索引模板

```bash
engram-server init my-expert --nested --packs-dir ~/.engram
```

5) 对话中写入分组知识（MCP）

当调用 `add_knowledge(name, filename, content, summary)` 时，`filename` 可用子目录格式，例如：

```text
filename = "训练基础/深蹲模式"
```

系统会写入 `knowledge/训练基础/深蹲模式.md`；若 `knowledge/训练基础/_index.md` 存在，则优先追加到子索引。

### 傻瓜式创建 Engram（双模式）

用户只用自然语言说“帮我创建一个 Engram”，模型应自动走以下流程：

1) 生成草稿  
- 对话直转：`create_engram_assistant(mode=\"from_conversation\", ...)`
- 引导创建：`create_engram_assistant(mode=\"guided\", ...)`

2) 回显并确认  
- 给用户展示草稿摘要（名称、知识目录、案例目录、自动补全字段）
- 明确提示：自动生成内容可能不完整，建议补充

3) 确认后落盘  
- `finalize_engram_draft(draft_json, confirm=True, nested=True)`
- 工具会自动执行 lint 并返回 errors/warnings
- 若有 error，先修复再交付

示例话术：
- “把我们刚才的讨论做成一个 Engram”（from_conversation）
- “帮我做一个面试官 Engram，你来补全细节”（guided + auto-fill）

## MCP 工具列表

| 工具 | 参数 | 说明 |
|------|------|------|
| `ping` | 无 | 连通性测试，返回 `pong` |
| `list_engrams` | 无 | 列出可用 Engram（含描述与文件统计） |
| `get_engram_info` | `name` | 获取完整 `meta.json` |
| `load_engram` | `name`, `query` | 加载角色/工作流程/规则全文 + 知识索引（含内联摘要）+ 案例索引（含 uses）+ 动态记忆（含热层索引）+ 可选全局记忆/继承知识/首次引导 |
| `read_engram_file` | `name`, `path` | 按需读取单个文件（含路径越界保护） |
| `write_engram_file` | `name`, `path`, `content`, `mode` | 写入或追加文件到 Engram 包（用于自动打包） |
| `capture_memory` | `name`, `content`, `category`, `summary`, `memory_type`, `tags`, `conversation_id`, `expires`, `is_global` | 对话中捕获用户偏好和关键信息，支持类型标注、标签、TTL过期、全局写入 |
| `consolidate_memory` | `name`, `category`, `consolidated_content`, `summary` | 将某个 category 的原始条目压缩为密集摘要，原始条目归档至 `{category}-archive.md` |
| `delete_memory` | `name`, `category`, `summary` | 按摘要精确删除一条记忆，同时从索引和分类文件中移除 |
| `correct_memory` | `name`, `category`, `old_summary`, `new_content`, `new_summary`, `memory_type`, `tags` | 修正一条已有记忆的内容，更新索引和分类文件 |
| `add_knowledge` | `name`, `filename`, `content`, `summary` | 向 Engram 添加新知识文件并自动更新知识索引 |
| `install_engram` | `source` | 从 git URL 或 registry 名称安装 Engram 包 |
| `init_engram` | `name`, `nested` | 通过 MCP 初始化新 Engram（可选二级知识索引模板） |
| `lint_engrams` | `name?` | 通过 MCP 执行一致性校验，返回 errors/warnings 明细 |
| `search_engrams` | `query` | 通过 MCP 搜索 registry 条目 |
| `stats_engrams` | `format` | 通过 MCP 获取统计，`format` 支持 `plain/json/csv` |
| `create_engram_assistant` | `mode`, `name?`, `topic?`, `audience?`, `style?`, `constraints?`, `language?`, `conversation?` | 生成 Engram 草稿（from_conversation / guided），缺失字段可自动补全并标注 |
| `finalize_engram_draft` | `draft_json`, `name?`, `nested`, `confirm` | 用户确认后落盘创建 Engram，并自动执行 lint 校验 |

### `load_engram` 返回内容格式

```markdown
# 已加载 Engram: fitness-coach

## 用户关注方向
{query}

## 角色
{role.md 全文}

## 工作流程
{workflow.md 全文}

## 规则
{rules.md 全文}

## 知识索引
{knowledge/_index.md 内容，含内联摘要}

## 案例索引
{examples/_index.md 内容，含 uses 关联}

## 动态记忆
{memory/_index.md 内容，含自动捕获的用户偏好和关键信息，用 <memory> 标签包裹}

## 全局用户记忆（可选）
{<packs-dir>/_global/memory/_index.md 的活跃条目，用 <global_memory> 标签包裹}

## 首次引导（可选）
{rules.md 中的 ## Onboarding 区块提取内容}
```

> 若 `meta.json` 配置了 `extends`，返回里还会出现"继承知识索引（来自父 Engram）"区块；当前仅支持单层继承。

### 记忆类型（memory_type）

`capture_memory` 支持七种语义类型：

| 类型 | 说明 | 示例 |
|------|------|------|
| `preference` | 用户偏好 | 偏好晨练、不喜欢跑步 |
| `fact` | 关于用户的客观事实 | 左膝有旧伤、身高175cm |
| `decision` | 对话中做出的关键决定 | 决定从3x/week开始训练 |
| `history` | 历史对话的重要节点 | 第一轮面试通过算法题 |
| `stated` | 用户明确说出的信息（高置信度）| "我膝盖有旧伤" |
| `inferred` | LLM 从行为推断的信息（低置信度）| 连续3次选早晨训练→推断偏好早起 |
| `general` | 默认，未分类 | 其他信息 |

`stated` vs `inferred` 的区别：引用 `inferred` 类记忆时应加"可能"等不确定性措辞；`correct_memory` 可将 `inferred` 升级为 `stated`。

`expires` 参数使用 `YYYY-MM-DD`（ISO 8601 的日期部分，如 `"2026-06-01"`）。系统按 UTC 日期判断是否过期，到期后记忆会转存到 `memory/{category}-expired.md` 并从加载结果中隐藏。适合状态性记忆（"用户正在备考"）。

`is_global=True` 将记忆写入 `<packs-dir>/_global/memory/`，所有 Engram 加载时都会自动附加这部分记忆。适合跨专家共享的用户基础信息（年龄、城市、职业等）。

### 全局用户记忆（Global Memory）

**解决的问题：** 你告诉健身教练"我28岁、住深圳"，但语言伙伴完全不知道。全局记忆让这类基础信息一次写入、所有专家共享。

**存储位置：** `<packs-dir>/_global/memory/`，结构与普通 Engram 的 memory 目录完全相同。若 `--packs-dir` 使用默认值 `~/.engram`，实际路径就是 `~/.engram/_global/memory/`。

**使用方式：**

```
用户第一次提到自己的基本信息时：
  → AI 调用 capture_memory(
        name="fitness-coach",   ← 当前专家名（用于节流key，不影响写入位置）
        content="用户名叫 Jammy，28岁，居住在深圳，职业是独立开发者",
        category="user-profile",
        summary="Jammy，28岁，深圳，独立开发者",
        memory_type="fact",
        is_global=True           ← 写入全局，而非当前 Engram
    )
  → 下次加载任意 Engram 时，load_engram 返回内容末尾自动附加：
    ## 全局用户记忆
    <global_memory>
    - `memory/user-profile.md` [2026-02-25] [fact] Jammy，28岁，深圳，独立开发者
    </global_memory>
```

**适合写入全局的信息：**
- 姓名、年龄、城市
- 职业和工作背景
- 语言偏好（中文/英文）
- 长期健康状况（如慢性病、过敏）

**不适合写入全局的信息：**
- 特定专家领域的偏好（训练计划偏好 → 写健身教练自己的 memory）
- 有时效性的状态（正在备考 → 用 expires 参数）

**目录结构示例（参见 `examples/_global/`）：**

```
<packs-dir>/_global/
└── memory/
    ├── _index.md          ← 热层索引（最近50条）
    ├── _index_full.md     ← 冷层索引（全量）
    └── user-profile.md    ← 用户基础信息
```

### 记忆压缩（consolidate_memory）

随着对话积累，某个 category 的原始条目会越来越多。`consolidate_memory` 解决这个问题：

```
原始条目不断追加（append-only）
         ↓
某个 category 超过 30 条时
         ↓
AI 调用 read_engram_file 读取原始内容
         ↓
AI 写出去重压缩的密集摘要
         ↓
调用 consolidate_memory → 原始条目归档，摘要替换
```

**不同类型的记忆，压缩策略不同：**

| 类型 | 特征 | 策略 |
|------|------|------|
| `fact` | 稳定，几乎不变 | 永久保留，无需压缩 |
| `preference` | 半稳定，偶尔更新 | 合并压缩，始终加载 |
| `decision` | 有时效性 | 保留近期，压缩旧的 |
| `history` | 越新越相关 | 定期压缩，归档旧的 |

压缩后 `_index.md` 只保留一条 `[consolidated]` 条目，context 注入量永远可控。
原始条目归档至 `memory/{category}-archive.md`，仍可通过 `read_engram_file` 查阅。

### 记忆删除（delete_memory）

当用户明确说某条记忆有误或已过时时使用。AI 先读取索引找到精确摘要，再调用删除：

```
用户："我已经不住北京了，帮我删掉那条记录"
  → AI 调用 read_engram_file("name", "memory/_index.md") 找到对应条目
  → 确认摘要文本 → 调用 delete_memory("name", "user-profile", "居住在北京")
  → 条目从索引和分类文件中同时移除
```

> `summary` 参数需与索引中的摘要文本完全匹配，建议先读索引再调用。

### 记忆修正（correct_memory）

当用户说某条记忆内容不准确时使用。原时间戳保留，只更新内容和摘要：

```
用户："我体重不是80kg了，现在75kg"
  → AI 读取 memory/_index.md，找到摘要"体重80kg"
  → 调用 correct_memory("name", "user-profile", "体重80kg",
      "用户体重75kg（已减重）", "体重75kg", memory_type="fact")
  → 原条目内容和索引同步更新，时间戳保留
```

`memory_type` 和 `tags` 可在修正时一并更新，无需单独操作。

### 动态知识扩充（add_knowledge）

对话中发现需要补充新知识主题时使用。适合"偶尔补充一个新主题"，不适合批量导入：

```
用户："帮我把刚才讨论的跑步技术要点记录到知识库里"
  → AI 整理内容
  → 调用 add_knowledge("name", "跑步技术", "# 跑步技术\n\n落地方式...", "落地方式与步频优化要点")
  → 新文件写入 knowledge/跑步技术.md，knowledge/_index.md 自动追加一行
```

> 知识索引条目超过 15 个时，建议手动整理 `_index.md` 的 `###` 分组结构，帮助模型快速定位。



### 自动模式

Agent 看到 `list_engrams` 返回的摘要，判断当前问题是否匹配某个专家，匹配则自动加载：

```
用户："我膝盖疼，还能做深蹲吗？"
  → agent 调用 list_engrams() 看到 fitness-coach
  → 判断匹配 → 调用 load_engram("fitness-coach", "膝盖疼深蹲")
  → 看到知识索引中的摘要，判断需要深入
  → 调用 read_engram_file("fitness-coach", "knowledge/膝关节损伤训练.md")
  → 拿到完整知识 → 以专家身份回答
```

### 手动模式

用户用 `@engram-name` 直接指定，agent 跳过判断直接加载：

```
用户："@fitness-coach 帮我制定一个增肌计划"
  → agent 识别 @ 指令 → 直接调用 load_engram("fitness-coach", "增肌计划")
```

> @ 指令的解析依赖 agent 端。MCP server 只提供工具，不处理消息格式。

## Engram 包结构

```text
<engram-name>/
  meta.json           # 支持 extends 字段实现继承
  role.md
  workflow.md
  rules.md            # 支持 ## Onboarding 区块
  knowledge/
    _index.md
    <topic>.md
  examples/           # 可选
    _index.md
    <case>.md
  memory/             # 动态记忆（自动生成，对话中捕获）
    _index.md         # 热层：最近50条
    _index_full.md    # 冷层：完整记录（按需加载）
    <category>.md
```

`meta.json` 支持 `extends` 字段实现 Engram 继承：

```json
{
  "name": "sports-nutritionist",
  "extends": "fitness-coach",
  "description": "运动营养师，在健身教练基础上增加营养学知识"
}
```

加载时自动合并父 Engram 的 knowledge index（仅单层继承）；子 Engram 的 role/workflow/rules/examples/memory 完全独立，不继承父项。

`meta.json` 示例：

```json
{
  "name": "fitness-coach",
  "author": "test",
  "version": "1.0.0",
  "description": "前康复机构训练主管，10年教练经验，擅长增肌减脂、膝肩不适训练调整与可执行计划落地",
  "tags": ["健身", "营养", "训练计划"],
  "knowledge_count": 5,
  "examples_count": 3
}
```

## 使用场景

Engram 不只是专家系统——它是一个通用的身份注入框架，适用于任何你想让 AI "成为"的角色。

| 场景 | 说明 | 示例 |
|------|------|------|
| 专家顾问 | 健身教练、律师、营养师等垂直领域专家 | `fitness-coach` |
| 聊天伙伴 | 远方的朋友、家人，保留他们的说话方式和记忆 | `old-friend` |
| 语言陪练 | 母语者角色，在聊天中自然纠错和教学 | `language-partner` |
| 模拟面试 | 技术面试官，完整的面试流程和反馈 | `mock-interviewer` |
| 用户画像 | 目标用户角色，用于产品验证和用户研究 | `user-persona` |
| 品牌客服 | 统一的客服人设、话术规范和处理流程 | `brand-support` |
| 角色扮演 | 小说角色、游戏NPC，用于创作或互动叙事 | `novel-character` |
| 历史人物 | 基于史料的思维模式还原，用于思辨和学习 | `historical-figure` |
| 项目上下文 | 团队的架构决策、技术选型、踩坑记录 | `project-context` |
| 过去的自己 | 记录某个人生阶段的想法，未来回顾和反思 | `past-self` |

## 与 MCP 工具和 Skills 协作

Engram 负责"是谁 + 知道什么 + 怎么思考"，MCP 工具和 Skills 负责"能做什么"。三者相辅相成：

```
Engram  = 身份 + 知识 + 决策流程
MCP 工具 = 可调用的外部能力（数据库、监控、API 等）
Skills  = 可触发的操作流程（部署、回滚、代码生成等）
```

在 `workflow.md` 中，你可以指定在特定决策节点调用哪些 MCP 工具或 Skills。模型加载 Engram 后，会按照 workflow 的指引，在合适的时机主动调用这些工具。
`starter-complete` 与 `starter-template` 里也已加入这条提醒，方便直接照着改。

示例（来自 `examples/project-context/workflow.md`）：

```markdown
## 可调用的外部工具

| 动作 | 工具类型 | 调用方式 |
|------|----------|----------|
| 查看最近提交 | MCP 工具 | 调用 git MCP server 的 git_log |
| 查看服务日志 | MCP 工具 | 调用 grafana MCP server 的 query_logs |
| 部署到测试环境 | Skill | 触发 /deploy-staging skill |
| 回滚线上版本 | Skill | 触发 /rollback skill |
```

这样 Engram 就不只是"知识库"，而是一个完整的专家工作台——既知道怎么判断，也知道该调什么工具。

## 创建自己的 Engram

最小可用包：

```text
my-engram/
  meta.json
  role.md
```

推荐完整结构：

- `role.md`：背景经历、沟通风格、核心信念
- `workflow.md`：决策流程
- `rules.md`：运作规则、常见错误、**记忆规则**（见下方）
- `knowledge/_index.md` + 主题文件：知识索引（含内联摘要）+ 细节
- `examples/_index.md` + 案例文件：案例索引（含 uses 关联）+ 复盘
- `memory/`：动态记忆目录（对话中自动生成，无需手动创建）

### 在 rules.md 中定义记忆规则（推荐）

`capture_memory` 依赖 AI 的主动判断，但 AI 不知道"这个 Engram 应该记什么"。在 `rules.md` 末尾加一节 `## 记忆规则`，明确告诉 AI 何时捕获、用什么 category 和 memory_type，可以大幅提升记忆的覆盖率和准确性。

```markdown
## 记忆规则
- 用户提到身体状况、伤病或疼痛时 → capture_memory(category="health", memory_type="fact", tags=["injury"])
  示例：膝盖旧伤、肩袖问题、腰椎间盘突出
- 用户说出具体训练目标时 → capture_memory(category="goals", memory_type="fact")
  示例：3个月减10斤、备战马拉松、增肌5kg
- 用户对训练计划给出反馈时 → capture_memory(category="feedback", memory_type="preference")
  示例：上次的计划太累、喜欢居家训练、不喜欢跑步
- 用户做出关键训练决定时 → capture_memory(category="decisions", memory_type="decision")
  示例：决定从全身训练开始、选择了3天分化方案
```

**设计原则：**
- 每条规则对应一个明确的触发场景，不要写"发现重要信息时"这种模糊描述
- category 命名保持一致，同一类信息始终写入同一个文件
- 用 memory_type 区分信息性质：`fact`（客观事实）/ `preference`（偏好）/ `decision`（决定）/ `history`（历史节点）
- tags 用于同一 category 内的细分过滤，如 `["injury", "knee"]`

所有内置示例（`examples/` 目录）均已包含针对各自领域的记忆规则，可直接参考。

### 案例元数据（YAML frontmatter）

每个案例文件头部建议使用结构化 YAML frontmatter，至少包含 `id` / `title` / `uses` / `tags` / `updated_at`：

```markdown
---
id: example_fitness_coach_膝盖疼的上班族
title: 膝盖疼的上班族
uses:
  - knowledge/膝关节损伤训练.md
  - knowledge/新手训练计划.md
tags:
  - fitness-coach
  - example
  - 膝关节损伤训练
  - 新手训练计划
updated_at: 2026-02-26
---

问题描述：32岁上班族，久坐导致膝盖不适...
```

`uses` 负责案例→知识关联；`id` 便于唯一标识与追踪；`updated_at` 建议统一 `YYYY-MM-DD`；`tags` 用于主题检索与筛选。知识文件保持原子化，案例负责组合与落地。`_index.md` 中也会展示 uses 关联，帮助模型快速判断哪些案例和知识相关。

> 当知识文件超过 10 个时，建议在 `_index.md` 中用 `###` 按主题分组，帮助模型快速定位相关条目，避免平铺过长导致漏看。参见 `examples/fitness-coach/knowledge/_index.md`。

可直接参考模板和完整示例：

- `examples/template/` — 空白模板（含 Onboarding 区块示例）
- `examples/fitness-coach/` — 专家顾问（健身教练）
- `examples/sports-nutritionist/` — 继承示例（extends fitness-coach，运动营养师）
- `examples/old-friend/` — 聊天伙伴（远在旧金山的老朋友）
- `examples/language-partner/` — 语言陪练（东京上班族，日语练习）
- `examples/mock-interviewer/` — 模拟面试官（技术面试全流程）
- `examples/user-persona/` — 用户画像（产品验证用的目标用户）
- `examples/brand-support/` — 品牌客服（统一话术和服务标准）
- `examples/novel-character/` — 虚构角色（赛博朋克世界的黑客）
- `examples/historical-figure/` — 历史人物（王阳明，心学对话）
- `examples/project-context/` — 项目上下文（团队架构决策和踩坑记录）
- `examples/past-self/` — 过去的自己（2020年刚毕业的版本）

## 在 AI 工具中集成

> 以下配置中，将 `/path/to/engram-mcp-server` 替换为你的实际项目路径。

### Claude Desktop

在 `claude_desktop_config.json` 中添加：

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

项目级配置（`.mcp.json` 放在项目根目录）或全局配置（`~/.claude/settings.json`）：

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

### Cursor / Windsurf / 其他 MCP 兼容 IDE

在对应 IDE 的 MCP 配置中添加相同的 server 配置即可。具体配置文件位置请参考各 IDE 文档。

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

## 启用自动加载

### 方式 A：手动添加 System Prompt（推荐）

将以下提示词添加到对应 AI 工具的指令文件开头：

| AI 工具 | 指令文件 |
|---------|---------|
| Claude Code | 项目根目录的 `CLAUDE.md` |
| Codex | 项目根目录的 `AGENTS.md` |
| 其他 | 对应工具的 system prompt 配置 |

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

### 方式 B：MCP Prompt

服务暴露 `engram-system-prompt`，支持 MCP Prompt 的客户端可自动注入。

### 方式 C：工具描述引导（零配置）

`list_engrams` / `load_engram` / `read_engram_file` 的工具描述已包含调用流程引导，部分 AI 客户端无需额外配置即可自动触发。

## 调整压缩触发阈值

当 `_index.md` 中的记忆条目总数达到阈值时，`load_engram` 会提示 AI 进行压缩。默认阈值是 **30 条**，可在以下位置修改：

文件：`src/engram_server/loader.py`，常量 `_CONSOLIDATE_HINT_THRESHOLD`

```python
_CONSOLIDATE_HINT_THRESHOLD = 30
```

建议范围：
- `20`：对话频繁，希望记忆保持精简
- `30`：默认，适合大多数场景（约 10-15 次对话触发一次提示）
- `50`：轻度使用，不想频繁压缩

> 这只是一个提示，AI 不会自动压缩，需要主动调用 `consolidate_memory`。

---

## 更新项目

如果使用一键安装（`uvx --from git+...`），清除缓存后重启即可获取最新版本：

```bash
uv cache clean
```

然后**重启 Claude Code**，`uvx` 会自动从 GitHub 拉取最新代码。

> 当前版本会在首次运行时为项目自动创建 `./.claude/engram/`（含 `starter-complete` 与 `starter-template`）。`~/.engram/` 仍可作为跨项目共享目录。

## 多设备同步

### 方案 A：iCloud / Dropbox / OneDrive 同步目录

把 `--packs-dir` 指向云盘同步目录即可，多台设备共用同一份 Engram 数据：

```bash
claude mcp add --scope user engram-server -- \
  uvx --from git+https://github.com/DazhuangJammy/Engram engram-server \
  --packs-dir "$HOME/Library/Mobile Documents/com~apple~CloudDocs/EngramPacks"
```

> Windows 可改成 OneDrive 路径，例如 `C:\\Users\\<你用户名>\\OneDrive\\EngramPacks`。

### 方案 B：Git 同步（把 `~/.engram` 当作仓库）

如果你更偏向可审计变更，可以直接把 `~/.engram` 初始化为 git 仓库并推送到私有远程：

```bash
cd ~/.engram
git init
git remote add origin <your-private-repo-url>
git add .
git commit -m "init engram packs"
git push -u origin main
```

之后在其他设备拉取同仓库，再用同样的 MCP 配置即可。

## 测试

```bash
pytest -q
```

## 路线图

### 已完成（v0.1.0）

- MCP server 核心功能：list / load / read_file / install / init
- 分层懒加载架构：常驻层 + 索引（含内联摘要）+ 按需全文
- 案例→知识关联：结构化 YAML frontmatter（id/title/uses/tags/updated_at）
- 模板系统：`engram-server init` 创建标准结构
- 测试覆盖：loader / server / install
- 11 个完整示例 Engram

### 已完成（v0.2.0）

- 动态记忆：`capture_memory` 对话中自动捕获用户偏好和关键信息
- 写入能力：`write_engram_file` 支持从对话自动打包 Engram
- `load_engram` 自动加载 `memory/_index.md`，无需用户重复说明
- 所有示例 Engram 新增 memory/ 样板

### 已完成（v0.3.0）

- `capture_memory` 新增 `memory_type`（preference/fact/decision/history/general）语义分类
- `capture_memory` 新增 `tags` 参数，支持多标签过滤
- `capture_memory` 新增 `conversation_id` 参数，支持对话作用域绑定
- 节流保护：30 秒内相同内容重复捕获自动跳过
- `load_engram` 动态记忆区块用 `<memory>` 标签包裹，AI 可清晰区分记忆与知识
- 记忆索引格式升级：含类型标注和标签信息

### 已完成（v0.4.0）

- `consolidate_memory` 工具：将原始条目压缩为密集摘要，原始条目归档至 `{category}-archive.md`
- `_index.md` 压缩后只保留一条 `[consolidated]` 条目，context 注入量永远可控
- `load_engram` 当记忆条目 ≥ 30 条时自动提示压缩
- 按记忆类型分层压缩策略（fact 永久保留 / preference 合并 / history 定期归档）
- 示例 Engram 新增 `preferences-archive.md` 展示归档格式

### 已完成（v0.5.0）

- `delete_memory` 工具：按摘要精确删除一条记忆，同时从索引和分类文件中移除
- `correct_memory` 工具：修正已有记忆内容，更新索引和分类文件，支持重新指定类型和标签
- `add_knowledge` 工具：对话中动态向 Engram 添加新知识文件，自动更新知识索引

### 已完成（v0.8.0）

- `engram-server stats`：CLI 统计命令，查看所有 Engram 的记忆/知识/案例数量、类型分布、最近活动
- `engram-server stats --tui`：Rich 渲染版统计面板（彩色表格 + 面板）
- `rich>=13.0` 作为必装依赖，不影响一键安装体验

### 已完成（v0.9.0）

- `engram-server lint`：校验索引一致性、uses 引用、meta 合法性、extends、空知识文件、最小必需文件
- `engram-server stats --json / --csv`：支持机器可读导出格式
- system prompt 与模板规则新增知识提取引导，鼓励 AI 主动沉淀结构化知识

### 已完成（v1.0.0）

- 分组索引：`add_knowledge` 支持二级目录写入与子索引优先更新
- `engram-server init --nested`：可一键生成带分组索引的模板
- 静态 Registry：新增 `registry.json`、`engram-server search`、`install` 名称解析
- README 新增多设备同步章节（云盘 / Git 两种方案）

### 已完成（v1.1.0）

- 傻瓜式自然语言路由：用户只说需求，模型默认自动调用 MCP 工具
- 创建助手双模式：`create_engram_assistant` 支持 `from_conversation` 与 `guided`
- 确认后落盘：`finalize_engram_draft` 自动创建文件并执行 `lint_engrams`
- 自动生成内容透明提示：草稿会标注 auto-filled 字段并提醒“可能不完整”
- 创建阶段不自动写入用户记忆，`memory` 保持空模板

### 已完成（v1.2.0）

- 项目级自动初始化：首次运行自动创建 `./.claude/engram/`
- 自动注入双起始包：`starter-complete`（完整示例）+ `starter-template`（说明模板）
- MCP 工具（`install_engram` / `init_engram` / `finalize_engram_draft`）默认写入当前项目目录

### 计划中

- `engram-server lint --fix`：自动修复孤儿文件、无效索引、空文件
- `search_engram_knowledge(name, query)`：服务端关键词扫描与段落返回
- Engram 社区 registry

## 许可证

MIT
