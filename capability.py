"""
架构：Capability 协议 + AgentPipeline

设计目的：让 Security/Memory/Cache/Reflection 等模块遵循统一接口，
通过 Pipeline 按需编排，替代 server.py 里 chat() 的手动堆砌。

接口设计：
  on_request   — 请求进来时执行（限流/安检/记忆注入/缓存检查）
                  返回 (should_short_circuit: bool, context: dict)
                  short_circuit=True 表示直接返回，不继续走后续 Pipeline
  on_response  — agent 返回后执行（缓存存储/反思触发/日志记录）
                  返回 str（可能是修改后的 answer）
"""

from dataclasses import dataclass, field


@dataclass
class PipelineContext:
    """Pipeline 中各 Capability 之间传递的上下文"""
    messages: list[dict] = field(default_factory=list)
    schemas: list[dict] = field(default_factory=list)
    conversation_id: int | None = None
    metadata: dict = field(default_factory=dict)


class Capability:
    """
    Capability 基类——所有能力模块遵循此协议。

    子类重写 on_request / on_response 中的一个或两个。
    不重写的方法直接透传，不做任何处理。

    on_request 返回 (short_circuit, context):
      - short_circuit=False → 继续下一个 Capability
      - short_circuit=True → 跳过后续 Capability，直接用 answer 返回

    on_response 返回 str（修改后的 answer）。
    """

    def on_request(self, request, context: PipelineContext) -> tuple[bool, PipelineContext, str | None]:
        """请求前钩子。返回 (should_stop, updated_context, answer_if_stop)"""
        return False, context, None

    def on_response(self, answer: str, context: PipelineContext) -> str:
        """响应后钩子。返回修改后的 answer。"""
        return answer


class AgentPipeline:
    """按序编排 Capability，替代 chat() 的手动流水线"""

    def __init__(self, capabilities: list[Capability] | None = None):
        self.capabilities = capabilities or []

    def add(self, cap: Capability):
        self.capabilities.append(cap)

    def run(self, request, run_agent) -> dict:
        """
        执行完整流水线。

        request: ChatRequest（Pydantic 模型）
        run_agent: callable，签名为 (messages, schemas, permission_level) -> answer: str
        """
        ctx = PipelineContext()

        # ── 阶段 1: on_request（请求前）──
        for cap in self.capabilities:
            should_stop, ctx, short_answer = cap.on_request(request, ctx)
            if should_stop:
                return {"reply": short_answer, "conversation_id": ctx.conversation_id}

        # ── 阶段 2: 运行 agent ──
        answer = run_agent(
            messages=ctx.messages,
            schemas=ctx.schemas,
            permission_level=request.permission_level if hasattr(request, "permission_level") else "low",
        )

        # ── 阶段 3: on_response（响应后）──
        for cap in self.capabilities:
            answer = cap.on_response(answer, ctx)

        return {"reply": answer, "conversation_id": ctx.conversation_id}
