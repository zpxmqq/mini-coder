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


def test_retrieve_memories_keeps_memory_type():
    install_fake_retriever()
    sys.modules.pop("infra.memory", None)
    import infra.memory as memory_module

    old_get_memories = memory_module.get_memories
    old_top_k = memory_module.top_k
    try:
        memory_module.get_memories = lambda: [
            {"memory_type": "fact", "content": "user builds mini-coder"},
            {"memory_type": "preference", "content": "user prefers slow explanations"},
            {"memory_type": "reference", "content": "user referenced Claude Code"},
        ]
        memory_module.top_k = lambda query, candidates, k: [
            ("user prefers slow explanations", 0.91),
            ("user builds mini-coder", 0.88),
        ]

        results = memory_module.retrieve_memories("how should I explain code?", k=2)

        assert results == [
            {"memory_type": "preference", "content": "user prefers slow explanations"},
            {"memory_type": "fact", "content": "user builds mini-coder"},
        ]
    finally:
        memory_module.get_memories = old_get_memories
        memory_module.top_k = old_top_k


def test_memory_capability_injects_grouped_memory_prompt():
    install_fake_retriever()
    import capabilities.builtin as builtin
    from capabilities.base import PipelineContext

    old_retrieve_memories = builtin.retrieve_memories
    try:
        builtin.retrieve_memories = lambda query, k=3: [
            {"memory_type": "fact", "content": "user builds mini-coder"},
            {"memory_type": "preference", "content": "user prefers slow explanations"},
            {"memory_type": "reference", "content": "user referenced Claude Code"},
        ]

        request = SimpleNamespace(message="continue D3")
        context = PipelineContext(messages=[])
        should_stop, context, short_answer = builtin.MemoryCapability().on_request(request, context)

        assert should_stop is False
        assert short_answer is None
        assert len(context.messages) == 1

        injected = context.messages[0]
        assert injected["role"] == "system"
        assert "相关记忆" in injected["content"]
        assert "长期事实" in injected["content"]
        assert "user builds mini-coder" in injected["content"]
        assert "用户偏好" in injected["content"]
        assert "user prefers slow explanations" in injected["content"]
        assert "参考背景" in injected["content"]
        assert "user referenced Claude Code" in injected["content"]
    finally:
        builtin.retrieve_memories = old_retrieve_memories


if __name__ == "__main__":
    test_retrieve_memories_keeps_memory_type()
    test_memory_capability_injects_grouped_memory_prompt()
    print("D3 memory flow tests passed")