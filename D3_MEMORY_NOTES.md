# D3 Memory Notes

## 目标

D3 的目标是把简单的“记忆注入”升级成一个可解释、可维护的 memory subsystem v1。

它不是把所有历史对话都塞进 prompt，而是拆成两条链路：

```text
写入链路：
conversation
  -> ReflectionCapability 在一轮对话结束后调用 reflect()
  -> LLM 从对话里提取 typed memories
  -> parser 校验 JSON / memory_type / content
  -> exact dedupe 判断是否完全重复
  -> semantic retrieval 找相似旧记忆
  -> LLM 判断 skip / replace / keep_both
  -> db 执行 add_memory() 或 update_memory()

检索链路：
当前用户问题
  -> retrieve_memories() 检索相关记忆
  -> semantic_score / decay_score / usage_boost 多因子排序
  -> MemoryCapability 按类型组织记忆
  -> 注入 system prompt
  -> mark_memories_used() 更新 last_used_at / access_count
```

## 已实现机制

### 1. Typed memory reflection

相关文件：

```text
infra/reflection.py
```

`REFERENCE_PROMPT` 要求 LLM 输出 JSON array。每条记忆包含：

```json
{
  "memory_type": "fact",
  "content": "用户正在开发 mini-coder 项目"
}
```

允许的 `memory_type`：

```text
fact        长期事实
preference  用户偏好
reference   参考背景
```

`parse_typed_memories()` 负责做严格校验：

```text
不是合法 JSON -> 不存
不是 list -> 不存
item 不是 dict -> 跳过
memory_type 不在允许列表 -> 跳过
content 为空 -> 跳过
输出“无 / none / null” -> 不存
```

核心原则：LLM 可以负责总结，但写入数据库前必须经过程序校验。

### 2. LLM JSON 输出清洗

相关文件：

```text
infra/reflection.py
```

`_normalize_llm_json(raw_text)` 用来处理 LLM 常见输出格式：

```text
1. LLM 用 ```json 包住 JSON
2. LLM 在 JSON 前后加解释文字
3. LLM 输出的 JSON array 需要从正文里截取出来
```

它的目标不是修复所有坏 JSON，而是取出最可能合法的 JSON 片段，再交给 `json.loads()`。

如果最后仍然不是合法 JSON，就不写入记忆。

### 3. Exact dedupe

相关文件：

```text
infra/db.py
infra/reflection.py
```

`memory_exists(content, memory_type)` 用来检查完全相同的记忆是否已经存在。

例如：

```text
用户正在开发 mini-coder 项目
用户正在开发 mini-coder 项目
```

如果 `content` 和 `memory_type` 都相同，就不重复写入。

这一步解决的是完全重复，成本低，判断稳定。

### 4. Semantic similar-memory retrieval

相关文件：

```text
infra/memory.py
infra/reflection.py
```

完全相等只能解决字符重复，不能解决语义重复或冲突。

例如：

```text
用户个子不低
用户身高 178cm
```

这两条不完全相等，但语义相关。D3+ 会先用 embedding 检索出相似旧记忆，再交给 LLM 判断是否合并。

### 5. LLM merge decision

相关文件：

```text
infra/reflection.py
```

`decide_memory_merge()` 会把新记忆和相似旧记忆一起发给 LLM，让 LLM 输出结构化决策。

允许的 action：

```text
skip       新记忆没有必要写入
replace    用新记忆覆盖某条旧记忆
keep_both  新旧记忆都保留
```

`parse_merge_decision()` 负责校验 LLM 输出：

```text
不是合法 JSON object -> 默认 keep_both
action 不合法 -> 默认 keep_both
replace 但 target_content 为空 -> 默认 keep_both
```

这里的原则是：复杂语义判断交给 LLM，但真正执行前仍然由程序做格式和边界校验。

### 6. Replace execution

相关文件：

```text
infra/db.py
infra/reflection.py
```

当 LLM 决定 `replace` 时，系统会根据 `target_content` 找到对应旧记忆的 `id`，然后调用：

```python
update_memory(memory_id, content, memory_type, embedding)
```

这样旧记忆会被更新，而不是简单追加一条新记忆。

如果找不到明确目标，系统不会强行覆盖，会退回 `keep_both`。

### 7. Memory lifecycle fields

相关文件：

```text
infra/db.py
```

`memories` 表增加了生命周期字段：

```text
created_at     记忆创建时间
updated_at     记忆最近更新时间
last_used_at   最近一次被检索并注入上下文的时间
access_count   被使用次数
```

数据库迁移辅助函数：

```text
_memory_column_exists()
_add_memory_column_if_missing()
```

这样已有表可以平滑补列，不需要手动删库重建。

### 8. Usage tracking

相关文件：

```text
capabilities/builtin.py
infra/db.py
```

`retrieve_memories()` 返回记忆时会带上 memory id。

`MemoryCapability` 把记忆注入 system prompt 后，会调用：

```python
mark_memories_used(memory_ids)
```

它会更新：

```text
last_used_at = CURRENT_TIMESTAMP
access_count = access_count + 1
```

这样记忆系统不只知道“有什么记忆”，还知道“哪些记忆经常被用到”。

### 9. Decay scoring and rerank

相关文件：

```text
infra/memory.py
```

检索记忆时，不只看语义相似度，还会结合时间衰减和使用次数：

```text
final_score = semantic_score * decay_score * usage_boost
```

不同类型记忆有不同半衰期：

```python
HALF_LIFE_DAYS = {
    "fact": 180,
    "preference": 90,
    "reference": 30,
}
```

含义：

```text
fact        长期事实，衰减慢
preference  用户偏好，中等衰减
reference   参考背景，衰减快
```

使用次数加成：

```text
usage_boost = 1 + 0.05 * log(1 + access_count)
```

这样系统会更倾向于召回相关、较新、经常被用到的记忆。

### 10. Time-aware merge prompt

相关文件：

```text
infra/reflection.py
```

`MERGE_DECISION_PROMPT` 会把旧记忆的时间信息也提供给 LLM：

```text
created_at
updated_at
last_used_at
access_count
```

这样 LLM 判断是否 `replace` 时，可以考虑：

```text
旧记忆是否过时
旧记忆是否经常使用
新记忆是否更具体
新旧记忆是否应该并存
```

## 面试讲法

可以这样介绍 D3：

> 我的记忆系统分成写入和检索两条链路。写入时，一轮对话结束后由 reflection prompt 让 LLM 提取 typed memory，每条记忆包含 content 和 memory_type。程序会先校验 JSON 格式、类型和空内容，再做完全重复检查。对于不完全相等但语义接近的记忆，会用 embedding 找相似旧记忆，再让 LLM 在 skip、replace、keep_both 中做合并决策。检索时，不只按语义相似度排序，还结合 memory_type、时间衰减和 access_count 做多因子重排，并在注入上下文后更新 last_used_at 和 access_count。

## 当前局限

### 1. Context budget 还没做

现在主要按 `k` 控制返回多少条记忆。

后续应该加入：

```text
max_items
max_chars / max_tokens
per_type_limit
```

避免记忆注入挤占主要任务上下文。

### 2. Provenance 还没做

现在记忆只保存内容和类型，还没有保存来源。

后续可以增加：

```text
source_conversation_id
source_message_ids
created_from: reflection / manual / import
```

这样当记忆出错时，可以追溯它来自哪一轮对话。

### 3. Active / inactive versioning 还没做

现在 `replace` 是直接更新旧记忆。

后续可以改成版本化：

```text
status: active / inactive
superseded_by
```

这样旧记忆不会彻底消失，而是被标记为失效。

### 4. Confidence / importance 还没做

后续 reflection 可以让 LLM 同时输出：

```json
{
  "memory_type": "preference",
  "content": "用户更希望先讲清楚原理再改代码",
  "confidence": 0.9,
  "importance": 0.8
}
```

排序时可以扩展成：

```text
final_score = semantic_score * decay_score * usage_boost * confidence * importance
```

### 5. Memory evaluation 还没做

后续需要建立评测集，衡量：

```text
召回准确率
冲突记忆处理效果
过时记忆污染率
prompt token 开销
对任务成功率的影响
```

可以做 ablation：

```text
无 memory
基础 memory
memory + type
memory + type + decay
memory + type + decay + merge
```

## 后续深化方向

### 1. Context budget

理想流程：

```text
retrieve top 20
  -> 按 final_score 排序
  -> 按 max_tokens 截断
  -> 保证每种 memory_type 至少有一定配额
  -> 只对真正注入的 memory 调用 mark_memories_used()
```

### 2. Provenance

每条记忆记录来源：

```text
source_conversation_id
source_message_ids
source_role
created_from
```

这样能回答：

```text
这条记忆为什么存在？
它来自哪次对话？
如果它错了，应该怎么纠正？
```

### 3. Active / inactive versioning

replace 时不直接覆盖，而是：

```text
旧记忆 status = inactive
新记忆 status = active
旧记忆 superseded_by = 新记忆 id
```

这样既能避免过时记忆继续污染上下文，也能保留审计链路。

### 4. Forget API

后续可以提供：

```text
forget_memory(memory_id)
forget_by_type(memory_type)
forget_by_query(query)
```

用于手动删除错误记忆或敏感记忆。

### 5. Memory eval

建立小型评测集：

```text
偏好召回题
事实召回题
冲突更新题
过时记忆题
无关记忆干扰题
```

用指标证明 memory 系统不是“看起来高级”，而是真的提高了任务效果。

## 当前结论

D3+ 之后，mini-coder 的记忆模块已经不只是“把历史塞进 prompt”。

它现在具备：

```text
结构化写入
JSON 校验
类型区分
完全去重
语义相似检索
LLM 合并决策
replace 更新
时间衰减
使用次数加权
上下文注入后使用状态追踪
```

可以暂时把它视为 memory subsystem v1。后续如果继续深化，优先做 context budget、provenance、active/inactive versioning 和 memory evaluation。