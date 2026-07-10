import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_fake_retriever():
    fake_retriever = ModuleType("core.retriever")
    fake_retriever.top_k = lambda query, candidates, k: []
    sys.modules["core.retriever"] = fake_retriever


def test_existing_conversation_keeps_order_and_persists_user_once():
    _install_fake_retriever()

    import capabilities.builtin as builtin
    from capabilities.base import PipelineContext

    original_check = builtin.check_conversation_id
    original_get = builtin.get_messages
    original_create = builtin.create_conversation
    original_add = builtin.add_message
    saved_messages = []

    try:
        builtin.check_conversation_id = lambda conversation_id: conversation_id == 7
        builtin.get_messages = lambda conversation_id: [
            {"role": "user", "content": "旧问题"},
            {"role": "assistant", "content": "旧回答"},
        ]
        builtin.create_conversation = lambda: 99
        builtin.add_message = lambda conversation_id, role, content: saved_messages.append(
            (conversation_id, role, content)
        )

        request = SimpleNamespace(conversation_id=7, message="当前问题")
        context = PipelineContext(
            messages=[{"role": "system", "content": "系统提示"}]
        )

        should_stop, context, short_answer = builtin.ConversationCapability().on_request(
            request, context
        )

        assert should_stop is False
        assert short_answer is None
        assert context.conversation_id == 7
        assert context.messages == [
            {"role": "system", "content": "系统提示"},
            {"role": "user", "content": "旧问题"},
            {"role": "assistant", "content": "旧回答"},
            {"role": "user", "content": "当前问题"},
        ]
        assert context.conversation_messages == [
            {"role": "user", "content": "旧问题"},
            {"role": "assistant", "content": "旧回答"},
            {"role": "user", "content": "当前问题"},
        ]
        assert saved_messages == [(7, "user", "当前问题")]

        context.messages[-1]["content"] = "只修改模型输入"
        assert context.conversation_messages[-1]["content"] == "当前问题"
    finally:
        builtin.check_conversation_id = original_check
        builtin.get_messages = original_get
        builtin.create_conversation = original_create
        builtin.add_message = original_add


def test_new_conversation_persists_first_user_message():
    _install_fake_retriever()

    import capabilities.builtin as builtin
    from capabilities.base import PipelineContext

    original_check = builtin.check_conversation_id
    original_get = builtin.get_messages
    original_create = builtin.create_conversation
    original_add = builtin.add_message
    saved_messages = []

    try:
        builtin.check_conversation_id = lambda conversation_id: False
        builtin.get_messages = lambda conversation_id: (_ for _ in ()).throw(
            AssertionError("新会话不应该读取历史消息")
        )
        builtin.create_conversation = lambda: 42
        builtin.add_message = lambda conversation_id, role, content: saved_messages.append(
            (conversation_id, role, content)
        )

        request = SimpleNamespace(conversation_id=None, message="第一条问题")
        context = PipelineContext(
            messages=[{"role": "system", "content": "系统提示"}]
        )

        should_stop, context, short_answer = builtin.ConversationCapability().on_request(
            request, context
        )

        assert should_stop is False
        assert short_answer is None
        assert context.conversation_id == 42
        assert context.messages == [
            {"role": "system", "content": "系统提示"},
            {"role": "user", "content": "第一条问题"},
        ]
        assert context.conversation_messages == [
            {"role": "user", "content": "第一条问题"},
        ]
        assert saved_messages == [(42, "user", "第一条问题")]
    finally:
        builtin.check_conversation_id = original_check
        builtin.get_messages = original_get
        builtin.create_conversation = original_create
        builtin.add_message = original_add


def test_response_updates_clean_conversation_history_once():
    _install_fake_retriever()

    import capabilities.builtin as builtin
    from capabilities.base import PipelineContext

    original_add = builtin.add_message
    saved_messages = []

    try:
        builtin.add_message = lambda conversation_id, role, content: saved_messages.append(
            (conversation_id, role, content)
        )
        context = PipelineContext(
            messages=[{"role": "system", "content": "系统提示"}],
            conversation_messages=[{"role": "user", "content": "当前问题"}],
            conversation_id=42,
        )

        answer = builtin.ConversationCapability().on_response("最终回答", context)

        assert answer == "最终回答"
        assert context.conversation_messages == [
            {"role": "user", "content": "当前问题"},
            {"role": "assistant", "content": "最终回答"},
        ]
        assert context.messages == [
            {"role": "system", "content": "系统提示"},
        ]
        assert saved_messages == [(42, "assistant", "最终回答")]
    finally:
        builtin.add_message = original_add


def test_reflection_uses_only_clean_conversation_messages():
    _install_fake_retriever()

    import capabilities.builtin as builtin
    from capabilities.base import PipelineContext

    original_reflect = builtin.reflect
    reflected_calls = []

    try:
        builtin.reflect = lambda conversation_id, messages: reflected_calls.append(
            (conversation_id, messages)
        )
        context = PipelineContext(
            messages=[
                {"role": "system", "content": "系统提示"},
                {"role": "system", "content": "相关长期记忆"},
            ],
            conversation_messages=[
                {"role": "user", "content": "当前问题"},
                {"role": "assistant", "content": "最终回答"},
            ],
            conversation_id=42,
        )

        answer = builtin.ReflectionCapability(min_messages=2).on_response(
            "最终回答", context
        )

        assert answer == "最终回答"
        assert reflected_calls == [
            (
                42,
                [
                    {"role": "user", "content": "当前问题"},
                    {"role": "assistant", "content": "最终回答"},
                ],
            )
        ]
    finally:
        builtin.reflect = original_reflect


def test_memory_injection_does_not_pollute_conversation_messages():
    _install_fake_retriever()

    import capabilities.builtin as builtin
    from capabilities.base import PipelineContext

    original_retrieve = builtin.retrieve_memories
    original_mark = builtin.mark_memories_used

    try:
        builtin.retrieve_memories = lambda query, k=3: [
            {
                "id": 8,
                "memory_type": "preference",
                "content": "用户希望先理解原理",
            }
        ]
        builtin.mark_memories_used = lambda memory_ids: None
        context = PipelineContext(
            messages=[
                {"role": "system", "content": "系统提示"},
                {"role": "user", "content": "当前问题"},
            ],
            conversation_messages=[
                {"role": "user", "content": "当前问题"},
            ],
        )

        builtin.MemoryCapability().on_request(
            SimpleNamespace(message="当前问题"), context
        )

        assert any("用户希望先理解原理" in message["content"] for message in context.messages)
        assert context.conversation_messages == [
            {"role": "user", "content": "当前问题"},
        ]
    finally:
        builtin.retrieve_memories = original_retrieve
        builtin.mark_memories_used = original_mark


if __name__ == "__main__":
    test_existing_conversation_keeps_order_and_persists_user_once()
    test_new_conversation_persists_first_user_message()
    test_response_updates_clean_conversation_history_once()
    test_reflection_uses_only_clean_conversation_messages()
    test_memory_injection_does_not_pollute_conversation_messages()
    print("D5 context flow tests passed")
