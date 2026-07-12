"""
D5 上下文治理的纯算法模块。

主要调用流程：
1. inspect_context(context.messages, context.schemas)
   检查本次发给 LLM 的消息和工具定义是否达到压缩阈值。
2. split_context_window(context.conversation_messages)
   如果需要压缩，再把未分组的真实对话划分为旧历史、最近轮次和当前 user。

注意：split_context_window() 接收的是原始、按时间排列的 conversation_messages，
不是 _group_conversation_turns() 或 _flatten_turns() 已经处理过的结果。
"""

import json
import math
from dataclasses import dataclass


ASCII_CHARS_PER_TOKEN = 4
NON_ASCII_CHARS_PER_TOKEN = 1.5
MESSAGE_OVERHEAD_TOKENS = 4


@dataclass(frozen=True)
class ContextBudget:
    """
    上下文预算配置。

    输入字段：模型最大上下文、为回答预留的 token、压缩触发比例。
    输出用途：由 inspect_context() 读取，本身不处理消息。
    """

    model_context_limit: int = 64_000
    reserved_output_tokens: int = 8_000
    compression_ratio: float = 0.8

    def __post_init__(self) -> None:
        if self.model_context_limit <= 0:
            raise ValueError("model_context_limit 必须大于 0")
        if self.reserved_output_tokens < 0:
            raise ValueError("reserved_output_tokens 不能小于 0")
        if self.reserved_output_tokens >= self.model_context_limit:
            raise ValueError("reserved_output_tokens 必须小于 model_context_limit")
        if not 0 < self.compression_ratio <= 1:
            raise ValueError("compression_ratio 必须在 (0, 1] 范围内")


@dataclass(frozen=True)
class ContextStats:
    """
    一次上下文检查的输出结果。

    包含 messages、schemas、总 token、可用输入空间、触发阈值，
    以及是否应该压缩的 should_compress。
    """

    message_tokens: int
    schema_tokens: int
    total_tokens: int
    available_input_tokens: int
    compression_threshold: int
    should_compress: bool


@dataclass(frozen=True)
class ContextWindow:
    """
    split_context_window() 的输出结果。

    compressible_messages：较早的对话，下一步交给 LLM 生成摘要。
    recent_messages：最近 N 轮对话，保持原文。
    current_user_message：当前请求，始终保持原文；不存在时为 None。
    """

    compressible_messages: list[dict]
    recent_messages: list[dict]
    current_user_message: dict | None


@dataclass(frozen=True)
class ContextSummary:
    """
    旧对话经过摘要 LLM 压缩并校验后的结构化结果。

    输入来源：未来的摘要解析器会把 LLM 返回的合法 JSON 转换成该对象。
    输出用途：交给 format_context_summary() 生成可注入 messages 的 system 消息。

    每个列表字段即使没有内容也要显式传入空列表，避免遗漏字段被静默接受。
    """

    task_goal: str
    completed_work: list[str]
    key_decisions: list[str]
    file_states: list[str]
    constraints: list[str]
    failures: list[str]
    pending_work: list[str]


def estimate_text_tokens(text: str) -> int:
    """
    使用中英文启发式规则估算一段字符串的 token 数。

    输入：普通字符串，例如消息 JSON 或 schema JSON。
    输出：估算 token 数 int；空字符串返回 0。
    """
    if not text:
        return 0

    ascii_count = sum(1 for char in text if char.isascii())
    non_ascii_count = len(text) - ascii_count

    ascii_tokens = math.ceil(ascii_count / ASCII_CHARS_PER_TOKEN)
    non_ascii_tokens = math.ceil(non_ascii_count / NON_ASCII_CHARS_PER_TOKEN)
    return ascii_tokens + non_ascii_tokens


def _serialize(value: object) -> str:
    """
    把 Python 对象序列化成用于 token 估算的紧凑 JSON 字符串。

    输入：message dict、schemas list 等可 JSON 序列化对象。
    输出：str。它只用于估算，不会修改输入对象。
    """
    return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))


def estimate_message_tokens(message: dict) -> int:
    """
    估算一条完整 message 的 token 数。

    输入：一条未分组的 message dict，可能包含 role、content、tool_calls 等字段。
    输出：该消息序列化后的估算 token，加上单条消息协议开销。
    """
    return estimate_text_tokens(_serialize(message)) + MESSAGE_OVERHEAD_TOKENS


def estimate_messages_tokens(messages: list[dict]) -> int:
    """
    估算本次准备发给 LLM 的 messages 总 token。

    输入：context.messages，即按时间排列、尚未按轮次分组的一维消息列表。
    输出：逐条调用 estimate_message_tokens() 后得到的总和。
    """
    return sum(estimate_message_tokens(message) for message in messages)


def estimate_schemas_tokens(schemas: list[dict]) -> int:
    """
    估算本次准备发给 LLM 的工具 schemas token。

    输入：context.schemas，即 ToolRegistry 选出的工具定义列表。
    输出：整个 schemas 列表序列化后的估算 token；空列表返回 0。
    """
    if not schemas:
        return 0
    return estimate_text_tokens(_serialize(schemas))


def inspect_context(
    messages: list[dict],
    schemas: list[dict],
    budget: ContextBudget | None = None,
) -> ContextStats:
    """
    合并检查 messages 和 schemas，并判断是否需要压缩。

    输入：
    - messages：context.messages，本次真正准备发给 LLM 的消息。
    - schemas：context.schemas，本次真正准备发给 LLM 的工具定义。
    - budget：可选预算；不传时使用 ContextBudget 默认值。

    输出：ContextStats。该函数只统计和判断，不会压缩或修改输入。
    """
    active_budget = budget or ContextBudget()
    message_tokens = estimate_messages_tokens(messages)
    schema_tokens = estimate_schemas_tokens(schemas)
    total_tokens = message_tokens + schema_tokens
    available_input_tokens = (
        active_budget.model_context_limit
        - active_budget.reserved_output_tokens
    )
    compression_threshold = max(
        1,
        int(available_input_tokens * active_budget.compression_ratio),
    )

    return ContextStats(
        message_tokens = message_tokens,
        schema_tokens = schema_tokens,
        total_tokens = total_tokens,
        available_input_tokens = available_input_tokens,
        compression_threshold = compression_threshold,
        should_compress = total_tokens >= compression_threshold,
    )


def _group_conversation_turns(
    messages: list[dict],
) -> tuple[list[dict], list[list[dict]]]:
    """
    把历史对话从一维消息列表分组成多个对话轮次。

    输入：split_context_window() 已经移除当前 user 后的历史消息，仍按时间排列。
    输出：
    - protected_messages：出现在第一个 user 前、无法归属轮次的消息。
    - turns：二维列表，每个子列表是一轮 [user, assistant, ...]。

    这是内部函数，调用者不需要提前对 conversation_messages 做分组。
    """
    protected_messages = []
    turns = []
    current_turn = []

    for message in messages:
        copied_message = message.copy()
        if copied_message.get("role") == "user":
            if current_turn:
                turns.append(current_turn)
            current_turn = [copied_message]
        elif current_turn:
            current_turn.append(copied_message)
        else:
            protected_messages.append(copied_message)

    if current_turn:
        turns.append(current_turn)

    return protected_messages, turns


def _flatten_turns(turns: list[list[dict]]) -> list[dict]:
    """
    把按轮次分组的二维消息列表，恢复成按时间排列的一维消息列表。

    输入：
    [
        [user1, assistant1],
        [user2, assistant2],
    ]

    输出：
    [user1, assistant1, user2, assistant2]
    """
    return [message.copy() for turn in turns for message in turn]


def split_context_window(
    conversation_messages: list[dict],
    keep_recent_turns: int = 4,
) -> ContextWindow:
    """
    从原始真实对话中划分可压缩历史、最近轮次和当前 user。

    输入：
    - conversation_messages：context.conversation_messages，未经分组、按时间排列的
      user/assistant 一维列表。不要先调用 _group_conversation_turns()。
    - keep_recent_turns：需要原样保留的最近完整轮次数量。

    内部流程：
    1. 复制输入，避免原列表被修改。
    2. 如果最后一条是 user，把它取出作为 current_user_message。
    3. 调用 _group_conversation_turns() 对剩余历史分组。
    4. 旧轮次放入 compressible_messages，最近 N 轮放入 recent_messages。
    5. 调用 _flatten_turns() 把二维轮次恢复成一维消息列表。

    输出：ContextWindow。输入 conversation_messages 保持不变。
    """
    if keep_recent_turns < 1:
        raise ValueError("keep_recent_turns 必须大于等于 1")

    messages = [message.copy() for message in conversation_messages]
    current_user_message = None

    if messages and messages[-1].get("role") == "user":
        current_user_message = messages.pop()

    protected_messages, turns = _group_conversation_turns(messages)
    split_index = max(len(turns) - keep_recent_turns, 0)
    compressible_turns = turns[:split_index]
    recent_turns = turns[split_index:]

    return ContextWindow(
        compressible_messages=_flatten_turns(compressible_turns),
        recent_messages=(
            [message.copy() for message in protected_messages]
            + _flatten_turns(recent_turns)
        ),
        current_user_message=(
            current_user_message.copy()
            if current_user_message is not None
            else None
        ),
    )

def format_context_summary(summary: ContextSummary) -> dict:
    """把校验后的结构化摘要转换为可注入 messages 的 system 消息。"""
    content_part = []
    content_part.append("历史对话摘要：")
    content_part.append("当前任务目标：")
    content_part.append(summary.task_goal)

    if summary.completed_work:
        content_part.append("已完成工作：")
        for item in summary.completed_work:
            content_part.append(f"- {item}")

    if summary.key_decisions:
        content_part.append("关键决策：")
        for item in summary.key_decisions:
            content_part.append(f"- {item}")

    if summary.file_states:
        content_part.append("文件状态：")
        for item in summary.file_states:
            content_part.append(f"- {item}")

    if summary.constraints:
        content_part.append("约束条件：")
        for item in summary.constraints:
            content_part.append(f"- {item}")

    if summary.failures:
        content_part.append("失败经历：")
        for item in summary.failures:
            content_part.append(f"- {item}")

    if summary.pending_work:
        content_part.append("待完成工作：")
        for item in summary.pending_work:
            content_part.append(f"- {item}")

    content = "\n".join(content_part)
    return {
        "role": "system",
        "content": content,
    }
