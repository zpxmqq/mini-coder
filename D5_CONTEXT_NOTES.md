# D5 Context Governance Notes

## 当前状态

截至 2026-07-12，D5.0 到 D5.7 的代码主体和自动化验证已经完成。

D5 当前解决的是：长对话持续增长时，如何在不直接截断历史的情况下，把较早对话压缩成可恢复任务状态的结构化摘要，并且避免每轮都从头压缩全部历史。

当前实现已经覆盖：

```text
会话消息唯一持久化入口
真实历史与模型输入分离
上下文 token 预算估算
按完整轮次划分压缩窗口
七字段结构化摘要
LLM JSON 语法和业务结构校验
ContextCompressionCapability 接入
MySQL 滚动摘要与消息 ID 游标
摘要请求分块和超长消息切片
失败不推进数据库游标
真实 MySQL 写入、更新和清理测试
```

当前还没有证明：

```text
真实摘要 LLM 的语义保真率
20 轮以上真实对话的压缩率和任务成功率
压缩前后 Agent 完成任务能力没有下降
并发请求同一 conversation 时不会发生摘要覆盖
```

所以准确说法是：**D5 的工程链路已经实现并通过结构与数据库验证，摘要效果评测仍待后续评测阶段完成。**

## D5 的目的

如果每轮都把完整历史发送给模型，输入 token 会随着对话轮数近似线性增长：

```text
第 1 轮：system + 第 1 轮
第 10 轮：system + 第 1~10 轮
第 30 轮：system + 第 1~30 轮
```

达到模型上下文上限后，常见但粗糙的办法是直接删除最早消息。这样可能丢失：

```text
当前任务目标
已经完成的代码修改
用户明确提出的约束
关键文件和函数状态
失败尝试及原因
下一步工作
```

D5 的目标不是保存所有原文，而是保留后续 Agent 继续任务所需的工作状态。

## 与 D3 Memory 的区别

| 维度 | D3 Memory | D5 Context Summary |
|---|---|---|
| 生命周期 | 跨会话长期保存 | 当前 conversation 的工作状态 |
| 主要内容 | 用户事实、偏好、参考背景 | 任务目标、已完成工作、文件状态、失败、待办 |
| 触发方式 | 对话后 Reflection 提取 | 当前模型输入达到 token 阈值 |
| 使用方式 | 根据当前 query 检索少量相关记忆 | 用一份滚动摘要替代较早原始对话 |
| 核心问题 | 以后还需要记住什么 | 当前长任务怎样继续进行 |

两者都会调用 LLM 总结，但保存目的、生命周期和注入方式不同。

## 总体数据流

```text
用户请求
  -> ConversationCapability
       加载带数据库 ID 的历史
       保存当前 user 消息
       构造三套消息视图
  -> ContextCompressionCapability
       inspect_context() 判断是否达到阈值
       split_context_window() 划分旧历史和最近轮次
       读取 previous_summary + compressed_through_message_id
       只选择游标之后的新旧消息
       按 SummaryBudget 分块
       previous_summary + chunk_1 -> summary_1
       summary_1 + chunk_2 -> summary_2
       ...
       全部分块成功后写 MySQL 摘要和新游标
       system prompt + summary + recent turns + current user
  -> MemoryCapability
       检索并注入相关长期记忆
  -> Agent
       使用压缩后的 messages 继续 ReAct 循环
```

## D5.0：统一会话持久化入口

相关文件：

```text
capabilities/builtin.py
server.py
```

原先 `server.py` 和会话模块都可能保存消息，容易出现：

```text
当前 user 被重复写入
第一条 user 没有写入
消息顺序混乱
```

现在由 `ConversationCapability` 统一负责：

```text
on_request  保存当前 user
on_response 保存最终 assistant
```

`server.py` 只负责编排，不再重复持久化消息。

## D5.1：分离三套消息视图

当前系统中的三套消息不能混为一谈：

### `context.messages`

真正准备发送给主 Agent 的输入，可能包含：

```text
system prompt
上下文摘要
长期记忆
user / assistant 历史
```

它可以被 Capability 重建和临时注入。

### `context.conversation_messages`

干净的 user / assistant 原始历史，不带摘要、记忆和数据库 ID。

用于：

```text
Reflection
原始会话语义
避免临时 system 注入污染长期记忆
```

### `context.metadata["conversation_records"]`

供 D5 内部使用的数据库消息记录：

```python
{
    "id": 41,
    "role": "user",
    "content": "继续实现 D5.7",
}
```

消息 ID 不能直接发送给模型，但 D5 需要它判断哪些消息已经压缩。

## D5.2：上下文预算感知

相关文件：

```text
infra/context_manager.py
tests/test_d5_context_budget.py
```

`ContextBudget` 保存：

```text
model_context_limit
reserved_output_tokens
compression_ratio
```

`inspect_context()` 分别估算：

```text
messages token
tool schemas token
总 token
可用输入 token
压缩触发阈值
```

当前 token 计算是中英文启发式估算，不是模型官方 tokenizer：

```text
ASCII 字符约 4 个字符 / token
非 ASCII 字符约 1.5 个字符 / token
每条消息增加固定协议开销
```

优点是依赖少、速度快；缺点是只能用于提前预警，不能保证与服务端计费完全一致。

## D5.3：按对话轮次切分窗口

相关函数：

```text
_group_conversation_turns()
_flatten_turns()
split_context_window()
```

一问一答作为一个完整轮次：

```text
[
    [user1, assistant1],
    [user2, assistant2],
    [user3, assistant3],
]
```

窗口输出：

```text
compressible_messages  较早轮次，允许压缩
recent_messages        最近 N 个完整轮次，保留原文
current_user_message   当前请求，始终保留原文
```

这样不会简单地从消息列表中间切断最近一轮问答。

## D5.4：七字段结构化摘要

`ContextSummary` 包含：

```text
task_goal       当前任务目标
completed_work  已完成工作
key_decisions   关键设计决策
file_states     文件、函数和代码状态
constraints     用户明确约束
failures        失败尝试、错误及原因
pending_work    待完成工作
```

与自由文本摘要相比，结构化摘要更容易：

```text
检查字段是否遗漏
恢复任务状态
在 Prompt 中稳定注入
后续做压缩质量评测
```

### 两层校验

`infra/llm_output.py` 负责通用 JSON 语法层：

```text
移除 Markdown code fence
截取 JSON 对象或数组
json.loads()
检查顶层是 dict 还是 list
```

`parse_context_summary()` 负责 D5 业务层：

```text
必须且只能有七个字段
task_goal 必须是字符串
其他字段必须是 list[str]
拒绝空列表项和非法占位符
拒绝七个字段全部为空
```

同一个通用 JSON 模块也被 D3 Reflection 复用，但 D3 和 D5 的业务校验仍然分开。

## D5.5：接入 Capability Pipeline

Pipeline 顺序：

```text
Security
Conversation
ContextCompression
Memory
Cache
Reflection
```

必须先由 Conversation 加载原始历史和消息 ID，ContextCompression 才能切分窗口。

Memory 放在压缩之后，避免长期记忆参与历史摘要，也避免压缩器把临时检索结果写进任务状态。

压缩不是在旧 messages 后面追加摘要，而是重建主模型输入：

```text
旧方式：system + 全部旧历史 + summary
正确方式：system + summary + recent + current
```

只有替换掉较早历史，token 才会真正下降。

## D5.6：MySQL 持久化滚动摘要

新增表：

```text
conversation_context_summaries
```

主要字段：

```text
conversation_id
summary_json
compressed_through_message_id
source_token_count
summary_token_count
version
updated_at
```

`compressed_through_message_id` 是稳定边界。例如：

```text
旧摘要覆盖消息 1~40
当前 compressible_messages 是 1~42
本次只发送消息 41~42 给摘要 LLM
成功后把边界更新为 42
```

不用“已压缩消息数量”作为边界，因为消息删除、插入或并发写入后，数量不如数据库主键稳定。

摘要与游标通过同一次 `upsert` 和 `commit` 更新，避免出现：

```text
摘要只覆盖到 40
数据库游标却已经推进到 42
```

### D5.6 失败策略

第一次生成摘要失败：

```text
不写数据库
不替换当前原始上下文
```

已有旧摘要，本次增量合并失败：

```text
继续注入旧摘要
旧游标之后的消息全部保留原文
不推进数据库游标
```

因此失败会增加 token，但不会静默丢失尚未压缩的信息。

## D5.7：摘要请求分块与滚动合并

主 Agent 的上下文需要预算，摘要 LLM 自己也需要独立预算。

`SummaryBudget` 默认值：

```text
模型上下文上限  64000
预留输出         8000
安全余量         2000
最大输入        54000
```

`take_summary_chunk()` 的拆分顺序：

```text
1. 优先把完整对话轮次放入同一块
2. 单个轮次过长时，允许按消息边界拆分
3. 单条消息仍然过长时，对 content 做二分查找切片
4. 每次构造完整摘要请求后重新估算 token
```

滚动合并过程：

```text
chunk_1 -> summary_1
summary_1 + chunk_2 -> summary_2
summary_2 + chunk_3 -> summary_3
```

每次生成的新摘要都会成为下一块的 `previous_summary`。

任一块发生下面情况时，整体返回失败：

```text
LLM 调用抛异常
输出不是合法 JSON
七字段业务校验失败
摘要本身超过 reserved_output_tokens
固定 Prompt 加旧摘要已经没有空间容纳新消息
```

中间摘要只存在于内存。全部块成功后，Capability 才把最终摘要和新游标写入数据库，因此数据库不会保存半成品。

## 完整示例

假设：

```text
数据库有消息 1~50
持久化摘要覆盖 1~40
本轮窗口允许压缩到 42
最近原文是 43~50
```

本轮摘要 LLM 只收到：

```text
previous_summary（覆盖 1~40）
new_messages（41~42）
```

成功后：

```text
新摘要覆盖 1~42
compressed_through_message_id = 42
主 Agent 输入 = system + 新摘要 + 原文 43~50
```

下一轮如果没有新消息进入压缩窗口：

```text
直接复用旧摘要
不调用摘要 LLM
不更新数据库版本
```

## 验证结果

已通过：

```text
tests/test_d5_context_budget.py
tests/test_d5_context_window.py
tests/test_d5_context_summary.py
tests/test_d5_context_flow.py
tests/test_d5_context_compression.py
tests/test_d5_context_db.py
tests/test_llm_output.py
```

`test_d5_context_compression.py` 覆盖：

```text
完整轮次优先分块
超长单消息切片后内容不丢失
每次摘要请求不超过输入预算
后一块收到前一块摘要
任意分块失败时整体失败
没有增量时不调用 LLM
输出摘要超过预算时拒绝
只处理数据库游标后的消息
失败时不推进游标并保留原文
```

`test_d5_context_db.py` 使用真实 MySQL 8.4 验证：

```text
摘要第一次 INSERT
摘要和游标读取
第二次 upsert
version 从 1 增长到 2
token 指标更新
测试会话最终清理且残留为 0
```

D3、D4 和 Reflection 回归也已通过。

## 当前限制与后续深化

### 1. 摘要语义质量尚未量化

当前测试证明格式、边界和失败策略正确，但模拟 LLM 不能证明真实模型没有遗漏约束。

后续需要构造带标准答案的长对话 case，评估：

```text
关键约束保留率
文件状态保留率
失败原因保留率
压缩前后任务成功率
压缩率
额外摘要调用延迟和 token 成本
```

### 2. 没有确定性的关键文件追踪

当前 `file_states` 由 LLM 从 user / assistant 对话中提取，并没有直接读取真实 tool call 记录。

因此“Agent 调过哪些文件”目前不是确定性数据。后续可以由 Agent Harness 记录：

```text
read_file / write_file / edit_file 的 path
文件内容 hash 或最后修改时间
本轮修改结果
```

再把这些确定性状态交给摘要器，而不是完全依赖 LLM 回忆。

### 3. 主 Agent 压缩后没有再次强制预算校验

如果当前用户单条输入本身就超过模型上限，压缩旧历史也解决不了。

后续可以在重建 `context.messages` 后再次调用 `inspect_context()`：

```text
仍超限 -> 拒绝请求或截断超长工具输出
```

### 4. 同一会话的并发更新没有锁

两个请求同时读取同一个 version 后都生成摘要，后写入的请求可能覆盖先写入结果。

后续可以使用：

```text
乐观锁：UPDATE ... WHERE version = old_version
会话级 Redis 锁
同一 conversation 串行队列
```

### 5. MySQL 故障没有降级

当前摘要状态读取或写入失败会继续抛出异常。生产化时需要明确决定：

```text
读取失败 -> 暂时使用原始历史
写入失败 -> 不推进边界，记录告警
```

## 面试介绍版本

> 我的上下文治理不是达到上限后直接截断，而是先估算 messages 和 tool schemas 的 token，超过阈值后按完整对话轮次切分窗口，最近几轮和当前请求保留原文，较早历史交给辅助 LLM 生成七字段结构化任务摘要。摘要会和覆盖到的最后一条 message_id 一起持久化到 MySQL，后续只把旧摘要和游标后的增量消息做滚动合并，避免每轮从头总结。摘要输入本身也有独立预算，过长时优先按轮次分块，单条消息过长再切片。任何一块校验失败都不会推进数据库游标，而是保留旧摘要和未压缩原文。当前格式、分块、游标和真实 MySQL 更新已经通过测试，语义保真率和压缩前后任务成功率还需要在评测阶段量化。

## 用户应能讲清的检查点

```text
为什么 context.messages 和 conversation_messages 不能共用一个列表
为什么压缩必须替换旧历史，而不是在后面追加摘要
为什么要保留最近完整轮次和当前 user 原文
为什么摘要要有七个固定字段
为什么 JSON 语法校验和 D5 业务校验要分开
为什么滚动摘要需要 message_id 游标
为什么所有分块成功后才能推进游标
一块摘要失败后系统怎样保证未压缩信息不丢失
D3 Memory 和 D5 Context Summary 分别解决什么问题
当前 D5 已证明什么、还没有证明什么
```
