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
- MCP 工具：`ping`、`list_engrams`、`get_engram_info`、`load_engram`、`read_engram_file`、`write_engram_file`、`capture_memory`、`consolidate_memory`、`delete_memory`、`correct_memory`、`add_knowledge`、`install_engram`
- 索引驱动加载：
  - `load_engram` 返回角色/工作流程/规则 + 知识索引（含内联摘要）+ 案例索引（含 uses）+ 动态记忆索引 + 全局用户记忆
  - `read_engram_file` 按路径按需读取知识或案例全文
- 动态记忆：对话中自动捕获用户偏好和关键信息，下次加载时自动带入
- 全局用户记忆：跨专家共享的用户基础信息（年龄、城市等），所有 Engram 加载时自动附加
- 记忆 TTL：支持 `expires` 字段，到期记忆自动归档到 `{category}-expired.md` 并隐藏
- Index 分层：`_index.md` 只保留最近50条（热层），完整记录写入 `_index_full.md`（冷层）
- Engram 继承：`meta.json` 支持 `extends` 字段，自动合并父 Engram 的 knowledge index
- 冷启动引导：`rules.md` 支持 `## Onboarding` 区块，首次使用时自动触发信息收集
- CLI 命令：`serve` / `list` / `install` / `init` / `stats`
- 统计面板：`engram-server stats` 查看记忆统计，`--tui` 启用 rich 渲染

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
- 不往你的项目里塞任何代码
- 每次 Claude Code 启动时，自动从 GitHub 拉取最新版本运行
- 专家包数据默认存放在 `~/.engram`

安装完成后**重启 Claude Code**，即可开始使用。

### 一键卸载

```bash
claude mcp remove --scope user engram-server
```

> 卸载只移除 MCP 配置，不会删除你的 Engram 数据（`~/.engram/`）。如需彻底清理数据，手动执行 `rm -rf ~/.engram`。

## 快速开始

### 添加 System Prompt（推荐）

在项目的 `CLAUDE.md`（Claude Code）或 `AGENTS.md`（Codex）文件开头加入以下提示词，让 AI 自动发现和使用 Engram：

```text
你有一个专家记忆系统可用。对话开始时先调用 engram-server 这个 mcp 中的list_engrams() 查看可用专家。
- 当用户的问题匹配某个专家时，调用 load_engram(name, query) 获取专家知识来回答。
- 发现跨专家通用的用户信息（年龄、城市、职业、语言偏好等基础信息）时，调用 capture_memory(..., is_global=True) 写入全局记忆
- 状态性记忆（"用户正在备考"、"用户目前受伤"等有时效的信息）加 expires 参数，expires 使用 YYYY-MM-DD（如 2026-06-01），到期后会归档并从加载结果隐藏。
- load_engram 返回内容中若出现"首次引导"区块，在对话中自然地收集所列信息并 capture_memory
- 对话中发现用户的重要偏好或关键信息时，调用 capture_memory(name, content, category, summary, memory_type, tags, conversation_id, expires, is_global) 记录下来。记录时可用 memory_type 标注语义类型（preference/fact/decision/history/general/inferred/stated），用 tags 打标签便于过滤。
- load_engram 返回结果中若出现「💡 当前共 N 条记忆」提示（动态记忆热层总条目 ≥ 30），先调用 read_engram_file(name, "memory/{category}.md") 读取条目较多的分类原始内容，再调用 consolidate_memory(name, category, consolidated_content, summary) 压缩（须自行合成 consolidated_content 传入，仅支持专家记忆，不支持全局记忆）
- 用户也可以用 @专家名 直接指定使用哪个专家。
- 如果调用了 mcp，回复的时候要告诉我调用了什么 mcp 和什么专家
- load_engram 返回知识索引后，若索引摘要不足以回答问题，调用 read_engram_file(name, "knowledge/xxx.md") 读取具体文件全文再回答
- 用户要求删除某条记忆时，调用 delete_memory(name, category, summary)（仅支持专家记忆，不支持全局记忆）
- 用户纠正某条记忆内容时，调用 correct_memory(name, category, old_summary, new_content, new_summary, memory_type, tags)（仅支持专家记忆，不支持全局记忆）
- 对话中产生了值得长期保存的新知识（非用户个人信息），调用 add_knowledge(name, filename, content, summary) 写入知识库
- 当记忆较多或要查历史时，可 read_engram_file(name, "memory/_index_full.md") 查看完整记忆冷层。
- load_engram 返回内容含「继承知识索引」区块时，知识来自父专家，可调用 read_engram_file(父专家名, "knowledge/xxx.md") 读取具体父专家知识文件
- 用户询问某个 engram 的详细信息时，调用 get_engram_info(name)
- 用户要安装新 engram 时，调用 install_engram(source)（source 为 git URL）
- 需要直接修改 engram 的 role.md / workflow.md / rules.md 等非知识库文件时，调用 write_engram_file(name, path, content, mode)
- 用户询问记忆统计或想了解当前有多少记忆时，建议用户在终端运行 `uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats` 或 `uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats --tui`
```

### 4. 重启 AI 客户端，开始使用

## CLI 用法

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

从 git 安装 Engram：

```bash
engram-server install <git-url> --packs-dir ~/.engram
```

初始化一个新 Engram 模板：

```bash
engram-server init my-expert --packs-dir ~/.engram
```

查看记忆统计（纯文本）：

```bash
uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats
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
| `install_engram` | `source` | 从 git URL 安装 Engram 包 |

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
你有一个专家记忆系统可用。对话开始时先调用 engram-server 这个 mcp 中的list_engrams() 查看可用专家。
- 当用户的问题匹配某个专家时，调用 load_engram(name, query) 获取专家知识来回答。
- 发现跨专家通用的用户信息（年龄、城市、职业、语言偏好等基础信息）时，调用 capture_memory(..., is_global=True) 写入全局记忆
- 状态性记忆（"用户正在备考"、"用户目前受伤"等有时效的信息）加 expires 参数，expires 使用 YYYY-MM-DD（如 2026-06-01），到期后会归档并从加载结果隐藏。
- load_engram 返回内容中若出现"首次引导"区块，在对话中自然地收集所列信息并 capture_memory
- 对话中发现用户的重要偏好或关键信息时，调用 capture_memory(name, content, category, summary, memory_type, tags, conversation_id, expires, is_global) 记录下来。记录时可用 memory_type 标注语义类型（preference/fact/decision/history/general/inferred/stated），用 tags 打标签便于过滤。
- load_engram 返回结果中若出现「💡 当前共 N 条记忆」提示（动态记忆热层总条目 ≥ 30），先调用 read_engram_file(name, "memory/{category}.md") 读取条目较多的分类原始内容，再调用 consolidate_memory(name, category, consolidated_content, summary) 压缩（须自行合成 consolidated_content 传入，仅支持专家记忆，不支持全局记忆）
- 用户也可以用 @专家名 直接指定使用哪个专家。
- 如果调用了 mcp，回复的时候要告诉我调用了什么 mcp 和什么专家
- load_engram 返回知识索引后，若索引摘要不足以回答问题，调用 read_engram_file(name, "knowledge/xxx.md") 读取具体文件全文再回答
- 用户要求删除某条记忆时，调用 delete_memory(name, category, summary)（仅支持专家记忆，不支持全局记忆）
- 用户纠正某条记忆内容时，调用 correct_memory(name, category, old_summary, new_content, new_summary, memory_type, tags)（仅支持专家记忆，不支持全局记忆）
- 对话中产生了值得长期保存的新知识（非用户个人信息），调用 add_knowledge(name, filename, content, summary) 写入知识库
- 当记忆较多或要查历史时，可 read_engram_file(name, "memory/_index_full.md") 查看完整记忆冷层。
- load_engram 返回内容含「继承知识索引」区块时，知识来自父专家，可调用 read_engram_file(父专家名, "knowledge/xxx.md") 读取具体父专家知识文件
- 用户询问某个 engram 的详细信息时，调用 get_engram_info(name)
- 用户要安装新 engram 时，调用 install_engram(source)（source 为 git URL）
- 需要直接修改 engram 的 role.md / workflow.md / rules.md 等非知识库文件时，调用 write_engram_file(name, path, content, mode)
- 用户询问记忆统计或想了解当前有多少记忆时，建议用户在终端运行 `uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats` 或 `uvx --from git+https://github.com/DazhuangJammy/Engram engram-server stats --tui`
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

> 你的 Engram 数据存放在 `~/.engram/` 目录，与项目代码完全分离，更新不会影响已有数据。

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

### 计划中

- `engram-server lint`：校验 uses 路径有效性、索引一致性
- 章节化知识目录：大文档自动切分为子目录 + 章节索引
- Engram 社区 registry

## 许可证

MIT
