# D3 Memory Notes

## 目的

D3 的目标不是把完整聊天历史塞进 prompt，而是把对话中长期有价值的信息提取成可检索、可复用的 typed memory。

链路：

```text
conversation
  -> reflection extracts typed memories
  -> parser validates JSON and fields
  -> exact dedupe before insert
  -> memories table stores content + memory_type
  -> retrieve_memories returns typed results
  -> MemoryCapability groups memories into system context
```

## 已实现

1. `infra/reflection.py`
   - `REFERENCE_PROMPT` 要求 LLM 输出 JSON array。
   - `parse_typed_memories()` 校验 LLM 输出：非法 JSON、非法 type、空 content、`无/null` 都跳过。
   - `reflect()` 只写入通过校验且未重复的 memory。

2. `infra/db.py`
   - `memory_exists(content, memory_type)` 做 exact dedupe。
   - 去重条件是同一个 `memory_type + content` 已存在。

3. `infra/memory.py`
   - `retrieve_memories()` 返回 `list[dict]`，保留 `memory_type` 和 `content`。
   - 当前用 top_k 返回的文本反查原始 memory；第一版假设 content 唯一。

4. `capabilities/builtin.py`
   - `MemoryCapability` 按 `fact / preference / reference` 分组注入 system message。
   - `ReflectionCapability` 用 `context.messages + assistant answer` 做反思输入。

## 测试

- `tests/test_reflection_parser.py`
  - typed memory JSON 解析。
  - 非法 JSON / 非法 type / 空 content 过滤。
  - Markdown fenced JSON 兼容。
  - `reflect()` 跳过已存在 memory。

- `tests/test_d3_memory_flow.py`
  - `retrieve_memories()` 不丢失 `memory_type`。
  - `MemoryCapability` 能按类型注入记忆上下文。

- `tests/test_d3_memory_pipeline.py`
  - 验证 D3 在 capability 生命周期里工作：on_request 注入记忆，on_response 触发 reflection，并把本轮 assistant answer 带入反思消息。

## 当前边界

当前只做 exact dedupe，不做语义合并。

能处理：

```text
用户正在开发 mini-coder 项目
用户正在开发 mini-coder 项目
```

暂不能自动合并：

```text
我个子不低
我身高178
```

原因：语义相似不等于重复，可能是补充、冲突或更具体的新事实。后续更完整的方案是：

```text
embedding 找相似旧记忆
  -> LLM 判断 skip / replace / keep_both
  -> 再决定是否写入或替换
```

第一版选择 exact dedupe，是为了确定性强、实现简单、不误删。