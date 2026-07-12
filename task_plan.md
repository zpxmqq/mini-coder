# D10+D11 任务计划：可观测执行与反馈闭环

## 目标

为每次 Agent 请求建立可追踪的执行身份和完整事件链，使工具调用、错误、权限决策、耗时和最终结果可以通过 `run_id` 查询；用户反馈再关联到具体 Run，用于定位问题环节，而不是自动修改系统权重。

## 当前阶段

D11.1 已完成，下一步进入 D11.2.1：为真实 Agent ReAct 循环接入 LLM 调用 Trace。

## 范围边界

### 本轮要做

```text
RunContext：一次 Agent 请求的身份和总体状态
TraceEvent：一次请求内部按顺序发生的执行事实
MySQL runs / trace_events / feedback 表
Agent 和 Capability 的低侵入埋点
工具错误分类、耗时和恢复结果记录
run_id 查询接口
反馈写入、查询和基础统计
parent_run_id：为 D7 主从 Agent 预留调用树
```

### 本轮不做

```text
不根据少量反馈自动调整路由权重
不记录或暴露模型隐藏推理
不把 Trace、Audit、业务日志混成一张表
不把 SQL 直接堆进 core/agent.py
不做完整可视化管理页面
不提前实现知识可信度校验层
```

## 各阶段

### D11.0：执行领域模型与事件协议

- [x] 定义 `RunContext`、`RunStatus`、`TraceEvent` 和事件类型。
- [x] 明确 `run_id`、`parent_run_id`、`sequence`、`iteration` 的区别。
- [x] 定义 payload 边界；敏感字段脱敏和超长结果截断留到 D11.1 Repository。
- [x] 定义 `TraceRecorder` 接口，使 Agent 只报告事件，不依赖 MySQL。
- [x] 增加 `TraceEmitter`，统一为单个 Run 连续分配 sequence。
- [ ] 用户实现一个小型状态校验函数或测试，由 Codex 检查。（用户决定跳过，不阻塞工程收口。）
- **验收：** 能脱离代码讲清 Run、TraceEvent、Audit、Feedback 四者职责；事件顺序和状态转换有测试。
- **状态：** complete（工程主体和自动测试完成，个人练习跳过）

### D11.1：持久化与 Repository

- [x] 新增 `agent_runs` 和 `trace_events` 表。
- [x] Repository 负责创建 Run、追加事件、结束 Run 和查询完整轨迹。
- [x] 摘要/截断工具参数和结果，敏感字段脱敏。
- [x] 使用真实 MySQL 验证写入、顺序、状态更新和测试数据清理。
- [ ] 用户补一个 Repository 查询或清理测试。（用户决定不亲自写测试，由 Codex 完成集成测试。）
- **验收：** 一次 Run 及其多条事件可以完整往返，失败不会留下不可解释的半状态。
- **状态：** complete

### D11.2：Agent ReAct 埋点

- [ ] 为 `core/agent.py::run()` 注入可选 recorder，不直接导入数据库。
- [ ] 记录 LLM 调用开始/结束、iteration、工具请求、工具执行和最终状态。
- [ ] 分类记录未知工具、参数非法、权限拒绝、执行异常、确认暂停和 MAX_ITER。
- [ ] 记录工具耗时和错误后的后续恢复结果。
- [ ] Audit 增加 run_id 关联，但继续保持安全审计独立。
- [ ] 用户编写一个错误事件顺序测试。
- **验收：** fake LLM 完成成功、工具失败后恢复、权限拒绝和 MAX_ITER 四条链路，Trace 顺序正确。
- **状态：** pending

### D11.3：请求与 Pipeline 生命周期

- [ ] 在任何 Capability 前创建 Run，使安全提前拒绝也可追踪。
- [ ] 将 run context 放入 `PipelineContext.metadata` 或明确字段。
- [ ] 记录 Capability 开始、结束、短路和异常，但控制事件粒度。
- [ ] 请求成功、失败、需要确认时正确更新 Run 状态。
- [ ] HTTP 响应返回 `run_id`。
- [ ] 用户补一个短路请求测试。
- **验收：** Security、Cache short-circuit、普通 Agent、异常四种请求都有完整 Run 生命周期。
- **状态：** pending

### D10.1：反馈模型与接口

- [ ] 新增 feedback 表，并通过外键关联 run_id。
- [ ] 定义 rating、reason_code、comment 和创建时间。
- [ ] 提供写入、查询和必要的修改约束。
- [ ] 拒绝不存在的 run_id 和非法反馈枚举。
- [ ] 用户实现反馈输入校验或对应测试。
- **验收：** 一条反馈可追溯到唯一 Run，不能成为无来源的孤立数据。
- **状态：** pending

### D10.2：反馈与 Trace 联合分析

- [ ] 提供 Run 详情、Trace 列表和 Feedback 查询接口。
- [ ] 按错误类型、工具、Run 状态统计负反馈。
- [ ] 区分路由、参数、工具执行、权限、循环超限和最终答案问题。
- [ ] 不自动改变线上行为，只生成可审查统计。
- [ ] 用户编写一个聚合统计函数或测试。
- **验收：** 给定一条负反馈，可以通过 run_id 找到执行链和可能失败阶段。
- **状态：** pending

### D11.4：验证、文档和收口

- [ ] 运行 D3/D4/D5 回归。
- [ ] 运行真实 MySQL 集成测试。
- [ ] 记录工具成功率、错误分布、平均 iteration 和耗时示例。
- [ ] 更新 AGENTS、CLAUDE、READING_ORDER 和独立 D10+D11 说明文档。
- [ ] 明确仍未实现的命令 timeout、并发写入和 Trace 保留策略。
- **验收：** 自动测试与真实数据库通过；面试话术只描述已经实现的能力。
- **状态：** pending

## 后续已登记架构：Knowledge Integrity Layer

D10+D11 和完整框架完成后，回到 D3/D5，并在 RAG 深化前设计统一的知识可信度层。

共享能力：

```text
Provenance：来源消息、工具事件、文件 hash、文档 chunk
Freshness：时间、git commit、content hash 和失效条件
Contradiction：新旧 claim 冲突检测
Validation：确定性校验优先，可选 LLM judge
Versioning：active / inactive / superseded_by
Policy：verified / unsupported / stale / conflict / quarantined
Correction：重新生成、人工纠正、停用和遗忘
```

复用方式：

```text
Memory：验证长期事实来源、冲突和版本
Context：验证关键约束是否被摘要保留
RAG：验证引用存在、来源可追溯、内容是否过期
```

这不是一个万能真假分类器。共享层只统一证据、状态和策略，各模块仍需要自己的 validator。

## 已延期计划

D6 流式 SSE 延期到内部 AgentEvent/Trace 模型稳定以后。原 D6 分析保留在 Git 历史和对话记录中，后续只需要增加 SSE sink，无需重新设计内部事件格式。

## 已做决策

| 决策 | 理由 |
|---|---|
| D11 先于 D10 | 没有 run_id 和 Trace，反馈只能统计满意度，不能定位问题 |
| Trace 与 Audit 分离 | Trace 服务调试和性能，Audit 服务安全责任 |
| Agent 依赖 Recorder 接口而非 MySQL | 防止执行核心与基础设施耦合 |
| D10 不自动调权重 | 当前样本和离线回归不足，自动修改可能放大噪声 |
| 为 parent_run_id 预留字段 | D7 主从 Agent 可以直接建立调用树 |
| 知识可信度层后置 | 先用 Trace 提供真实工具证据，再深化 Memory/Context/RAG 更合理 |

## 遇到的错误

| 错误 | 尝试次数 | 解决方案 |
|---|---:|---|
| 暂无 | 0 | — |
