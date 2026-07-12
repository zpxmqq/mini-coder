# D10+D11 发现与决策

## 当前需求

- D6 流式输出延期，先深入系统内部执行架构。
- 合并实现 D11 可观测执行与精简 D10 反馈闭环。
- 完整框架结束后，回到 Memory/Context 做知识可信度深化，再做特色 RAG。

## 当前代码事实

- `core/agent.py` 通过 ReAct 循环执行 LLM 和工具，但没有 run_id、统一事件或耗时记录。
- D4 的 `infra/audit.py` 只把安全事件追加到 JSONL；它不是完整 Trace。
- `infra/db.py` 已创建 `agent_runs` 和 `trace_events`；`feedback` 表尚未实现。
- 工具失败、参数错误和权限拒绝会回喂 LLM，但无法查询“之后是否恢复成功”。
- `PENDING_CONFIRMATIONS` 是进程内字典，服务重启后丢失。
- `bash` 当前没有 subprocess timeout，不能声称已经支持命令超时恢复。

## 核心领域模型

```text
Run：一次完整用户请求的总体状态
TraceEvent：Run 内按顺序发生的一件执行事实
AuditEvent：需要长期负责和审计的安全决策
Feedback：用户对某个 Run 的外部评价
```

## 知识可信度层的后续结论

可以设计一个跨 Memory、Context、RAG 复用的 Knowledge Integrity Layer，但不能只调用另一个 LLM 判断真假。

共享骨架应包含：

```text
KnowledgeClaim
EvidenceReference
ValidationResult
FreshnessPolicy
ConflictPolicy
VersionState
```

各模块需要不同的确定性证据：

| 模块 | 优先证据 |
|---|---|
| Memory | 原始 message_id、用户后续明确纠正、工具事实 |
| Context | 被摘要覆盖的 message_id、明确约束清单、Trace 文件状态 |
| RAG | document_id、chunk_id、文档版本、引用内容 |
| 代码事实 | 当前文件内容、content hash、git commit、工具读取结果 |

可观测执行先做的原因是：Trace 会成为后续可信度层的重要证据来源。

## D6 延期发现

- 流式 SSE 是体验和传输能力，不直接提升 Agent 推理正确性。
- 等 TraceEvent 稳定后，D6 可以把同一事件发送给 SSE，而不是再发明一套事件。
- `POST + fetch ReadableStream` 仍是后续前端方案。

## 明确边界

- 本阶段不声称实现自动故障恢复，只记录 Harness 已有的回喂、阻断和确认行为。
- 本阶段不声称实现内容真实性校验。
- 本阶段不将用户反馈直接作用于在线路由权重。
- 不记录 chain-of-thought、API key 或完整敏感工具结果。

## D11.0 实现发现

- `RunStatus.NEEDS_CONFIRMATION` 不是终态：批准后可以恢复到 `RUNNING`。
- `COMPLETED`、`FAILED`、`CANCELLED` 是终态，禁止重新回到运行状态。
- `sequence` 是整个 Run 的事件顺序，`iteration` 只表示 ReAct 轮次。
- `TraceEvent` 使用 frozen dataclass，payload 在初始化和输出时深拷贝，避免嵌套参数被外部修改。
- `TraceRecorder` 是 Protocol；领域层不知道事件最终写 MySQL、内存还是 SSE。
- `TraceEmitter` 负责自动编号，只有 Recorder 成功保存后才推进 sequence。

## D11.1 实现发现

- `MySQLTraceRepository` 同时承担 Run 仓储和 `TraceRecorder` 适配器职责，Agent 无需依赖 MySQL。
- `agent_runs` 保存一次请求的总体状态；`trace_events` 通过外键和 `(run_id, sequence)` 唯一约束保存有序事件链。
- Repository 写入 payload 前递归脱敏敏感字段，并把单个超长字符串限制在 4000 字符以内。
- 数据库保存的是安全处理后的 payload 副本，不修改内存中的 frozen `TraceEvent`。
- MySQL `DATETIME` 不保存时区，因此 Repository 写入前统一转成 UTC 无时区时间，读取后恢复 UTC 时区。
- `create_run`、`record`、`update_run`、`get_run` 和 `get_events` 已通过真实 MySQL 往返测试，测试数据会自动清理。
