# Engram MCP Server

RAG 能检索知识，但没有人设、没有决策流程——Engram 解决这个问题。

给 AI 注入可切换的专家记忆——不只是知识检索，而是**"谁 + 知道什么 + 怎么思考"**的完整人设。一套 Markdown 文件就能让任何 AI 获得专家级记忆，零向量依赖，即插即用。

```
Engram  = 专家是谁 + 知道什么 + 怎么思考
Tools   = 具体能做什么操作
```

人工策展 + 模型自主检索，在小规模高质量知识场景下比 RAG 更精准——不是因为技术更强，而是因为人工策展的质量天然高于自动切分。把 memory 分享给别人，对方的 AI 立刻成为同一个专家。未来大家共享的不是 Skills，而是 Memory。

支持所有 MCP 兼容客户端：Claude Desktop / Claude Code、Cursor、Windsurf、Codex 等。

## 功能特性

- 零向量依赖：不使用 chromadb / litellm，只依赖 `mcp`
- MCP 工具：`ping`、`list_engrams`、`get_engram_info`、`load_engram`、`read_engram_file`、`install_engram`
- 索引驱动加载：
  - `load_engram` 返回角色/工作流程/规则 + 知识索引（含内联摘要）+ 案例索引（含 uses）
  - `read_engram_file` 按路径按需读取知识或案例全文
- CLI 命令：`serve` / `list` / `install` / `init`

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
  ├── rules.md             全文  ← 运作规则 + 常见错误
  ├── knowledge/_index.md  ← 知识索引（文件列表 + 一句话描述 + 内联摘要）
  └── examples/_index.md   ← 案例索引（文件列表 + 一句话描述 + uses 关联）

第二层：按需加载（LLM 根据索引摘要判断后主动调用）
  └── read_engram_file(name, path)  ← 读取任意知识或案例文件
```

骨架常驻不丢，知识通过"索引内联摘要 + 全文按需"控制 token 消耗。不管 Engram 有多大，每次注入的内容都是可控的。

## 安装

推荐使用 [uv](https://docs.astral.sh/uv/)（自动管理 Python 版本和依赖）：

```bash
# 安装 uv（如果还没有）
# macOS / Linux
brew install uv
# 或
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆项目
git clone <repo-url> engram-mcp-server
cd engram-mcp-server

# 安装（uv 会自动下载合适的 Python 版本）
uv pip install -e .
```

<details>
<summary>其他安装方式</summary>

**pip 安装（需要 Python >= 3.10）：**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

</details>

## 快速开始

1. 安装（见上方）

2. 在项目根目录创建 `.mcp.json`（以 Claude Code 为例）：
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
   > 将 `/path/to/engram-mcp-server` 替换为你的实际项目路径。

3. 放置 Engram 包到 `~/.engram/<name>/`，重启 Claude Code 即可使用。

## CLI 用法

启动 MCP stdio 服务（默认命令）：

```bash
engram-server serve --packs-dir ~/.claude/engram
```

等价写法：

```bash
engram-server --packs-dir ~/.claude/engram
```

列出已安装 Engram：

```bash
engram-server list --packs-dir ~/.claude/engram
```

从 git 安装 Engram：

```bash
engram-server install <git-url> --packs-dir ~/.claude/engram
```

初始化一个新 Engram 模板：

```bash
engram-server init my-expert --packs-dir ~/.claude/engram
```

## MCP 工具列表

| 工具 | 参数 | 说明 |
|------|------|------|
| `ping` | 无 | 连通性测试，返回 `pong` |
| `list_engrams` | 无 | 列出可用 Engram（含描述与文件统计） |
| `get_engram_info` | `name` | 获取完整 `meta.json` |
| `load_engram` | `name`, `query` | 加载角色/工作流程/规则全文 + 知识索引（含内联摘要）+ 案例索引（含 uses） |
| `read_engram_file` | `name`, `path` | 按需读取单个文件（含路径越界保护） |
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
```

## 工作流程：Agent 如何使用 Engram

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
  meta.json
  role.md
  workflow.md
  rules.md
  knowledge/
    _index.md
    <topic>.md
  examples/           # 可选
    _index.md
    <case>.md
```

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
- `rules.md`：运作规则、常见错误
- `knowledge/_index.md` + 主题文件：知识索引（含内联摘要）+ 细节
- `examples/_index.md` + 案例文件：案例索引（含 uses 关联）+ 复盘

### 案例→知识关联（uses frontmatter）

每个案例文件头部用 YAML frontmatter 标注引用的知识文件：

```markdown
---
uses:
  - knowledge/膝关节损伤训练.md
  - knowledge/新手训练计划.md
---

问题描述：32岁上班族，久坐导致膝盖不适...
```

一个案例可引用多个知识文件，天然支持"混合知识案例"。知识文件保持原子化，案例负责组合与落地。`_index.md` 中也会展示 uses 关联，帮助模型快速判断哪些案例和知识相关。

> 当知识文件超过 10 个时，建议在 `_index.md` 中用 `###` 按主题分组，帮助模型快速定位相关条目，避免平铺过长导致漏看。参见 `examples/fitness-coach/knowledge/_index.md`。

可直接参考模板和完整示例：

- `examples/template/` — 空白模板
- `examples/fitness-coach/` — 专家顾问（健身教练）
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

## 启用自动加载（三种方式）

### 方式 A：MCP Prompt（推荐）

服务暴露 `engram-system-prompt`，支持 MCP Prompt 的客户端可自动注入。

### 方式 B：工具描述引导（零配置）

`list_engrams` / `load_engram` / `read_engram_file` 的描述已包含调用流程。

### 方式 C：手动添加 System Prompt

```text
你有一个专家记忆系统可用。对话开始时先调用 list_engrams() 查看可用专家。
当用户的问题匹配某个专家时，调用 load_engram(name, query) 加载常驻层和索引。
查看知识索引中的摘要，需要细节时调用 read_engram_file(name, path) 读取完整知识或案例。
用户也可以用 @专家名 直接指定使用哪个专家。
```

## 测试

```bash
pytest -q
```

## 路线图

### 已完成（v0.1.0）

- MCP server 核心功能：list / load / read_file / install / init
- 分层懒加载架构：常驻层 + 索引（含内联摘要）+ 按需全文
- 案例→知识关联：uses frontmatter
- 模板系统：`engram-server init` 创建标准结构
- 测试覆盖：loader / server / install
- 11 个完整示例 Engram

### 计划中

- `engram-server lint`：校验 uses 路径有效性、索引一致性
- 章节化知识目录：大文档自动切分为子目录 + 章节索引
- Engram 社区 registry

## 许可证

MIT
