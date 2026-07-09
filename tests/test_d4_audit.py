import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_write_audit_event_appends_jsonl_record():
    from infra.audit import write_audit_event

    with TemporaryDirectory() as temp_dir:
        log_path = Path(temp_dir) / "security_audit.jsonl"

        write_audit_event(
            "tool_permission_denied",
            {
                "tool_name": "bash",
                "risk_level": "high",
                "allowed_risk": "low",
            },
            log_path=log_path,
        )

        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1

        record = json.loads(lines[0])
        assert record["event"] == "tool_permission_denied"
        assert record["tool_name"] == "bash"
        assert record["risk_level"] == "high"
        assert record["allowed_risk"] == "low"
        assert "created_at" in record


if __name__ == "__main__":
    test_write_audit_event_appends_jsonl_record()
    print("D4 audit tests passed")
