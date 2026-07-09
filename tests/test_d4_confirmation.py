import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_low_risk_tool_does_not_need_confirmation():
    from infra.security import needs_confirmation

    assert needs_confirmation("low") is False


def test_medium_and_high_risk_tools_need_confirmation():
    from infra.security import needs_confirmation

    assert needs_confirmation("medium") is True
    assert needs_confirmation("high") is True


def test_build_confirmation_request_contains_tool_metadata_and_arguments():
    from core.agent import build_confirmation_request

    tool = SimpleNamespace(name="edit_file", risk_level="medium")
    tool_call = SimpleNamespace(id="call_123")
    args = {
        "path": "core/tool.py",
        "old_string": "old",
        "new_string": "new",
    }

    request = build_confirmation_request(tool_call, tool, args)

    assert request == {
        "status": "needs_confirmation",
        "tool_call_id": "call_123",
        "tool_name": "edit_file",
        "arguments": args,
        "risk_level": "medium",
    }

def test_run_returns_confirmation_request_for_medium_risk_tool_when_enabled():
    import core.agent as agent

    original_chat = agent.chat_with_deepseek
    original_audit = agent.write_audit_event
    calls = []

    class FakeFunction:
        name = "edit_file"
        arguments = '{"path": "demo.txt", "old_string": "old", "new_string": "new"}'

    class FakeToolCall:
        id = "call_edit_1"
        function = FakeFunction()

    class FakeMessage:
        content = None
        tool_calls = [FakeToolCall()]

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    def fake_chat(messages, tools=None):
        calls.append((messages, tools))
        return FakeResponse()

    agent.chat_with_deepseek = fake_chat
    agent.write_audit_event = lambda event, payload=None: None
    try:
        result = agent.run(
            [{"role": "user", "content": "edit demo.txt"}],
            require_confirmation=True,
        )
    finally:
        agent.chat_with_deepseek = original_chat
        agent.write_audit_event = original_audit

    confirmation_id = result.pop("confirmation_id")
    assert confirmation_id.startswith("confirm_")
    assert confirmation_id in agent.PENDING_CONFIRMATIONS
    agent.PENDING_CONFIRMATIONS.pop(confirmation_id, None)
    assert result == {
        "status": "needs_confirmation",
        "tool_call_id": "call_edit_1",
        "tool_name": "edit_file",
        "arguments": {
            "path": "demo.txt",
            "old_string": "old",
            "new_string": "new",
        },
        "risk_level": "medium",
    }
    assert len(calls) == 1

if __name__ == "__main__":
    test_low_risk_tool_does_not_need_confirmation()
    test_medium_and_high_risk_tools_need_confirmation()
    test_build_confirmation_request_contains_tool_metadata_and_arguments()
    test_run_returns_confirmation_request_for_medium_risk_tool_when_enabled()
    print("D4 confirmation tests passed")
