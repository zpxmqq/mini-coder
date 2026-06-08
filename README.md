# mini-coder

轻量 AI Coding Agent — 参考 Claude Code 架构的复刻与精简实现。

## 目标

8 周内做出**一个能扛面试官追问的 Agent 项目**：

- 不堆功能，每个机制都要有真实测出来的数字
- GitHub 从 Week 1 公开,commit 历史就是"真做过"的证据
- README 写 design decisions(为什么这样设计 + 哪些方案被淘汰了)
- 最终交付:repo + 3 分钟 demo 视频 + 评测报告

## 核心机制(对应简历 6 条 bullets)

1. **Skill 二阶段路由** — embedding 召回 + LLM 精排
2. **自适应记忆沉淀闭环** — reflection node + SQLite 结构化存储 + 相似任务召回
3. **分层上下文压缩** + Anthropic Prompt Caching
4. **主从双 Agent** — LangGraph supervisor 模式
5. **权限分级 + Prompt 注入防御**
6. **完整离线评测** — SWE-Lite 子集 + GPT-4-as-judge 三维度打分

## 8 周时间表

| Week | 主题 |
| --- | --- |
| 1 | ReAct loop + 5 原子工具(read/write/edit/bash/grep) |
| 2 | Skill 二阶段路由 |
| 3 | 主从双 Agent |
| 4 | 上下文压缩 + Prompt Cache |
| 5 | 记忆沉淀闭环 |
| 6 | 权限分级 + 注入防御 |
| 7 | 评测搭建 + ablation 实验 |
| 8 | README 终稿 + demo 视频 + 简历整理 |

## 技术栈

LangGraph · Anthropic Claude SDK · OpenAI SDK · BGE-Reranker · SQLite · pytest

---

> 写于 2026-06-04,明天 Week 1 Day 1 起步。
