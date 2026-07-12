import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_context_summary_stores_structured_fields():
    from infra.context_manager import ContextSummary

    summary = ContextSummary(
        task_goal="完成 D5 上下文压缩",
        completed_work=["完成 token 估算"],
        key_decisions=["最近四轮保留原文"],
        file_states=["infra/context_manager.py 已完成窗口切分"],
        constraints=["不修改 core/agent.py"],
        failures=["第一次摘要输出不是合法 JSON"],
        pending_work=["接入 ContextCompressionCapability"],
    )

    assert summary.task_goal == "完成 D5 上下文压缩"
    assert summary.completed_work == ["完成 token 估算"]
    assert summary.key_decisions == ["最近四轮保留原文"]
    assert summary.file_states == ["infra/context_manager.py 已完成窗口切分"]
    assert summary.constraints == ["不修改 core/agent.py"]
    assert summary.failures == ["第一次摘要输出不是合法 JSON"]
    assert summary.pending_work == ["接入 ContextCompressionCapability"]


if __name__ == "__main__":
    test_context_summary_stores_structured_fields()
    print("D5 context summary tests passed")
