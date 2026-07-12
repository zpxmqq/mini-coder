"""Agent 执行过程的领域模型，不依赖数据库和 Web 框架。"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol
from copy import deepcopy
import uuid


def current_time() -> datetime:
    """返回带 UTC 时区的当前时间，避免不同机器上的本地时区歧义。"""
    return datetime.now(timezone.utc)


class RunStatus(StrEnum):
    """一次 Agent Run 的总体状态。"""

    RUNNING = "running"
    NEEDS_CONFIRMATION = "needs_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_RUN_STATUSES = {
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}


ALLOWED_RUN_TRANSITIONS = {
    RunStatus.RUNNING: {
        RunStatus.NEEDS_CONFIRMATION,
        RunStatus.COMPLETED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.NEEDS_CONFIRMATION: {
        RunStatus.RUNNING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.COMPLETED: set(),
    RunStatus.FAILED: set(),
    RunStatus.CANCELLED: set(),
}


@dataclass
class RunContext:
    """
    描述一次完整 Agent 请求的身份和总体状态。

    run_id：当前请求的唯一编号。
    parent_run_id：可选的父 Run，为后续主从 Agent 建立调用树。
    conversation_id：当前请求所属会话；创建 Run 时可能还没有会话 ID。
    """

    run_id: str
    status: RunStatus = RunStatus.RUNNING
    parent_run_id: str | None = None
    conversation_id: int | None = None
    started_at: datetime = field(default_factory=current_time)
    finished_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id 不能为空")
        if self.parent_run_id is not None and not self.parent_run_id.strip():
            raise ValueError("parent_run_id 不能为空字符串")
        if self.parent_run_id == self.run_id:
            raise ValueError("parent_run_id 不能等于 run_id")
        if not isinstance(self.status, RunStatus):
            raise ValueError("status 必须是 RunStatus")
        if self.started_at.tzinfo is None:
            raise ValueError("started_at 必须包含时区")
        if self.finished_at is not None and self.finished_at.tzinfo is None:
            raise ValueError("finished_at 必须包含时区")

    @classmethod
    def create(
        cls,
        conversation_id: int | None = None,
        parent_run_id: str | None = None,
        now: datetime | None = None,
    ) -> "RunContext":
        """创建一条处于 running 状态的新 Run。"""
        return cls(
            run_id=f"run_{uuid.uuid4().hex}",
            conversation_id=conversation_id,
            parent_run_id=parent_run_id,
            started_at=now or current_time(),
        )

    @property
    def is_terminal(self) -> bool:
        """返回当前 Run 是否已经进入不可恢复的终态。"""
        return self.status in TERMINAL_RUN_STATUSES

    def transition_to(
        self,
        new_status: RunStatus,
        now: datetime | None = None,
    ) -> None:
        """校验并执行状态转换；非法转换直接抛出 ValueError。"""
        if not isinstance(new_status, RunStatus):
            raise ValueError("new_status 必须是 RunStatus")
        if new_status == self.status:
            return
        if new_status not in ALLOWED_RUN_TRANSITIONS[self.status]:
            raise ValueError(
                f"不允许从 {self.status.value} 转换到 {new_status.value}"
            )

        self.status = new_status
        if new_status in TERMINAL_RUN_STATUSES:
            self.finished_at = now or current_time()
        else:
            self.finished_at = None


class TraceEventType(StrEnum):
    """D11 当前允许记录的结构化执行事件。"""

    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
    RUN_NEEDS_CONFIRMATION = "run_needs_confirmation"

    CAPABILITY_STARTED = "capability_started"
    CAPABILITY_COMPLETED = "capability_completed"
    CAPABILITY_SHORT_CIRCUITED = "capability_short_circuited"
    CAPABILITY_FAILED = "capability_failed"

    LLM_CALL_STARTED = "llm_call_started"
    LLM_CALL_COMPLETED = "llm_call_completed"
    LLM_CALL_FAILED = "llm_call_failed"

    TOOL_REQUESTED = "tool_requested"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    TOOL_UNKNOWN = "tool_unknown"
    TOOL_ARGUMENTS_INVALID = "tool_arguments_invalid"
    TOOL_PERMISSION_DENIED = "tool_permission_denied"
    TOOL_CONFIRMATION_REQUESTED = "tool_confirmation_requested"
    TOOL_CONFIRMATION_APPROVED = "tool_confirmation_approved"
    TOOL_CONFIRMATION_REJECTED = "tool_confirmation_rejected"

    MAX_ITERATIONS_REACHED = "max_iterations_reached"


@dataclass(frozen=True)
class TraceEvent:
    """
    一次 Run 中按顺序发生的一件执行事实。

    sequence 是整个 Run 内的事件顺序；iteration 是 ReAct 循环轮次，
    二者含义不同。没有进入 ReAct 循环的事件可以不传 iteration。
    """

    run_id: str
    sequence: int
    event_type: TraceEventType
    iteration: int | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    success: bool | None = None
    duration_ms: int | None = None
    payload: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=current_time)

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id 不能为空")
        if self.sequence < 1:
            raise ValueError("sequence 必须从 1 开始")
        if not isinstance(self.event_type, TraceEventType):
            raise ValueError("event_type 必须是 TraceEventType")
        if self.iteration is not None and self.iteration < 1:
            raise ValueError("iteration 必须从 1 开始")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms 不能小于 0")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at 必须包含时区")
        if not isinstance(self.payload, dict):
            raise ValueError("payload 必须是 dict")

        # frozen dataclass 仍允许在初始化阶段深拷贝，隔离嵌套参数和结果。
        object.__setattr__(self, "payload", deepcopy(self.payload))

    def to_dict(self) -> dict:
        """转换为可 JSON 序列化的字典，供后续 MySQL 和 SSE 复用。"""
        return {
            "run_id": self.run_id,
            "sequence": self.sequence,
            "event_type": self.event_type.value,
            "iteration": self.iteration,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "payload": deepcopy(self.payload),
            "created_at": self.created_at.isoformat(),
        }


class TraceRecorder(Protocol):
    """执行核心依赖的最小记录接口。"""

    def record(self, event: TraceEvent) -> None:
        """保存一条已经校验过的 TraceEvent。"""
        ...


class NullTraceRecorder:
    """默认空实现：不开启 Trace 时保持现有 Agent 行为。"""

    def record(self, event: TraceEvent) -> None:
        return None


class InMemoryTraceRecorder:
    """测试和本地调试使用的内存 Recorder。"""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []#保存所有事件
        self._last_sequence_by_run: dict[str, int] = {}#只保存事件的序号

    def record(self, event: TraceEvent) -> None:
        expected_sequence = self._last_sequence_by_run.get(event.run_id, 0) + 1
        if event.sequence != expected_sequence:
            raise ValueError(
                f"Run {event.run_id} 的下一条 sequence 应为 "
                f"{expected_sequence}，实际为 {event.sequence}"
            )

        self._events.append(event)
        self._last_sequence_by_run[event.run_id] = event.sequence

    def get_events(self, run_id: str) -> list[TraceEvent]:
        """按写入顺序返回指定 Run 的事件副本。"""
        return [event for event in self._events if event.run_id == run_id]


class TraceEmitter:
    """
    为一个 Run 创建连续编号的事件，并交给 Recorder 保存。

    Agent 只需要调用 emit(event_type, ...)，不需要自己维护 sequence。
    initial_sequence 用于人工确认恢复等需要从已有轨迹继续编号的场景。
    """

    def __init__(
        self,
        run: RunContext,
        recorder: TraceRecorder | None = None,
        initial_sequence: int = 0,
    ) -> None:
        if initial_sequence < 0:
            raise ValueError("initial_sequence 不能小于 0")

        self.run = run
        self.recorder = recorder or NullTraceRecorder()
        self._sequence = initial_sequence

    @property
    def sequence(self) -> int:
        """返回最后一条已经成功保存的事件序号。"""
        return self._sequence

    def emit(
        self,
        event_type: TraceEventType,
        *,
        iteration: int | None = None,
        tool_call_id: str | None = None,
        tool_name: str | None = None,
        success: bool | None = None,
        duration_ms: int | None = None,
        payload: dict | None = None,
        created_at: datetime | None = None,
    ) -> TraceEvent:
        """创建并保存下一条事件；保存失败时不推进 sequence。"""
        event = TraceEvent(
            run_id=self.run.run_id,
            sequence=self._sequence + 1,
            event_type=event_type,
            iteration=iteration,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            success=success,
            duration_ms=duration_ms,
            payload=payload or {},
            created_at=created_at or current_time(),
        )
        self.recorder.record(event)
        self._sequence = event.sequence
        return event
