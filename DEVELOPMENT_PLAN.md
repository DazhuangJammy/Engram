# Engram MCP Server 开发计划

> 更新时间：2026-02-27
> 目标：做一个独立的 MCP server，让任何支持 MCP 的 agent 都能连接，共享记忆包（Engram）。
> 核心理念：记忆决定了 agent 是"每次从零开始的聊天机器人"还是"真正了解你的人"。
> Engram 不限于专家——它可以是顾问、老朋友、聊天伙伴、虚构角色，任何你想让 AI "成为"的身份。

---

## 一、项目定位

这是一个独立项目，不依赖任何特定 agent 框架。

任何支持 MCP 协议的 agent 都能通过 stdio 连接使用，包括：
- Claude Desktop / Claude Code（原生支持 MCP）
- Cursor、Windsurf 等 AI IDE
- 其他任何 MCP 兼容的 agent

### 用户使用流程

```
1. 一键安装：claude mcp add --scope user engram-server -- uvx --from git+https://github.com/DazhuangJammy/Engram engram-server
2. 重启 Claude Code
3. 首次进入某项目时自动创建 `./.claude/engram/`
4. 自动生成两个起始包：`starter-complete`（完整示例）+ `starter-template`（说明模板）
5. 需要更多专家时，再通过 MCP 工具 install_engram 或 CLI install 拉取
6. 在 CLAUDE.md 或 system prompt 加提示词并开始使用
```

---

## 二、核心设计：分层懒加载（非 RAG）

### 为什么不用 RAG

纯 RAG（向量搜索取 top-k 片段）的问题：
- 语义相近 ≠ 逻辑完整，容易丢失上下文关联
- 碎片化检索会丢细节
- 人设和决策流程可能被漏掉
- 需要额外依赖（向量数据库、embedding 模型），增加部署复杂度

### 当前方案：索引驱动的懒加载

Engram 被加载后，内容不是全量塞入，而是分层按需加载：

```
第一层：常驻加载（load_engram 时一次性返回）
  ├── role.md              全文  ← 角色人设（背景 + 沟通风格 + 回答原则）
  ├── workflow.md          全文  ← 工作流程（决策步骤）
  ├── rules.md             全文  ← 运作规则 + 常见错误 + Onboarding 区块
  ├── knowledge/_index.md  ← 知识索引（文件列表 + 一句话描述 + 内联摘要，若 extends 会附加父知识索引）
  ├── examples/_index.md   ← 案例索引（文件列表 + 一句话描述 + uses 关联，建议按主题分组）
  ├── memory/_index.md     ← 动态记忆索引（自动捕获的用户偏好和关键信息）
  └── <packs-dir>/_global/memory/_index.md  ← 全局用户记忆（跨专家共享）

第二层：按需加载（LLM 根据索引摘要判断后主动调用）
  └── read_engram_file(name, path)  ← 读取任意文件（知识、案例、记忆等，含 memory/_index_full.md）

第三层：对话中写入（LLM 识别到重要信息时主动调用）
  └── capture_memory(name, content, category, summary, memory_type, tags, conversation_id, expires, is_global)  ← 捕获用户偏好、关键决定等
```

骨架常驻不丢，知识通过"索引内联摘要 + 全文按需"控制 token 消耗。
不管 Engram 有多大，每次注入的内容都是可控的。

---

## 三、Engram 包结构

### 目录布局

```
<project>/.claude/engram/
├── starter-complete/                    # 自动生成：完整可加载示例
│   ├── meta.json
│   ├── role.md / workflow.md / rules.md
│   │                                  # workflow 内含“可调用 MCP 工具/Skills”的提醒
│   ├── knowledge/
│   │   ├── _index.md
│   │   ├── 目标拆解法.md
│   │   └── 周迭代复盘法.md
│   ├── examples/
│   │   ├── _index.md
│   │   └── 完整案例.md
│   └── memory/
│       └── _index.md
├── starter-template/                    # 自动生成：说明模板
│   ├── meta.json
│   ├── role.md / workflow.md / rules.md
│   │                                  # workflow 内含“可调用 MCP 工具/Skills”的提醒
│   ├── knowledge/...
│   └── examples/
│       ├── 写好案例.md
│       └── 说明样本.md
└── <other-installed-engrams>/

~/.engram/                               # 可选共享/回退目录（--packs-dir）
├── _global/memory/                      # 全局用户记忆（跨专家共享）
└── <shared-engrams>/
```

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

问题描述：32岁上班族，久坐...
```

`uses` 负责案例→知识关联；`id` 便于唯一标识与追踪；`updated_at` 统一 `YYYY-MM-DD`；`tags` 用于主题检索与筛选。知识文件保持原子化，案例负责组合与落地。

### 索引分组（推荐）

当知识文件超过 10 个时，平铺索引会变长，模型扫描效率下降。建议在 `_index.md` 中用 `###` 按主题分组：

```markdown
## 知识索引

### 训练基础
- `knowledge/增肌训练基础.md` - 渐进超负荷、训练量区间与动作编排。
  摘要：主动作维持稳定加重，周训练量落在可恢复区间。

### 损伤与康复
- `knowledge/膝关节损伤训练.md` - 急慢性分流、无痛区间训练和进阶标准。
  摘要：先排除急性损伤，再在无痛区间训练。
```

信息量不变，只是加了分组标题。模型的注意力先锚定到相关分组，再在组内精读。
不做任何服务端过滤，不丢信息。

---

## 四、MCP Server 暴露的工具

| 工具 | 参数 | 说明 |
|------|------|------|
| `ping` | 无 | 连通性检查 |
| `list_engrams` | 无 | 列出所有可用专家（name + description + counts） |
| `get_engram_info` | name | 返回完整 meta.json |
| `load_engram` | name, query | 返回常驻层 + 知识索引（含内联摘要）+ 案例索引（含 uses） |
| `read_engram_file` | name, path | 读取任意文件（案例、知识等） |
| `write_engram_file` | name, path, content, mode | 写入或追加文件到 Engram 包（用于自动打包） |
| `capture_memory` | name, content, category, summary, memory_type, tags, conversation_id, expires, is_global | 对话中捕获用户偏好和关键信息，支持类型标注、标签、对话作用域、TTL过期、全局写入，30秒节流保护 |
| `consolidate_memory` | name, category, consolidated_content, summary | 将某个 category 的原始条目压缩为密集摘要，原始条目归档至 `{category}-archive.md` |
| `delete_memory` | name, category, summary | 按摘要精确删除一条记忆，同时从索引和分类文件中移除 |
| `correct_memory` | name, category, old_summary, new_content, new_summary, memory_type, tags | 修正已有记忆内容，更新索引和分类文件，支持重新指定类型和标签 |
| `add_knowledge` | name, filename, content, summary | 向 Engram 添加新知识文件并自动更新知识索引 |
| `install_engram` | source (git URL / registry 名称) | 从 GitHub URL 或 registry 名称安装 Engram 包 |
| `init_engram` | name, nested | 通过 MCP 初始化新 Engram（可选二级知识索引模板） |
| `lint_engrams` | name? | 通过 MCP 执行一致性校验，返回 errors/warnings |
| `search_engrams` | query | 通过 MCP 搜索 registry 条目 |
| `stats_engrams` | format | 通过 MCP 获取统计，支持 plain/json/csv |
| `create_engram_assistant` | mode, name?, topic?, audience?, style?, constraints?, language?, conversation? | 生成 Engram 草稿（from_conversation / guided） |
| `finalize_engram_draft` | draft_json, name?, nested, confirm | 用户确认后落盘，并自动执行 lint |

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
{<packs-dir>/_global/memory/_index.md 活跃条目，用 <global_memory> 标签包裹}

## 首次引导（可选）
{rules.md 中 ## Onboarding 区块提取内容}
```

> 若 `meta.json` 配置了 `extends`，返回中还会出现"继承知识索引（来自父 Engram）"区块；当前仅支持单层继承。

---

## 五、触发模式

### 自动模式

Agent 看到 `list_engrams` 返回的摘要，判断当前问题是否匹配某个专家，匹配则调用 `load_engram`。

```
用户："我膝盖疼，还能做深蹲吗？"
  → agent 调用 list_engrams() 看到 fitness-coach
  → 判断匹配 → 调用 load_engram("fitness-coach", "膝盖疼深蹲")
  → 看到知识索引中的摘要，判断需要深入
  → 调用 read_engram_file("fitness-coach", "knowledge/膝关节损伤训练.md")
  → 拿到完整知识 → 以专家身份回答
  → 发现用户膝盖有旧伤这个重要信息
  → 调用 capture_memory("fitness-coach", "左膝旧伤...", "user-profile", "膝关节活动度受限")
  → 下次对话自动带入这条记忆
```

### 手动模式

用户用 `@engram-name` 直接指定，agent 跳过判断直接加载。

```
用户："@fitness-coach 帮我制定一个增肌计划"
  → agent 识别 @ 指令 → 直接调用 load_engram("fitness-coach", "增肌计划")
```

> @ 指令的解析依赖 agent 端。MCP server 只提供工具，不处理消息格式。

---

## 六、用户接入方式

### 方式 A：只加提示词（零代码改动）

用户在 agent 的 system prompt 或 CLAUDE.md 里加一段：

```
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

### 方式 B：使用 MCP Prompt（推荐）

server 内置了 `engram-system-prompt` prompt，会动态生成包含所有可用专家的系统提示词。
支持 MCP prompt 的 agent 可以直接注入，无需手动维护。

---

## 七、项目结构

```
engram-mcp-server/
├── pyproject.toml
├── README.md
├── DEVELOPMENT_PLAN.md          # 本文件
├── src/
│   └── engram_server/
│       ├── __init__.py
│       ├── server.py            # MCP server 入口，注册工具 + CLI
│       ├── loader.py            # EngramLoader：扫描、读取、写入、记忆捕获
│       ├── lint.py              # 一致性校验（CLI/MCP 共用）
│       ├── registry.py          # registry 拉取/搜索/名称解析
│       ├── creator.py           # 创建助手：草稿生成与落盘
│       ├── stats.py             # 统计数据收集 + 纯文本/Rich 双模式渲染
│       └── templates/           # engram-server init 模板
│           ├── meta.json
│           ├── role.md
│           ├── workflow.md
│           ├── rules.md
│           ├── knowledge/       # 含 _index.md（内联摘要）
│           └── examples/        # 含 _index.md（含 uses）+ 案例名.md
├── tests/
│   ├── fixtures/
│   │   └── fitness-coach/       # 完整测试用 Engram 包
│   ├── test_loader.py
│   ├── test_server.py
│   ├── test_install.py
│   ├── test_stats.py
│   ├── test_lint.py
│   ├── test_registry.py
│   ├── test_create_assistant.py
│   └── test_auto_routing.py
└── .claude/
    └── engram/
        └── fitness-coach/       # 运行时 Engram 包（供本项目自身使用）
```

---

## 八、依赖

```
mcp              # MCP SDK（Python），提供 server 框架
rich>=13.0       # 终端渲染（stats --tui 面板）
```

零外部依赖（无向量数据库、无 embedding 模型）。
所有检索逻辑基于文件索引 + LLM 自主判断，不需要 chromadb 或 litellm。

---

## 九、分发模型

### MCP Server 分发
- GitHub 开源
- 通过 `uvx --from git+URL` 直接运行，无需发布 PyPI
- 本地运行，不需要云服务器

### Engram 包分发
- 每个 Engram 包是一个独立 GitHub repo
- 首次运行会自动在当前项目创建两个本地起始包（`starter-complete` / `starter-template`）
- 两个起始包都内置了 Skills 调用提醒，用户可直接按 workflow 改造
- 通过 CLI 安装：`engram-server install <git-url|engram-name>`
- 或通过 MCP 工具安装：agent 调用 `install_engram("https://github.com/xxx/fitness-coach")`
- 或手动 clone 到项目 `./.claude/engram/`（也可 clone 到共享目录 `~/.engram/`）

### 用户完整流程

```bash
# 1. 一键安装（全局配置，所有项目可用）
claude mcp add --scope user engram-server -- uvx --from git+https://github.com/DazhuangJammy/Engram engram-server

# 2. 重启 Claude Code

# 3. 首次进入项目会自动创建：
#   ./.claude/engram/starter-complete
#   ./.claude/engram/starter-template
#
# 4. 需要更多 Engram 包时（三选一）
# 方式一：让 agent 调用 install_engram 工具
# 方式二：CLI 安装
#   engram-server install https://github.com/xxx/fitness-coach
#   engram-server install fitness-coach
# 方式三：手动 clone
#   git clone https://github.com/xxx/fitness-coach ./.claude/engram/fitness-coach

# 5. 在 CLAUDE.md 或 system prompt 加提示词
# 6. 开始使用

# 卸载
claude mcp remove --scope user engram-server
```

### CLI 命令

```bash
engram-server serve [--packs-dir DIR]    # 启动 MCP stdio server（默认）
engram-server list [--packs-dir DIR]     # 列出已安装的 Engram
engram-server search <query>             # 搜索 registry
engram-server install <git-url|name>     # 从 git 或 registry 安装 Engram 包
engram-server init <name> [--nested]     # 从模板创建新 Engram 包（可选二级索引）
engram-server lint [name]                # 一致性校验（error=1, warning=0）
engram-server stats [--json|--csv|--tui] # 查看/导出统计
```

---

## 十、当前状态与路线图

### 已完成（v0.1.0）

- MCP server 核心功能：list / load / read_file / install / init
- 分层懒加载架构：常驻层 + 索引（含内联摘要）+ 按需全文
- 案例→知识关联：结构化 YAML frontmatter（id/title/uses/tags/updated_at，索引中内联展示）
- 模板系统：engram-server init 创建标准结构
- 测试覆盖：loader / server / install
- 示例 Engram：fitness-coach（专家顾问）、old-friend（聊天伙伴）

### 已完成（v0.2.0）

- 动态记忆：`capture_memory` 对话中自动捕获用户偏好和关键信息，写入 `memory/` 目录
- 写入能力：`write_engram_file` 支持从对话自动打包 Engram
- `load_engram` 自动加载 `memory/_index.md` 作为常驻层，无需用户重复说明
- 所有 10 个示例 Engram 新增 memory/ 样板（含 _index.md + 分类文件）
- 系统提示词更新：引导 AI 主动捕获记忆
- 测试覆盖：write_file / capture_memory / memory 加载（26 个测试全部通过）

### 已完成（v0.3.0）

- `capture_memory` 新增 `memory_type` 语义分类（preference / fact / decision / history / general）
- `capture_memory` 新增 `tags` 参数，支持多标签过滤
- `capture_memory` 新增 `conversation_id` 参数，支持对话作用域绑定
- 节流保护：30 秒内相同内容重复捕获自动跳过，防止重复写入
- `load_engram` 动态记忆区块用 `<memory>` 标签包裹，AI 可清晰区分记忆与知识
- 记忆索引格式升级：含类型标注 `[type]` 和标签 `[tag1,tag2]`
- 所有示例 Engram 的 memory/ 文件升级为新格式

### 已完成（v0.4.0）

- `consolidate_memory` 工具：将原始条目压缩为密集摘要，原始条目归档至 `{category}-archive.md`
- `_index.md` 压缩后只保留一条 `[consolidated]` 条目，context 注入量永远可控
- `load_engram` 当记忆条目 ≥ 30 条时自动提示压缩
- 按记忆类型分层压缩策略（fact 永久保留 / preference 合并 / history 定期归档）
- `count_memory_entries` 内部方法，统计某 category 的原始条目数
- 示例 Engram 新增 `preferences-archive.md` 展示归档格式

### 已完成（v0.5.0）

- `delete_memory` 工具：按摘要精确删除一条记忆，同时从索引和分类文件中移除
- `correct_memory` 工具：修正已有记忆内容，更新索引和分类文件，支持重新指定类型和标签
- `add_knowledge` 工具：对话中动态向 Engram 添加新知识文件，自动更新知识索引

### 已完成（v0.6.0）

- 所有 11 个示例 Engram 的 `rules.md` 新增 `## 记忆规则` 章节
- 每个 Engram 针对自身领域定义明确的记忆触发规则（触发场景 → category + memory_type + tags）
- `template/rules.md` 新增通用记忆规则模板，供创建新 Engram 时参考
- README 新增"在 rules.md 中定义记忆规则"章节，说明设计原则和最佳实践

### 已完成（v0.7.0）

- **全局用户记忆**：新增 `<packs-dir>/_global/memory/` 跨专家共享目录，`capture_memory` 增加 `is_global=True` 参数，`load_engram` 自动附加全局记忆索引
- **记忆 TTL**：`capture_memory` 增加 `expires` 参数（`YYYY-MM-DD`），按 UTC 日期判断过期，过期条目在加载时自动转存到 `{category}-expired.md` 并隐藏
- **Index 分层**：`_index.md` 只保留最近50条（热层），完整记录写入 `_index_full.md`（冷层），`consolidate_memory` 同步更新两层
- **Engram 继承**：`meta.json` 支持 `extends` 字段，`load_engram` 自动合并父 Engram 的 knowledge index（单层继承）
- **冷启动引导**：`rules.md` 支持 `## Onboarding` 区块，首次使用时自动附加引导提示，完成后写入 `_onboarded` 标记
- **记忆置信度**：`memory_type` 新增 `inferred`（LLM推断）和 `stated`（用户明确表达）两个值
- 所有示例 Engram 的 `rules.md` 新增 `## Onboarding` 区块
- 新增继承示例 Engram：`sports-nutritionist`（extends fitness-coach）

### 已完成（v0.8.0）

- `engram-server stats` CLI 命令：查看所有 Engram 的记忆/知识/案例数量、类型分布、最近活动
- `engram-server stats --tui`：Rich 渲染版统计面板（彩色表格 + 面板）
- `rich>=13.0` 作为必装依赖
- 新增 `src/engram_server/stats.py`（数据类 + gather_stats + render_plain + render_tui）
- 新增 `tests/test_stats.py`（7 个测试用例）

### 已完成（v0.9.0）

- `engram-server lint`：校验 uses 路径、索引一致性、meta 合法性、extends 引用、role.md 最小必需项、空知识文件
- `engram-server stats --json / --csv`：增加机器可读导出
- System prompt / rules 模板 / 示例规则增加知识提取引导

### 已完成（v1.0.0）

- 分组索引：`add_knowledge` 支持 `"子目录/文件名"`，子目录有 `_index.md` 时优先更新子索引
- `engram-server init --nested`：生成二级知识目录模板
- Engram Registry：新增 `registry.json`、`registry.py`、`engram-server search`、`install` 名称解析
- MCP 封装：新增 `init_engram` / `lint_engrams` / `search_engrams` / `stats_engrams`，支持模型直接调用自动执行
- README / README_en 新增多设备同步说明（云盘与 Git 两种方案）

### 使用方式速查（v0.9.0 / v1.0.0 / v1.1.0）

- `engram-server lint --packs-dir ~/.engram`：批量校验全部 Engram
- `engram-server lint <name> --packs-dir ~/.engram`：校验单个 Engram；error 时退出码 1
- `engram-server stats --json|--csv --packs-dir ~/.engram`：导出机器可读统计
- `engram-server search <query> --packs-dir ~/.engram`：从 Registry 搜索可安装 Engram
- `engram-server install <name> --packs-dir ~/.engram`：按名称安装（自动解析 source URL）
- `engram-server init my-expert --nested --packs-dir ~/.engram`：生成二级索引模板
- MCP `add_knowledge(name, filename, content, summary)`：`filename` 可用 `"子目录/文件名"` 写入分组知识
- MCP `create_engram_assistant(mode="from_conversation|guided", ...)`：自然语言创建 Engram 草稿
- MCP `finalize_engram_draft(draft_json, confirm=True, nested=True)`：确认后落盘并自动 lint

### 已完成（v1.1.0）

- 傻瓜式自然语言路由：用户只说需求，模型自动调用 MCP，不让用户手动跑 CLI
- 创建助手双模式：
  - `from_conversation`：把当前对话整理成 Engram 草稿
  - `guided`：模型引导补全字段，支持“你来补全”
- 草稿确认后落盘：`finalize_engram_draft` 自动写文件并执行 lint
- 自动生成内容透明提示：明确“可能不完整，建议人工补充”
- 创建阶段不自动写入用户记忆条目（`memory` 保持空模板）
- from_conversation / guided / 确认&拒绝分支测试已覆盖（含自动 lint）

### 已完成（v1.2.0）

- 项目级自动初始化：首次运行自动创建 `./.claude/engram/`
- 自动注入双起始包：`starter-complete`（完整示例）+ `starter-template`（说明模板）
- MCP 工具（install/init/finalize）默认写入当前项目目录，降低“换项目后没包可用”的门槛

### 远期（P2）

- `engram-server lint --fix`：自动修复孤儿文件、移除无效索引条目、删除空文件
- `search_engram_knowledge(name, query)`：服务端关键词扫描知识文件并返回匹配段落
- Engram 社区 Registry 页面（基于 `registry.json` 生成静态站）
