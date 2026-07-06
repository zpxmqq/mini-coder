# D0 版本 — 五层模块化架构读取顺序

## 第一天：看懂 Capability 协议（整个系统的脊椎）

读取顺序（按依赖关系，从上层到下）：
1. config.py         ← 环境变量加载，最简单
2. capabilities/base.py ← Capability 基类 + PipelineContext + AgentPipeline
3. capabilities/builtin.py ← 5 个内置 Capability（Security/Conversation/Memory/Cache/Reflection）
4. server.py         ← 看 Pipeline 怎么被串起来的

## 第二天：看懂 Agent 核心（数据流）

5. core/provider.py   ← DeepSeek API 调用 + tenacity 重试
6. core/agent.py       ← ReAct while 循环（42 行，系统的心脏）
7. core/retriever.py   ← embedding + 余弦相似度
8. core/tool.py        ← 30 个自描述 Tool 实例（920 行，但只需看懂前 30 行 Tool 类定义）
9. core/registry.py    ← 四阶段路由（意图→粗筛→embedding→精排）

## 第三天：看懂基础设施

10. infra/db.py          ← MySQL 持久化（只关注 3 张表的结构）
11. infra/cache.py        ← Redis 语义缓存
12. infra/memory.py       ← 记忆检索
13. infra/reflection.py   ← LLM 反思提取
14. infra/security.py     ← Prompt 注入检测

## 第四天：看连接

15. server.py（重读）    ← 顺着代码流走一遍完整请求周期
16. main.py              ← CLI 命令行入口
17. tests/               ← 四组测试（W4/W5/W6/D2）
