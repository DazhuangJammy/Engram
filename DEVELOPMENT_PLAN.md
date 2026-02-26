# Engram MCP Server 开发计划

> 更新时间：2026-02-25
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
3. 安装 Engram 包（通过 MCP 工具 install_engram 或 CLI engram-server install <git-url>）
4. 在 CLAUDE.md 或 system prompt 加提示词
5. 开始使用
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
~/.engram/
├── fitness-coach/
│   ├── meta.json                        # 元信息
│   ├── role.md                          # 角色（常驻）
│   ├── workflow.md                      # 工作流程（常驻）
│   ├── rules.md                         # 规则（常驻）
│   ├── knowledge/                       # 知识层（按需加载）
│   │   ├── _index.md                    # 知识索引
│   │   ├── 增肌训练基础.md               # 完整知识
│   │   └── ...
│   ├── examples/                        # 案例层（按需加载）
│   │   ├── _index.md                    # 案例索引
│   │   ├── 膝盖疼的上班族.md             # 案例（含 uses frontmatter）
│   │   └── ...
│   └── memory/                          # 动态记忆（对话中自动生成）
│       ├── _index.md                    # 记忆热层索引（最近50条，自动维护）
│       ├── _index_full.md               # 记忆完整索引（全量，按需加载）
│       ├── user-profile.md              # 用户档案
│       └── preferences.md              # 用户偏好
├── _global/
│   └── memory/                          # 全局用户记忆（跨专家共享）
│       ├── _index.md
│       ├── _index_full.md
│       └── user-profile.md
└── contract-lawyer/
    └── ...
```

### 案例→知识关联（uses frontmatter）

每个案例文件头部用 YAML frontmatter 标注引用的知识文件：

```markdown
---
uses:
  - knowledge/膝关节损伤训练.md
  - knowledge/新手训练计划.md
---

问题描述：32岁上班族，久坐...
```

一个案例可引用多个知识文件，天然支持"混合知识案例"。
知识文件保持原子化，案例负责组合与落地。

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
| `install_engram` | source (git URL) | 从 GitHub 安装 Engram 包 |

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
你有一个专家记忆系统可用。对话开始时先调用 list_engrams() 查看可用专家。
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
│   └── test_install.py
└── .claude/
    └── engram/
        └── fitness-coach/       # 运行时 Engram 包（供本项目自身使用）
```

---

## 八、依赖

```
mcp              # MCP SDK（Python），提供 server 框架
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
- 通过 CLI 安装：`engram-server install <git-url>`
- 或通过 MCP 工具安装：agent 调用 `install_engram("https://github.com/xxx/fitness-coach")`
- 或手动 clone 到 `~/.engram/` 目录

### 用户完整流程

```bash
# 1. 一键安装（全局配置，所有项目可用）
claude mcp add --scope user engram-server -- uvx --from git+https://github.com/DazhuangJammy/Engram engram-server

# 2. 重启 Claude Code

# 3. 安装 Engram 包（三选一）
# 方式一：让 agent 调用 install_engram 工具
# 方式二：CLI 安装
#   engram-server install https://github.com/xxx/fitness-coach
# 方式三：手动 clone
#   git clone https://github.com/xxx/fitness-coach ~/.engram/fitness-coach

# 4. 在 CLAUDE.md 或 system prompt 加提示词
# 5. 开始使用

# 卸载
claude mcp remove --scope user engram-server
```

### CLI 命令

```bash
engram-server serve [--packs-dir DIR]   # 启动 MCP stdio server（默认）
engram-server list [--packs-dir DIR]    # 列出已安装的 Engram
engram-server install <git-url>         # 从 git 安装 Engram 包
engram-server init <name>               # 从模板创建新 Engram 包
```

---

## 十、当前状态与路线图

### 已完成（v0.1.0）

- MCP server 核心功能：list / load / read_file / install / init
- 分层懒加载架构：常驻层 + 索引（含内联摘要）+ 按需全文
- 案例→知识关联：uses frontmatter（索引中内联展示）
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

### 下一阶段（P1）

- `engram-server lint`：校验 uses 路径有效性、索引一致性
- 章节化知识目录：大文档自动切分为子目录 + 章节索引

### 远期（P2）

- `search_engram_knowledge(name, query)`：服务端 query-aware 精读
- 构建期多模型流水线：小模型做抽取，大模型做润色
- Engram 社区 registry
