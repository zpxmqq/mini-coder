"""Run 和 TraceEvent 的 MySQL 持久化实现。"""

import json
from datetime import datetime, timezone

import pymysql

from core.execution import RunContext, RunStatus, TraceEvent, TraceEventType
from infra.db import DB_CONFIG


MAX_PAYLOAD_STRING_LENGTH = 4000
TRUNCATION_MARKER = "...[已截断]"
SENSITIVE_FIELD_NAMES = {
    "password",
    "passwd",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "authorization",
    "secret",
    "client_secret",
}
SENSITIVE_FIELD_SUFFIXES = (
    "_password",
    "_token",
    "_api_key",
    "_authorization",
    "_secret",
)


def _to_mysql_datetime(value: datetime | None) -> datetime | None:
    """
    把领域模型中的带时区时间转换为 MySQL DATETIME 使用的 UTC 无时区时间。

    输入：带时区的 datetime，或者 None。
    输出：表示同一时刻的 UTC 无时区 datetime，或者 None。
    """
    if value is None:
        return None
    if value.utcoffset() is None:
        raise ValueError("写入 MySQL 的 datetime 必须包含时区")
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _from_mysql_datetime(value: datetime | None) -> datetime | None:
    """
    把 MySQL DATETIME 还原为领域模型使用的 UTC 时间。

    输入：MySQL 返回的无时区 datetime，或者 None。
    输出：带 UTC 时区的 datetime，或者 None。
    """
    if value is None:
        return None
    if value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_sensitive_field(field_name: str) -> bool:
    """判断一个 payload 字段名是否可能承载凭据或密钥。"""
    normalized_name = field_name.strip().lower().replace("-", "_")
    return (
        normalized_name in SENSITIVE_FIELD_NAMES
        or normalized_name.endswith(SENSITIVE_FIELD_SUFFIXES)
    )


def _sanitize_payload_value(value):
    """
    递归生成适合持久化的 payload 副本。

    将payload可能的形式分为三类，三类分别进行处理
    输入：payload 中任意层级的字典、列表、元组或基础值。
    输出：敏感字段已替换、过长字符串已截断的新数据，不修改原始对象。
    """
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if isinstance(key, str) and _is_sensitive_field(key):
                sanitized[key] = "***"
            else:
                sanitized[key] = _sanitize_payload_value(item)
        return sanitized

    if isinstance(value, (list, tuple)):
        return [_sanitize_payload_value(item) for item in value]

    if isinstance(value, str) and len(value) > MAX_PAYLOAD_STRING_LENGTH:
        content_length = MAX_PAYLOAD_STRING_LENGTH - len(TRUNCATION_MARKER)
        return value[:content_length] + TRUNCATION_MARKER

    return value


class MySQLTraceRepository:
    """负责在 Run/TraceEvent 领域对象和 MySQL 表之间转换数据。"""

    def __init__(self, db_config: dict | None = None) -> None:
        """保存数据库配置副本，避免外部后续修改影响当前 Repository。"""
        self.db_config = dict(DB_CONFIG if db_config is None else db_config)

    def create_run(self, run: RunContext) -> None:
        """
        把一条新的 RunContext 写入 agent_runs。

        输入：已经通过领域模型校验的 RunContext。
        输出：无；写入失败时回滚事务并继续向上抛出数据库异常。
        """
        conn = pymysql.connect(**self.db_config)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agent_runs (
                        run_id,
                        conversation_id,
                        parent_run_id,
                        status,
                        started_at,
                        finished_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run.run_id,
                        run.conversation_id,
                        run.parent_run_id,
                        run.status.value,
                        _to_mysql_datetime(run.started_at),
                        _to_mysql_datetime(run.finished_at),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record(self, event: TraceEvent) -> None:
        """
        清理并保存一条 TraceEvent，使 Repository 可以作为 TraceRecorder 使用。

        输入：TraceEmitter 已经组装并校验完成的 TraceEvent。
        输出：无；序列化或写入失败时回滚，并把异常继续向上抛出。
        """
        sanitized_payload = _sanitize_payload_value(event.payload)
        payload_json = json.dumps(sanitized_payload, ensure_ascii=False)

        conn = pymysql.connect(**self.db_config)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO trace_events (
                        run_id,
                        sequence,
                        event_type,
                        iteration,
                        tool_call_id,
                        tool_name,
                        success,
                        duration_ms,
                        payload,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event.run_id,
                        event.sequence,
                        event.event_type.value,
                        event.iteration,
                        event.tool_call_id,
                        event.tool_name,
                        event.success,
                        event.duration_ms,
                        payload_json,
                        _to_mysql_datetime(event.created_at),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_run(self, run: RunContext) -> None:
        """
        把 RunContext 的最新状态和结束时间同步到 agent_runs。

        输入：已经完成合法状态转换的 RunContext。
        输出：无；更新失败时回滚事务并继续向上抛出数据库异常。
        """
        conn = pymysql.connect(**self.db_config)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE agent_runs
                    SET status = %s,
                        finished_at = %s
                    WHERE run_id = %s
                    """,
                    (
                        run.status.value,
                        _to_mysql_datetime(run.finished_at),
                        run.run_id,
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_run(self, run_id: str) -> RunContext | None:
        """
        根据 run_id 查询并恢复一条 RunContext。

        输入：需要查询的 Run 唯一编号。
        输出：找到时返回 RunContext，不存在时返回 None。
        """
        conn = pymysql.connect(**self.db_config)
        try:
            with conn.cursor() as cursor:
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
                    (run_id,),
                )
                row = cursor.fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        return RunContext(
            run_id=row[0],
            conversation_id=row[1],
            parent_run_id=row[2],
            status=RunStatus(row[3]),
            started_at=_from_mysql_datetime(row[4]),
            finished_at=_from_mysql_datetime(row[5]),
        )

    def get_events(self, run_id: str) -> list[TraceEvent]:
        """
        按事件序号查询并恢复一个 Run 的全部 TraceEvent。

        输入：需要查询的 Run 唯一编号。
        输出：按 sequence 升序排列的 TraceEvent 列表；没有事件时返回空列表。
        """
        conn = pymysql.connect(**self.db_config)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT run_id,
                           sequence,
                           event_type,
                           iteration,
                           tool_call_id,
                           tool_name,
                           success,
                           duration_ms,
                           payload,
                           created_at
                    FROM trace_events
                    WHERE run_id = %s
                    ORDER BY sequence
                    """,
                    (run_id,),
                )
                rows = cursor.fetchall()
        finally:
            conn.close()

        events = []
        for row in rows:
            payload_json = row[8]
            if isinstance(payload_json, bytes):
                payload_json = payload_json.decode("utf-8")

            events.append(
                TraceEvent(
                    run_id=row[0],
                    sequence=row[1],
                    event_type=TraceEventType(row[2]),
                    iteration=row[3],
                    tool_call_id=row[4],
                    tool_name=row[5],
                    success=None if row[6] is None else bool(row[6]),
                    duration_ms=row[7],
                    payload=json.loads(payload_json),
                    created_at=_from_mysql_datetime(row[9]),
                )
            )
        return events
