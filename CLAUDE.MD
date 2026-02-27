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
