import json
from datetime import datetime, timezone
from pathlib import Path


AUDIT_LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "security_audit.jsonl"


def write_audit_event(event: str, payload: dict | None = None, log_path: str | Path | None = None) -> None:
    """把安全审计事件追加写入 JSONL 日志文件。"""
    target = Path(log_path) if log_path is not None else AUDIT_LOG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "event": event,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload:
        record.update(payload)

    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
