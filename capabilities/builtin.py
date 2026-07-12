"""
内置 Capability 实现：限流 / 安全 / 对话管理 / 记忆 / 缓存 / Agent / 反思

每个 Capability 遵循 capability.py 的 on_request/on_response 协议。
可直接组合进 AgentPipeline 使用。
"""

from capabilities.base import Capability, PipelineContext
from infra.security import check_prompt_injection
from core.tool import ALLOWED_LEVELS
from infra.memory import retrieve_memories
from infra.reflection import reflect
from infra.context_compressor import (
    SummaryBudget,
    parse_context_summary,
    summarize_context,
)
from infra.context_manager import (
    ContextBudget,
    estimate_message_tokens,
    estimate_messages_tokens,
    format_context_summary,
    inspect_context,
    split_context_window,
)
from infra.cache import get_cache_key, check_cache, set_cache
from infra.db import (
    add_message,
    check_conversation_id,
    create_conversation,
    get_context_summary_state,
    get_message_records,
    mark_memories_used,
    upsert_context_summary_state,
)
import time


class RateLimitCapability(Capability):
    """限流：固定窗口计数器，同一 IP 每分钟最多 max_requests 次请求"""

    def __init__(self, max_requests: int = 10):
        self.max_requests = max_requests
        self._window: dict[str, list[float]] = {}

    def on_request(self, request, context):
        ip = "unknown"  # 由 server.py 注入真实 IP——先做简化版
        now = time.time()
        self._window.setdefault(ip, [])
        self._window[ip] = [t for t in self._window[ip] if now - t < 60]
        if len(self._window[ip]) >= self.max_requests:
            return True, context, "请求太频繁，请稍后再试"
        self._window[ip].append(now)
        return False, context, None


class SecurityCapability(Capability):
    """安全：注入检测 + 权限级别校验"""

    def on_request(self, request, context):
        risk = check_prompt_injection(request.message)
        if risk:
            return True, context, f"输入包含不安全内容: {risk}"
        return False, context, None


class ConversationCapability(Capability):
    """对话管理：加载历史 / 新建对话"""

    def on_request(self, request, context):
        conv_id = request.conversation_id
        if conv_id and check_conversation_id(conv_id):
            records = get_message_records(conv_id)
        else:
            conv_id = create_conversation()
            records = []

        history = [
            {
                "role": record["role"],
                "content": record["content"],
            }
            for record in records
        ]

        current_user = {"role": "user", "content": request.message}
        conversation_messages = history + [current_user]
        current_message_id = add_message(conv_id, "user", request.message)
        conversation_records = records + [{
            "id": current_message_id,
            "role": "user",
            "content": request.message,
        }]

        # 真实对话和模型输入分别保存，避免临时注入内容污染原始对话。
        context.conversation_messages.extend(
            message.copy() for message in conversation_messages
        )
        context.messages.extend(
            message.copy() for message in conversation_messages
        )
        context.metadata["conversation_records"] = [
            record.copy() for record in conversation_records
        ]
        context.conversation_id = conv_id
        return False, context, None

    def on_response(self, answer, context):
        if context.conversation_id:
            assistant_message_id = add_message(
                context.conversation_id,
                "assistant",
                answer,
            )
            context.conversation_messages.append({
                "role": "assistant",
                "content": answer,
            })
            context.metadata.setdefault("conversation_records", []).append({
                "id": assistant_message_id,
                "role": "assistant",
                "content": answer,
            })
        return answer


class ContextCompressionCapability(Capability):
    """上下文压缩：超过 token 阈值时，用结构化摘要替换较早对话。"""

    def __init__(
        self,
        keep_recent_turns: int = 4,
        budget: ContextBudget | None = None,
        summary_budget: SummaryBudget | None = None,
    ):
        self.keep_recent_turns = keep_recent_turns
        self.budget = budget
        self.summary_budget = summary_budget

    @staticmethod
    def _replace_context_messages(
        context: PipelineContext,
        summary_message: dict,
        retained_records: list[dict],
    ) -> None:
        """用摘要和指定的原始记录重建本次模型输入。"""
        preserved_count = max(
            len(context.messages) - len(context.conversation_messages),
            0,
        )
        compressed_messages = [
            message.copy()
            for message in context.messages[:preserved_count]
        ]
        compressed_messages.append(summary_message.copy())
        compressed_messages.extend(
            {
                "role": record["role"],
                "content": record["content"],
            }
            for record in retained_records
        )
        context.messages = compressed_messages

    def on_request(self, request, context):
        stats = inspect_context(
            context.messages,
            context.schemas,
            self.budget,
        )
        if not stats.should_compress:
            return False, context, None

        conversation_records = context.metadata.get("conversation_records")
        if not conversation_records:
            return False, context, None

        window = split_context_window(
            conversation_records,
            keep_recent_turns=self.keep_recent_turns,
        )
        if not window.compressible_messages:
            return False, context, None

        state = None
        previous_summary = None
        compressed_through_message_id = 0
        if context.conversation_id is not None:
            state = get_context_summary_state(context.conversation_id)
            if state is not None:
                previous_summary = parse_context_summary(state["summary_json"])
                if previous_summary is not None:
                    compressed_through_message_id = int(
                        state["compressed_through_message_id"]
                    )

        new_compressible_records = [
            record
            for record in window.compressible_messages
            if isinstance(record.get("id"), int)
            and record["id"] > compressed_through_message_id
        ]
        new_compressible_messages = [
            {
                "role": record["role"],
                "content": record["content"],
            }
            for record in new_compressible_records
        ]

        summary = summarize_context(
            new_compressible_messages,
            previous_summary=previous_summary,
            budget=self.summary_budget,
        )
        if summary is None:
            if previous_summary is not None:
                fallback_records = [
                    record
                    for record in conversation_records
                    if isinstance(record.get("id"), int)
                    and record["id"] > compressed_through_message_id
                ]
                self._replace_context_messages(
                    context,
                    format_context_summary(previous_summary),
                    fallback_records,
                )
            return False, context, None

        summary_message = format_context_summary(summary)

        if new_compressible_records and context.conversation_id is not None:
            compressed_through_message_id = new_compressible_records[-1]["id"]
            represented_messages = [
                {
                    "role": record["role"],
                    "content": record["content"],
                }
                for record in window.compressible_messages
            ]
            upsert_context_summary_state(
                conversation_id=context.conversation_id,
                summary=summary,
                compressed_through_message_id=compressed_through_message_id,
                source_token_count=estimate_messages_tokens(represented_messages),
                summary_token_count=estimate_message_tokens(summary_message),
            )

        retained_records = list(window.recent_messages)
        if window.current_user_message is not None:
            retained_records.append(window.current_user_message)
        self._replace_context_messages(
            context,
            summary_message,
            retained_records,
        )
        return False, context, None


class MemoryCapability(Capability):
    """记忆：检索相关记忆 → 按类型注入 system prompt"""

    def on_request(self, request, context):
        relevant = retrieve_memories(request.message, k=3)
        if relevant:
            grouped = {
                "fact": [],
                "preference": [],
                "reference": [],
            }
            used_memory_ids = []
            for memory in relevant:
                memory_type = memory.get("memory_type", "fact")
                content = memory.get("content", "")
                if memory_type in grouped and content:
                    grouped[memory_type].append(content)
                    if "id" in memory:
                        used_memory_ids.append(memory["id"])

            labels = {
                "fact": "长期事实",
                "preference": "用户偏好",
                "reference": "参考背景",
            }
            sections = []
            for memory_type in ("fact", "preference", "reference"):
                contents = grouped[memory_type]
                if contents:
                    section = labels[memory_type] + ":\n" + "\n".join(f"- {content}" for content in contents)
                    sections.append(section)

            if sections:
                memory_text = "相关记忆:\n" + "\n\n".join(sections)
                context.messages.append({"role": "system", "content": memory_text})
                mark_memories_used(used_memory_ids)
        return False, context, None

class CacheCapability(Capability):
    """缓存：检查缓存 → 命中直接返回 / 未命中存缓存"""

    def on_request(self, request, context):
        self._cache_key = get_cache_key(request.message, context.schemas)
        cached = check_cache(self._cache_key)
        if cached:
            return True, context, cached  # short-circuit
        return False, context, None

    def on_response(self, answer, context):
        set_cache(self._cache_key, answer)
        return answer


class ReflectionCapability(Capability):
    """反思：对话长度 ≥ min_messages 时触发 LLM 反思提取记忆"""

    def __init__(self, min_messages: int = 6):
        self.min_messages = min_messages

    def on_response(self, answer, context):
        if (
            context.conversation_id
            and len(context.conversation_messages) >= self.min_messages
        ):
            messages_for_reflection = [
                message.copy() for message in context.conversation_messages
            ]
            reflect(context.conversation_id, messages_for_reflection)
        return answer
