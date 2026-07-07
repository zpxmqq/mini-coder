from infra.reflection import parse_typed_memories


def test_parse_valid_typed_memories():
    raw = """
    [
      {"memory_type": "fact", "content": "用户正在开发 mini-coder 项目"},
      {"memory_type": "preference", "content": "用户希望讲解代码时慢一点"}
    ]
    """

    memories = parse_typed_memories(raw)

    assert memories == [
        {"memory_type": "fact", "content": "用户正在开发 mini-coder 项目"},
        {"memory_type": "preference", "content": "用户希望讲解代码时慢一点"},
    ]


def test_parse_rejects_invalid_json():
    assert parse_typed_memories("这不是 JSON") == []


def test_parse_rejects_invalid_type_and_empty_content():
    raw = """
    [
      {"memory_type": "fact", "content": ""},
      {"memory_type": "todo", "content": "明天写 README"},
      {"memory_type": "reference", "content": "用户参考过 Claude Code 架构"}
    ]
    """

    memories = parse_typed_memories(raw)

    assert memories == [
        {"memory_type": "reference", "content": "用户参考过 Claude Code 架构"}
    ]


def test_parse_accepts_json_inside_markdown_fence():
    raw = """
    ```json
    [
      {"memory_type": "fact", "content": "用户使用 FastAPI 做后端接口"}
    ]
    ```
    """

    memories = parse_typed_memories(raw)

    assert memories == [
        {"memory_type": "fact", "content": "用户使用 FastAPI 做后端接口"}
    ]

def test_reflect_skips_existing_memory():
    from types import SimpleNamespace
    import infra.reflection as reflection

    raw = """
    [
      {"memory_type": "fact", "content": "user builds mini-coder"},
      {"memory_type": "preference", "content": "user prefers slow explanations"}
    ]
    """
    fake_resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=raw))]
    )
    stored = []

    old_chat = reflection.chat_with_deepseek
    old_exists = reflection.memory_exists
    old_add = reflection.add_memory
    try:
        reflection.chat_with_deepseek = lambda messages: fake_resp
        reflection.memory_exists = lambda content, memory_type: content == "user builds mini-coder"
        reflection.add_memory = lambda conversation_id, content, embedding=None, memory_type="fact": stored.append(
            {"conversation_id": conversation_id, "content": content, "memory_type": memory_type}
        )

        result = reflection.reflect(
            1,
            [
                {"role": "user", "content": "remember my project"},
                {"role": "assistant", "content": "ok"},
            ],
        )

        assert result == [
            {"memory_type": "preference", "content": "user prefers slow explanations"}
        ]
        assert stored == [
            {
                "conversation_id": 1,
                "content": "user prefers slow explanations",
                "memory_type": "preference",
            }
        ]
    finally:
        reflection.chat_with_deepseek = old_chat
        reflection.memory_exists = old_exists
        reflection.add_memory = old_add
