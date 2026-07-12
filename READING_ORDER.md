# 当前 D0~D5 架构读取顺序

## 第一天：看懂 Capability 协议（整个系统的脊椎）

读取顺序（按依赖关系，从上层到下）：
1. config.py         ← 环境变量加载，最简单
2. capabilities/base.py ← Capability 基类 + PipelineContext + AgentPipeline
3. capabilities/builtin.py ← 内置 Capability（Security/Conversation/ContextCompression/Memory/Cache/Reflection 等）
4. server.py         ← 看 Pipeline 怎么被串起来的

## 第二天：看懂 Agent 核心（数据流）

5. core/provider.py   ← DeepSeek API 调用 + tenacity 重试
6. core/agent.py       ← ReAct while 循环（42 行，系统的心脏）
7. core/retriever.py   ← embedding + 余弦相似度
8. core/tool.py        ← 30 个自描述 Tool 实例（920 行，但只需看懂前 30 行 Tool 类定义）
9. core/registry.py    ← 四阶段路由（意图→粗筛→embedding→精排）

## 第三天：看懂基础设施

10. infra/db.py          ← MySQL 持久化（conversation/messages/memories/context summaries 等）
11. infra/cache.py        ← Redis 语义缓存
12. infra/memory.py       ← 记忆检索
13. infra/reflection.py   ← LLM 反思提取
14. infra/security.py     ← Prompt 注入、路径边界和确认策略
15. infra/audit.py        ← 工具执行审计

## 第四天：看 D5 上下文治理

16. infra/context_manager.py    ← token 预算、轮次划分、ContextSummary
17. infra/llm_output.py         ← 通用 LLM JSON 语法解析
18. infra/context_compressor.py ← Prompt、业务校验、摘要分块和滚动合并
19. D5_CONTEXT_NOTES.md         ← 完整数据流、失败策略、测试与限制

## 第五天：看连接与验证

20. server.py（重读）    ← 顺着 Pipeline 走一遍完整请求周期
21. main.py              ← CLI 命令行入口
22. D3_MEMORY_NOTES.md   ← 记忆写入、合并、检索和多因子排序
23. D4_SECURITY_NOTES.md ← 路径、权限、确认、恢复和审计
24. tests/               ← D2、D3、D4、D5 及真实 MySQL 集成测试
