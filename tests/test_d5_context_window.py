import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _build_completed_turns(count: int) -> list[dict]:
    messages = []
    for index in range(1, count + 1):
        messages.extend([
            {"role": "user", "content": f"问题{index}"},
            {"role": "assistant", "content": f"回答{index}"},
        ])
    return messages


def test_old_turns_are_compressible_and_recent_turns_are_preserved():
    from infra.context_manager import split_context_window

    messages = _build_completed_turns(6)
    messages.append({"role": "user", "content": "当前问题"})

    window = split_context_window(messages, keep_recent_turns=2)

    assert window.compressible_messages == _build_completed_turns(4)
    assert window.recent_messages == _build_completed_turns(6)[8:]
    assert window.current_user_message == {
        "role": "user",
        "content": "当前问题",
    }


def test_short_history_does_not_create_compressible_messages():
    from infra.context_manager import split_context_window

    history = _build_completed_turns(2)
    messages = history + [{"role": "user", "content": "当前问题"}]

    window = split_context_window(messages, keep_recent_turns=4)

    assert window.compressible_messages == []
    assert window.recent_messages == history
    assert window.current_user_message["content"] == "当前问题"


def test_last_assistant_is_not_mistaken_for_current_user():
    from infra.context_manager import split_context_window

    messages = _build_completed_turns(3)

    window = split_context_window(messages, keep_recent_turns=1)

    assert window.compressible_messages == _build_completed_turns(2)
    assert window.recent_messages == _build_completed_turns(3)[4:]
    assert window.current_user_message is None


def test_unmatched_leading_message_is_preserved_in_recent_messages():
    from infra.context_manager import split_context_window

    orphan_message = {"role": "assistant", "content": "缺少对应 user 的旧回答"}
    messages = [orphan_message] + _build_completed_turns(3)
    messages.append({"role": "user", "content": "当前问题"})

    window = split_context_window(messages, keep_recent_turns=1)

    assert window.compressible_messages == _build_completed_turns(2)
    assert window.recent_messages == [orphan_message] + _build_completed_turns(3)[4:]


def test_window_results_do_not_share_message_dicts_with_input():
    from infra.context_manager import split_context_window

    messages = _build_completed_turns(3)
    messages.append({"role": "user", "content": "当前问题"})

    window = split_context_window(messages, keep_recent_turns=1)
    window.compressible_messages[0]["content"] = "修改后的问题"
    window.recent_messages[0]["content"] = "修改后的最近问题"
    window.current_user_message["content"] = "修改后的当前问题"

    assert messages[0]["content"] == "问题1"
    assert messages[4]["content"] == "问题3"
    assert messages[-1]["content"] == "当前问题"


def test_invalid_keep_recent_turns_is_rejected():
    from infra.context_manager import split_context_window

    try:
        split_context_window([], keep_recent_turns=0)
    except ValueError:
        return
    raise AssertionError("keep_recent_turns=0 应该被拒绝")


if __name__ == "__main__":
    test_old_turns_are_compressible_and_recent_turns_are_preserved()
    test_short_history_does_not_create_compressible_messages()
    test_last_assistant_is_not_mistaken_for_current_user()
    test_unmatched_leading_message_is_preserved_in_recent_messages()
    test_window_results_do_not_share_message_dicts_with_input()
    test_invalid_keep_recent_turns_is_rejected()
    print("D5 context window tests passed")
