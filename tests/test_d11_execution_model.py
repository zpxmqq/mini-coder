import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_run_context_creates_unique_run_and_keeps_parent():
    from core.execution import RunContext, RunStatus

    first = RunContext.create(conversation_id=7)
    child = RunContext.create(
        conversation_id=7,
        parent_run_id=first.run_id,
    )

    assert first.run_id.startswith("run_")
    assert child.run_id.startswith("run_")
    assert child.run_id != first.run_id
    assert child.parent_run_id == first.run_id
    assert child.status == RunStatus.RUNNING
    assert child.started_at.tzinfo is not None


def test_run_status_supports_confirmation_resume_and_terminal_state():
    from core.execution import RunContext, RunStatus

    started_at = datetime(2026, 7, 12, tzinfo=timezone.utc)
    finished_at = started_at + timedelta(seconds=2)
    run = RunContext.create(now=started_at)

    run.transition_to(RunStatus.NEEDS_CONFIRMATION)
    assert run.status == RunStatus.NEEDS_CONFIRMATION
    assert run.is_terminal is False

    run.transition_to(RunStatus.RUNNING)
    run.transition_to(RunStatus.COMPLETED, now=finished_at)

    assert run.status == RunStatus.COMPLETED
    assert run.finished_at == finished_at
    assert run.is_terminal is True

    try:
        run.transition_to(RunStatus.RUNNING)
    except ValueError as error:
        assert "completed" in str(error)
        return
    raise AssertionError("终态 Run 不应该重新转换为 running")


def test_run_context_rejects_itself_as_parent():
    from core.execution import RunContext

    try:
        RunContext(run_id="run_same", parent_run_id="run_same")
    except ValueError as error:
        assert "parent_run_id" in str(error)
        return
    raise AssertionError("Run 不应该把自己设置为父 Run")


def test_trace_event_validates_fields_and_serializes():
    from core.execution import TraceEvent, TraceEventType

    created_at = datetime(2026, 7, 12, 8, 30, tzinfo=timezone.utc)
    payload = {
        "path": "core/agent.py",
        "arguments": {"encoding": "utf-8"},
    }
    event = TraceEvent(
        run_id="run_123",
        sequence=2,
        event_type=TraceEventType.TOOL_COMPLETED,
        iteration=1,
        tool_call_id="call_1",
        tool_name="read_file",
        success=True,
        duration_ms=18,
        payload=payload,
        created_at=created_at,
    )

    payload["path"] = "外部修改不应影响事件"
    payload["arguments"]["encoding"] = "gbk"
    serialized = event.to_dict()

    assert event.payload == {
        "path": "core/agent.py",
        "arguments": {"encoding": "utf-8"},
    }
    assert serialized == {
        "run_id": "run_123",
        "sequence": 2,
        "event_type": "tool_completed",
        "iteration": 1,
        "tool_call_id": "call_1",
        "tool_name": "read_file",
        "success": True,
        "duration_ms": 18,
        "payload": {
            "path": "core/agent.py",
            "arguments": {"encoding": "utf-8"},
        },
        "created_at": "2026-07-12T08:30:00+00:00",
    }


def test_trace_event_rejects_invalid_sequence_iteration_and_duration():
    from core.execution import TraceEvent, TraceEventType

    invalid_values = [
        {"sequence": 0},
        {"sequence": 1, "iteration": 0},
        {"sequence": 1, "duration_ms": -1},
    ]

    for values in invalid_values:
        try:
            TraceEvent(
                run_id="run_invalid",
                event_type=TraceEventType.RUN_STARTED,
                **values,
            )
        except ValueError:
            continue
        raise AssertionError(f"非法 TraceEvent 没有被拒绝: {values}")


def test_memory_recorder_requires_continuous_sequence_per_run():
    from core.execution import (
        InMemoryTraceRecorder,
        TraceEvent,
        TraceEventType,
    )

    recorder = InMemoryTraceRecorder()
    first = TraceEvent(
        run_id="run_a",
        sequence=1,
        event_type=TraceEventType.RUN_STARTED,
    )
    second = TraceEvent(
        run_id="run_a",
        sequence=2,
        event_type=TraceEventType.LLM_CALL_STARTED,
        iteration=1,
    )
    another_run = TraceEvent(
        run_id="run_b",
        sequence=1,
        event_type=TraceEventType.RUN_STARTED,
    )

    recorder.record(first)
    recorder.record(another_run)
    recorder.record(second)

    assert recorder.get_events("run_a") == [first, second]
    assert recorder.get_events("run_b") == [another_run]

    try:
        recorder.record(
            TraceEvent(
                run_id="run_a",
                sequence=4,
                event_type=TraceEventType.RUN_COMPLETED,
            )
        )
    except ValueError as error:
        assert "应为 3" in str(error)
        return
    raise AssertionError("Recorder 不应该接受跳号的 sequence")


def test_null_recorder_accepts_valid_event_without_side_effects():
    from core.execution import NullTraceRecorder, TraceEvent, TraceEventType

    recorder = NullTraceRecorder()
    result = recorder.record(
        TraceEvent(
            run_id="run_no_trace",
            sequence=1,
            event_type=TraceEventType.RUN_STARTED,
        )
    )

    assert result is None


def test_trace_emitter_assigns_sequence_and_records_events():
    from core.execution import (
        InMemoryTraceRecorder,
        RunContext,
        TraceEmitter,
        TraceEventType,
    )

    run = RunContext.create()
    recorder = InMemoryTraceRecorder()
    emitter = TraceEmitter(run, recorder)

    first = emitter.emit(TraceEventType.RUN_STARTED)
    second = emitter.emit(
        TraceEventType.LLM_CALL_STARTED,
        iteration=1,
    )

    assert first.sequence == 1
    assert second.sequence == 2
    assert emitter.sequence == 2
    assert recorder.get_events(run.run_id) == [first, second]


def test_trace_emitter_does_not_advance_sequence_when_recording_fails():
    from core.execution import RunContext, TraceEmitter, TraceEventType

    class FailingRecorder:
        def record(self, event):
            raise RuntimeError("数据库暂时不可用")

    emitter = TraceEmitter(RunContext.create(), FailingRecorder())

    try:
        emitter.emit(TraceEventType.RUN_STARTED)
    except RuntimeError as error:
        assert "数据库暂时不可用" in str(error)
    else:
        raise AssertionError("Recorder 异常应该继续向上抛出")

    assert emitter.sequence == 0


if __name__ == "__main__":
    test_run_context_creates_unique_run_and_keeps_parent()
    test_run_status_supports_confirmation_resume_and_terminal_state()
    test_run_context_rejects_itself_as_parent()
    test_trace_event_validates_fields_and_serializes()
    test_trace_event_rejects_invalid_sequence_iteration_and_duration()
    test_memory_recorder_requires_continuous_sequence_per_run()
    test_null_recorder_accepts_valid_event_without_side_effects()
    test_trace_emitter_assigns_sequence_and_records_events()
    test_trace_emitter_does_not_advance_sequence_when_recording_fails()
    print("D11 execution model tests passed")
