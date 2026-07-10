import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_long_text_costs_more_tokens_than_short_text():
    from infra.context_manager import estimate_text_tokens

    assert estimate_text_tokens("这是短文本") < estimate_text_tokens("这是更长的文本" * 20)
    assert estimate_text_tokens("short") < estimate_text_tokens("long text " * 20)


def test_messages_and_schemas_are_counted_separately():
    from infra.context_manager import (
        estimate_messages_tokens,
        estimate_schemas_tokens,
    )

    messages = [
        {"role": "system", "content": "系统提示"},
        {"role": "user", "content": "读取 core/agent.py"},
    ]
    schemas = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        }
    ]

    assert estimate_messages_tokens(messages) > 0
    assert estimate_schemas_tokens(schemas) > 0
    assert estimate_messages_tokens([]) == 0
    assert estimate_schemas_tokens([]) == 0


def test_tool_call_arguments_are_included_in_message_estimate():
    from infra.context_manager import estimate_message_tokens

    short_call = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "write_file",
                    "arguments": '{"path":"a.txt","content":"x"}',
                },
            }
        ],
    }
    long_call = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "write_file",
                    "arguments": '{"path":"a.txt","content":"' + "长内容" * 100 + '"}',
                },
            }
        ],
    }

    assert estimate_message_tokens(long_call) > estimate_message_tokens(short_call)


def test_inspect_context_combines_tokens_and_decides_compression():
    from infra.context_manager import ContextBudget, inspect_context

    messages = [{"role": "user", "content": "需要保留的上下文" * 20}]
    schemas = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取文件内容",
            },
        }
    ]
    budget = ContextBudget(
        model_context_limit=120,
        reserved_output_tokens=20,
        compression_ratio=0.5,
    )

    stats = inspect_context(messages, schemas, budget)

    assert stats.total_tokens == stats.message_tokens + stats.schema_tokens
    assert stats.available_input_tokens == 100
    assert stats.compression_threshold == 50
    assert stats.should_compress is True


def test_small_context_does_not_trigger_compression():
    from infra.context_manager import ContextBudget, inspect_context

    stats = inspect_context(
        [{"role": "user", "content": "你好"}],
        [],
        ContextBudget(
            model_context_limit=1000,
            reserved_output_tokens=200,
            compression_ratio=0.8,
        ),
    )

    assert stats.compression_threshold == 640
    assert stats.should_compress is False


def test_invalid_context_budget_is_rejected():
    from infra.context_manager import ContextBudget

    invalid_configs = [
        {"model_context_limit": 0},
        {"model_context_limit": 100, "reserved_output_tokens": 100},
        {"compression_ratio": 0},
        {"compression_ratio": 1.1},
    ]

    for config in invalid_configs:
        try:
            ContextBudget(**config)
        except ValueError:
            continue
        raise AssertionError(f"非法配置没有被拒绝: {config}")


if __name__ == "__main__":
    test_long_text_costs_more_tokens_than_short_text()
    test_messages_and_schemas_are_counted_separately()
    test_tool_call_arguments_are_included_in_message_estimate()
    test_inspect_context_combines_tokens_and_decides_compression()
    test_small_context_does_not_trigger_compression()
    test_invalid_context_budget_is_rejected()
    print("D5 context budget tests passed")
