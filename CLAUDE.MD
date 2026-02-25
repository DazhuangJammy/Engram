你有一个专家记忆系统可用。对话开始时先调用 list_engrams() 查看可用专家。
- 当用户的问题匹配某个专家时，调用 load_engram(name, query) 获取专家知识来回答。
- 发现跨专家通用的用户信息（年龄、城市、职业、语言偏好等基础信息）时，调用 capture_memory(..., is_global=True) 写入全局记忆
- 状态性记忆（"用户正在备考"、"用户目前受伤"等有时效的信息）加expires 参数，如expires="2026-06-01"                                                                                
- load_engram 返回内容中若出现"首次引导"区块，在对话中自然地收集所列信息并capture_memory   
- 对话中发现用户的重要偏好或关键信息时，调用 capture_memory(name, content, category, summary) 记录下来。
- load_engram 后若某个记忆分类条目超过 30 条，主动调用 consolidate_memory 压缩
- 用户也可以用 @专家名 直接指定使用哪个专家。
- 如果调用了 mcp，回复的时候要告诉我调用了什么 mcp 和什么专家