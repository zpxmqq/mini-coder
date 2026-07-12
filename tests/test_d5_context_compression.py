import json
import sys
from dataclasses import asdict
from pathlib import Path
from types import ModuleType, SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_fake_retriever():
    fake_retriever = ModuleType("core.retriever")
    fake_retriever.top_k = lambda query, candidates, k: []
    sys.modules["core.retriever"] = fake_retriever


def _summary_json(label: str) -> str:
    return json.dumps(
        {
            "task_goal": "完成 D5 上下文压缩",
            "completed_work": [label],
            "key_decisions": ["使用滚动摘要"],
            "file_states": [],
            "constraints": ["不能丢失未压缩原文"],
            "failures": [],
            "pending_work": [],
        },
        ensure_ascii=False,
    )


def _fake_response(content: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )


def _summary_payload(request_messages: list[dict]) -> dict:
    payload_text = request_messages[1]["content"].split("\n", 1)[1]
    return json.loads(payload_text)


def _build_records(turn_count: int) -> list[dict]:
    records = []
    message_id = 1
    for turn in range(1, turn_count + 1):
        records.append({
            "id": message_id,
            "role": "user",
            "content": f"问题{turn}",
        })
        message_id += 1
        records.append({
            "id": message_id,
            "role": "assistant",
            "content": f"回答{turn}",
        })
        message_id += 1
    return records


def _without_ids(records: list[dict]) -> list[dict]:
    return [
        {"role": record["role"], "content": record["content"]}
        for record in records
    ]


def test_chunking_preserves_complete_turns_when_they_fit():
    from infra.context_compressor import (
        SummaryBudget,
        estimate_summary_request_tokens,
        take_summary_chunk,
    )

    first_turn = [
        {"role": "user", "content": "A" * 300},
        {"role": "assistant", "content": "B" * 300},
    ]
    second_turn = [
        {"role": "user", "content": "C" * 300},
        {"role": "assistant", "content": "D" * 300},
    ]
    one_turn_tokens = estimate_summary_request_tokens(first_turn)
    budget = SummaryBudget(
        model_context_limit=one_turn_tokens + 500,
        reserved_output_tokens=500,
        safety_margin_tokens=0,
    )

    chunk = take_summary_chunk(first_turn + second_turn, budget=budget)

    assert chunk is not None
    assert chunk.messages == first_turn
    assert chunk.remaining_messages == second_turn


def test_oversized_message_is_split_without_losing_content():
    from infra.context_compressor import (
        SummaryBudget,
        estimate_summary_request_tokens,
        summarize_context,
    )
    from infra.context_manager import estimate_messages_tokens

    original_content = "超长消息内容" * 1000
    messages = [{"role": "user", "content": original_content}]
    base_tokens = estimate_summary_request_tokens([])
    input_token_limit = base_tokens + 400
    budget = SummaryBudget(
        model_context_limit=input_token_limit + 500,
        reserved_output_tokens=500,
        safety_margin_tokens=0,
    )
    calls = []

    def fake_llm(request_messages):
        calls.append(request_messages)
        return _fake_response(_summary_json(f"已处理第 {len(calls)} 块"))

    summary = summarize_context(
        messages,
        llm_call=fake_llm,
        budget=budget,
    )

    assert summary is not None
    assert len(calls) > 1
    assert all(
        estimate_messages_tokens(request_messages) <= input_token_limit
        for request_messages in calls
    )

    payloads = [_summary_payload(request_messages) for request_messages in calls]
    fragments = [
        message["content"]
        for payload in payloads
        for message in payload["new_messages"]
    ]
    assert "".join(fragments) == original_content
    assert payloads[0]["previous_summary"] is None
    assert all(
        payload["previous_summary"] is not None
        for payload in payloads[1:]
    )


def test_any_failed_chunk_discards_the_temporary_rolling_summary():
    from infra.context_compressor import (
        SummaryBudget,
        estimate_summary_request_tokens,
        summarize_context,
    )

    messages = [{"role": "user", "content": "需要分块" * 1000}]
    base_tokens = estimate_summary_request_tokens([])
    budget = SummaryBudget(
        model_context_limit=base_tokens + 900,
        reserved_output_tokens=500,
        safety_margin_tokens=0,
    )
    call_count = 0

    def failing_second_call(request_messages):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            return _fake_response("不是合法 JSON")
        return _fake_response(_summary_json("第一块成功"))

    summary = summarize_context(
        messages,
        llm_call=failing_second_call,
        budget=budget,
    )

    assert call_count == 2
    assert summary is None


def test_empty_increment_reuses_summary_without_calling_llm():
    from infra.context_compressor import summarize_context
    from infra.context_manager import ContextSummary

    previous_summary = ContextSummary(
        task_goal="继续完成 D5",
        completed_work=["旧摘要已经持久化"],
        key_decisions=[],
        file_states=[],
        constraints=[],
        failures=[],
        pending_work=[],
    )

    def forbidden_llm_call(request_messages):
        raise AssertionError("没有新增消息时不应该调用摘要 LLM")

    summary = summarize_context(
        [],
        llm_call=forbidden_llm_call,
        previous_summary=previous_summary,
    )

    assert summary is previous_summary


def test_summary_larger_than_reserved_output_is_rejected():
    from infra.context_compressor import (
        SummaryBudget,
        estimate_summary_request_tokens,
        summarize_context,
    )

    base_tokens = estimate_summary_request_tokens([])
    budget = SummaryBudget(
        model_context_limit=base_tokens + 300,
        reserved_output_tokens=100,
        safety_margin_tokens=0,
    )
    oversized_summary = json.dumps(
        {
            "task_goal": "很长的目标" * 100,
            "completed_work": [],
            "key_decisions": [],
            "file_states": [],
            "constraints": [],
            "failures": [],
            "pending_work": [],
        },
        ensure_ascii=False,
    )

    summary = summarize_context(
        [{"role": "user", "content": "短消息"}],
        llm_call=lambda request_messages: _fake_response(oversized_summary),
        budget=budget,
    )

    assert summary is None


def test_capability_only_merges_records_after_persisted_cursor():
    _install_fake_retriever()

    import capabilities.builtin as builtin
    from capabilities.base import PipelineContext
    from infra.context_compressor import SummaryBudget
    from infra.context_manager import ContextBudget, ContextSummary

    records = _build_records(6)
    records.append({"id": 13, "role": "user", "content": "当前问题"})
    clean_messages = _without_ids(records)
    previous_summary = ContextSummary(
        task_goal="完成 D5",
        completed_work=["已压缩消息 1 到 4"],
        key_decisions=[],
        file_states=[],
        constraints=[],
        failures=[],
        pending_work=[],
    )
    merged_summary = ContextSummary(
        task_goal="完成 D5.7",
        completed_work=["已压缩消息 1 到 8"],
        key_decisions=["分块全部成功后才推进游标"],
        file_states=[],
        constraints=[],
        failures=[],
        pending_work=[],
    )
    summary_budget = SummaryBudget()
    context = PipelineContext(
        messages=[{"role": "system", "content": "系统提示"}] + clean_messages,
        conversation_messages=[message.copy() for message in clean_messages],
        conversation_id=7,
        metadata={"conversation_records": records},
    )
    captured_summary_calls = []
    saved_states = []

    original_get_state = builtin.get_context_summary_state
    original_summarize = builtin.summarize_context
    original_upsert = builtin.upsert_context_summary_state
    try:
        builtin.get_context_summary_state = lambda conversation_id: {
            "summary_json": json.dumps(asdict(previous_summary), ensure_ascii=False),
            "compressed_through_message_id": 4,
        }

        def fake_summarize(messages, previous_summary=None, budget=None):
            captured_summary_calls.append((messages, previous_summary, budget))
            return merged_summary

        builtin.summarize_context = fake_summarize
        builtin.upsert_context_summary_state = lambda **kwargs: saved_states.append(
            kwargs
        )

        capability = builtin.ContextCompressionCapability(
            keep_recent_turns=2,
            budget=ContextBudget(
                model_context_limit=100,
                reserved_output_tokens=10,
                compression_ratio=0.1,
            ),
            summary_budget=summary_budget,
        )
        should_stop, context, short_answer = capability.on_request(
            SimpleNamespace(),
            context,
        )

        assert should_stop is False
        assert short_answer is None
        assert captured_summary_calls == [
            (_without_ids(records[4:8]), previous_summary, summary_budget)
        ]
        assert len(saved_states) == 1
        assert saved_states[0]["compressed_through_message_id"] == 8
        assert saved_states[0]["summary"] == merged_summary
        assert context.messages[0] == {"role": "system", "content": "系统提示"}
        assert "完成 D5.7" in context.messages[1]["content"]
        assert context.messages[2:] == _without_ids(records[8:])
        assert context.conversation_messages == clean_messages
    finally:
        builtin.get_context_summary_state = original_get_state
        builtin.summarize_context = original_summarize
        builtin.upsert_context_summary_state = original_upsert


def test_capability_failure_keeps_old_cursor_messages_as_raw_text():
    _install_fake_retriever()

    import capabilities.builtin as builtin
    from capabilities.base import PipelineContext
    from infra.context_manager import ContextBudget, ContextSummary

    records = _build_records(6)
    records.append({"id": 13, "role": "user", "content": "当前问题"})
    clean_messages = _without_ids(records)
    previous_summary = ContextSummary(
        task_goal="完成 D5",
        completed_work=["已压缩消息 1 到 4"],
        key_decisions=[],
        file_states=[],
        constraints=[],
        failures=[],
        pending_work=[],
    )
    context = PipelineContext(
        messages=[{"role": "system", "content": "系统提示"}] + clean_messages,
        conversation_messages=[message.copy() for message in clean_messages],
        conversation_id=7,
        metadata={"conversation_records": records},
    )

    original_get_state = builtin.get_context_summary_state
    original_summarize = builtin.summarize_context
    original_upsert = builtin.upsert_context_summary_state
    try:
        builtin.get_context_summary_state = lambda conversation_id: {
            "summary_json": json.dumps(asdict(previous_summary), ensure_ascii=False),
            "compressed_through_message_id": 4,
        }
        builtin.summarize_context = lambda *args, **kwargs: None
        builtin.upsert_context_summary_state = lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("摘要失败时不能推进数据库游标")
        )

        capability = builtin.ContextCompressionCapability(
            keep_recent_turns=2,
            budget=ContextBudget(
                model_context_limit=100,
                reserved_output_tokens=10,
                compression_ratio=0.1,
            ),
        )
        capability.on_request(SimpleNamespace(), context)

        assert context.messages[0] == {"role": "system", "content": "系统提示"}
        assert "完成 D5" in context.messages[1]["content"]
        assert context.messages[2:] == _without_ids(records[4:])
        assert context.conversation_messages == clean_messages
    finally:
        builtin.get_context_summary_state = original_get_state
        builtin.summarize_context = original_summarize
        builtin.upsert_context_summary_state = original_upsert


def test_invalid_summary_budget_is_rejected():
    from infra.context_compressor import SummaryBudget

    invalid_configs = [
        {"model_context_limit": 0},
        {"reserved_output_tokens": 0},
        {"safety_margin_tokens": -1},
        {
            "model_context_limit": 100,
            "reserved_output_tokens": 80,
            "safety_margin_tokens": 20,
        },
    ]

    for config in invalid_configs:
        try:
            SummaryBudget(**config)
        except ValueError:
            continue
        raise AssertionError(f"非法摘要预算没有被拒绝: {config}")


if __name__ == "__main__":
    test_chunking_preserves_complete_turns_when_they_fit()
    test_oversized_message_is_split_without_losing_content()
    test_any_failed_chunk_discards_the_temporary_rolling_summary()
    test_empty_increment_reuses_summary_without_calling_llm()
    test_summary_larger_than_reserved_output_is_rejected()
    test_capability_only_merges_records_after_persisted_cursor()
    test_capability_failure_keeps_old_cursor_messages_as_raw_text()
    test_invalid_summary_budget_is_rejected()
    print("D5 context compression tests passed")
