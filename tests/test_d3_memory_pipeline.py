import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def install_fake_retriever():
    fake_retriever = ModuleType("core.retriever")
    fake_retriever.top_k = lambda query, candidates, k: [(text, 1.0) for text in candidates[:k]]
    sys.modules["core.retriever"] = fake_retriever


def test_d3_memory_capabilities_work_as_request_response_pipeline():
    install_fake_retriever()

    import capabilities.builtin as builtin
    from capabilities.base import PipelineContext

    old_retrieve_memories = builtin.retrieve_memories
    old_reflect = builtin.reflect
    reflected_calls = []

    try:
        builtin.retrieve_memories = lambda query, k=3: [
            {"memory_type": "fact", "content": "user builds mini-coder"},
            {"memory_type": "preference", "content": "user prefers slow explanations"},
        ]
        builtin.reflect = lambda conversation_id, messages: reflected_calls.append(
            {"conversation_id": conversation_id, "messages": messages}
        )

        request = SimpleNamespace(message="continue D3")
        context = PipelineContext(
            messages=[{"role": "user", "content": request.message}],
            conversation_id=42,
        )
        memory_capability = builtin.MemoryCapability()
        reflection_capability = builtin.ReflectionCapability(min_messages=1)

        should_stop, context, short_answer = memory_capability.on_request(request, context)
        assert should_stop is False
        assert short_answer is None
        assert any("user builds mini-coder" in m["content"] for m in context.messages)
        assert any("user prefers slow explanations" in m["content"] for m in context.messages)

        answer = "D3 memory pipeline is connected."
        returned_answer = reflection_capability.on_response(answer, context)

        assert returned_answer == answer
        assert len(reflected_calls) == 1
        assert reflected_calls[0]["conversation_id"] == 42
        assert reflected_calls[0]["messages"][-1] == {"role": "assistant", "content": answer}
    finally:
        builtin.retrieve_memories = old_retrieve_memories
        builtin.reflect = old_reflect


if __name__ == "__main__":
    test_d3_memory_capabilities_work_as_request_response_pipeline()
    print("D3 memory pipeline test passed")