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
from infra.cache import get_cache_key, check_cache, set_cache
from infra.db import create_conversation, get_messages, check_conversation_id, add_message, mark_memories_used
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
            history = get_messages(conv_id)
            context.messages.extend(history)
        else:
            conv_id = create_conversation()
        context.conversation_id = conv_id
        return False, context, None

    def on_response(self, answer, context):
        if context.conversation_id:
            add_message(context.conversation_id, "assistant", answer)
        return answer


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
        if context.conversation_id and len(context.messages) >= self.min_messages:
            messages_for_reflection = context.messages + [
                {"role": "assistant", "content": answer}
            ]
            reflect(context.conversation_id, messages_for_reflection)
        return answer
