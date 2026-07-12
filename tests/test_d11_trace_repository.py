"""D11.1 Trace Repository 的真实 MySQL 集成测试。"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymysql


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_create_run_persists_run_context():
    """create_run 应把 RunContext 的基础字段写入 agent_runs。"""
    from core.execution import RunContext
    from infra.db import DB_CONFIG, init_db
    from infra.trace_repository import MySQLTraceRepository

    init_db()
    started_at = datetime(2026, 7, 12, 9, 30, 15, 123456, tzinfo=timezone.utc)
    run = RunContext.create(now=started_at)
    repository = MySQLTraceRepository()

    try:
        repository.create_run(run)

        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT run_id,
                       conversation_id,
                       parent_run_id,
                       status,
                       started_at,
                       finished_at
                FROM agent_runs
                WHERE run_id = %s
                """,
                (run.run_id,),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        assert row == (
            run.run_id,
            None,
            None,
            "running",
            started_at.replace(tzinfo=None),
            None,
        )
    finally:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM agent_runs WHERE run_id = %s", (run.run_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()


def test_record_persists_sanitized_trace_event():
    """record 应保存事件，并在写入前脱敏和截断 payload。"""
    from core.execution import RunContext, TraceEmitter, TraceEventType
    from infra.db import DB_CONFIG, init_db
    from infra.trace_repository import MySQLTraceRepository

    init_db()
    run = RunContext.create()
    repository = MySQLTraceRepository()
    repository.create_run(run)
    long_output = "x" * 4100

    try:
        emitter = TraceEmitter(run, recorder=repository)
        event = emitter.emit(
            TraceEventType.TOOL_COMPLETED,
            iteration=1,
            tool_call_id="call_repository_test",
            tool_name="read_file",
            success=True,
            duration_ms=25,
            payload={
                "path": "core/agent.py",
                "credentials": {
                    "api_key": "should-not-be-stored",
                    "token_count": 120,
                },
                "output": long_output,
            },
        )

        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT sequence,
                       event_type,
                       iteration,
                       tool_call_id,
                       tool_name,
                       success,
                       duration_ms,
                       payload
                FROM trace_events
                WHERE run_id = %s
                """,
                (run.run_id,),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        stored_payload = json.loads(row[7])
        assert row[:7] == (
            1,
            "tool_completed",
            1,
            "call_repository_test",
            "read_file",
            1,
            25,
        )
        assert stored_payload["path"] == "core/agent.py"
        assert stored_payload["credentials"] == {
            "api_key": "***",
            "token_count": 120,
        }
        assert len(stored_payload["output"]) <= 4000
        assert stored_payload["output"].endswith("...[已截断]")

        # Repository 只能清理待落库的副本，不能修改已经发出的领域事件。
        assert event.payload["credentials"]["api_key"] == "should-not-be-stored"
        assert event.payload["output"] == long_output
    finally:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            # trace_events 使用 ON DELETE CASCADE，因此只需要删除父 Run。
            cursor.execute("DELETE FROM agent_runs WHERE run_id = %s", (run.run_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()


def test_update_run_persists_confirmation_and_completion():
    """update_run 应同步非终态和终态，并只为终态保存结束时间。"""
    from core.execution import RunContext, RunStatus
    from infra.db import DB_CONFIG, init_db
    from infra.trace_repository import MySQLTraceRepository

    init_db()
    started_at = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)
    finished_at = datetime(2026, 7, 12, 10, 0, 3, tzinfo=timezone.utc)
    run = RunContext.create(now=started_at)
    repository = MySQLTraceRepository()
    repository.create_run(run)

    try:
        run.transition_to(RunStatus.NEEDS_CONFIRMATION)
        repository.update_run(run)

        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT status, finished_at FROM agent_runs WHERE run_id = %s",
                (run.run_id,),
            )
            confirmation_row = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        assert confirmation_row == ("needs_confirmation", None)

        run.transition_to(RunStatus.RUNNING)
        run.transition_to(RunStatus.COMPLETED, now=finished_at)
        repository.update_run(run)

        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT status, finished_at FROM agent_runs WHERE run_id = %s",
                (run.run_id,),
            )
            completed_row = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        assert completed_row == (
            "completed",
            finished_at.replace(tzinfo=None),
        )
    finally:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM agent_runs WHERE run_id = %s", (run.run_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()


def test_get_run_restores_domain_model_and_returns_none_when_missing():
    """get_run 应恢复 RunContext，找不到 run_id 时返回 None。"""
    from core.execution import RunContext, RunStatus
    from infra.db import DB_CONFIG, init_db
    from infra.trace_repository import MySQLTraceRepository

    init_db()
    started_at = datetime(2026, 7, 12, 11, 0, tzinfo=timezone.utc)
    finished_at = datetime(2026, 7, 12, 11, 0, 5, tzinfo=timezone.utc)
    run = RunContext.create(now=started_at)
    repository = MySQLTraceRepository()
    repository.create_run(run)

    try:
        run.transition_to(RunStatus.COMPLETED, now=finished_at)
        repository.update_run(run)

        assert repository.get_run(run.run_id) == run
        assert repository.get_run("run_does_not_exist") is None
    finally:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM agent_runs WHERE run_id = %s", (run.run_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()


def test_get_events_restores_events_in_sequence_order():
    """get_events 应按 sequence 返回重新构造的 TraceEvent 列表。"""
    from core.execution import RunContext, TraceEmitter, TraceEventType
    from infra.db import DB_CONFIG, init_db
    from infra.trace_repository import MySQLTraceRepository

    init_db()
    run = RunContext.create()
    repository = MySQLTraceRepository()
    repository.create_run(run)

    try:
        emitter = TraceEmitter(run, recorder=repository)
        first = emitter.emit(
            TraceEventType.RUN_STARTED,
            payload={"source": "test"},
            created_at=datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc),
        )
        second = emitter.emit(
            TraceEventType.TOOL_FAILED,
            iteration=1,
            tool_call_id="call_failed",
            tool_name="read_file",
            success=False,
            duration_ms=7,
            payload={"error_type": "file_not_found"},
            created_at=datetime(2026, 7, 12, 12, 0, 1, tzinfo=timezone.utc),
        )

        assert repository.get_events(run.run_id) == [first, second]
        assert repository.get_events("run_does_not_exist") == []
    finally:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM agent_runs WHERE run_id = %s", (run.run_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    test_create_run_persists_run_context()
    test_record_persists_sanitized_trace_event()
    test_update_run_persists_confirmation_and_completion()
    test_get_run_restores_domain_model_and_returns_none_when_missing()
    test_get_events_restores_events_in_sequence_order()
    print("D11 trace repository tests passed")
