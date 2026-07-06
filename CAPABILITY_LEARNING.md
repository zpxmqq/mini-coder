# Capability 协议 — 学习路线 & 资料索引

## 你的架构本质

Capability 协议 = 责任链模式 + 中间件模式，在 AI Agent 层的一个变体。

责任链：每个处理器决定"自己处理还是传给下一个"
中间件：请求 → 中间件1 → 中间件2 → 核心处理 → 中间件2 → 中间件1 → 响应

你的 Capability 协议就是拿这个经典模式，套在 Agent 的生命周期上：
  on_request = 中间件的"请求前"阶段
  on_response = 中间件的"响应后"阶段

## 核心理解

你的 Capability 不是凭空捏的——它是责任链模式在 Agent 领域的一个具体应用。

### 第一步：先看经典设计模式（1h）

责任链模式（refactoring.guru）——看完就能认出你的 Capability 协议：
  https://refactoring.guru/design-patterns/chain-of-responsibility

这个网站图文解释到位，支持中文。关键理解：
  - Handler（处理者）= Capability
  - 每个 Handler 可以处理请求或传给下一个
  - Client 编排链的顺序

你的 on_request 返回 (False, ctx, None) = "不处理，传给下一个"
你的 on_request 返回 (True, ctx, "被拦截") = "我来处理，链停在这里"

### 第二步：看 FastAPI 中间件是怎么做的（30min）

FastAPI 中间件就是你的 Capability 的 HTTP 层翻版：
  https://fastapi.tiangolo.com/tutorial/middleware/

```python
# FastAPI 中间件（跟你的一模一样）
@app.middleware("http")
async def add_process_time_header(request, call_next):
    # on_request: 请求前
    response = await call_next(request)  # 调用下一个中间件/核心
    # on_response: 响应后
    return response
```

### 第三步：看 LangGraph 多 Agent 编排（2h）

LangGraph 的 Supervisor Agent 模式是你的 Capability 在更复杂场景的应用：
  https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/

```python
from langgraph_supervisor import create_supervisor
workflow = create_supervisor([research_agent, math_agent], model=model)
```

你的 Pipeline 跟它的本质区别：
  你管的是 Agent 外层的请求生命周期
  LangGraph 管的是 Agent 内部多 Agent 的协作

### 第四步（进阶）：Nuwa Protocol —— Agent 能力协议（1h）

这是最接近你设计的工业级实现——Agent Capability 作为可插拔的模块：
  https://deepwiki.com/nuwa-protocol/NIPs/4.1-agent-capability-protocol-(nip-5)

它的设计跟你的一样：声明式 的能力包（JSON 描述）→ 注册到路由器 → 请求时匹配触发

## 四步看完后你能回答的问题

1. "你的 Capability 协议用了什么设计模式？"
→ 责任链模式 + 中间件模式

2. "为什么用这个模式？"
→ 把 Security/Memory/Cache 等横切关注点从核心 agent 循环中解耦出来

3. "跟 FastAPI 的 Middleware 有什么异同？"
→ 同：都是请求前/响应后两个钩子。异：我的在 Agent 层，比 HTTP 层更接近业务逻辑

4. "跟 LangGraph Supervisor 有什么关系？"
→ 表层：我的 Capability 是 Agent 外层的管道；LangGraph Supervisor 是 Agent 内层的多 Agent 协作。两者可以组合

## 每个的预计时间

| 资源 | 时间 | 难度 |
|---|---|---|
| refactoring.guru 责任链 | 1h | ⭐ |
| FastAPI Middleware | 30min | ⭐ |
| LangGraph Supervisor 教程 | 2h | ⭐⭐ |
| Nuwa Protocol NIP-5 | 1h | ⭐⭐⭐ |

总计 4.5h，两天能看完。
