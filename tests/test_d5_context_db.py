import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _delete_test_conversation(conversation_id: int) -> None:
    """只清理本测试创建的会话及其摘要、消息。"""
    import pymysql

    from infra.db import DB_CONFIG

    connection = pymysql.connect(**DB_CONFIG)
    cursor = connection.cursor()
    try:
        cursor.execute(
            "DELETE FROM conversation_context_summaries WHERE conversation_id = %s",
            (conversation_id,),
        )
        cursor.execute(
            "DELETE FROM messages WHERE conversation_id = %s",
            (conversation_id,),
        )
        cursor.execute(
            "DELETE FROM conversations WHERE id = %s",
            (conversation_id,),
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def test_context_summary_state_round_trip_with_mysql():
    """验证滚动摘要在真实 MySQL 中的首次写入、读取和增量更新。"""
    from infra.context_compressor import parse_context_summary
    from infra.context_manager import ContextSummary
    from infra.db import (
        add_message,
        create_conversation,
        get_context_summary_state,
        init_db,
        upsert_context_summary_state,
    )

    init_db()
    conversation_id = create_conversation("D5 context summary integration test")

    try:
        first_message_id = add_message(
            conversation_id,
            "user",
            "第一批需要压缩的测试消息",
        )
        first_summary = ContextSummary(
            task_goal="完成 D5 数据库集成测试",
            completed_work=["已保存第一版摘要"],
            key_decisions=["摘要和压缩游标原子更新"],
            file_states=[],
            constraints=["不能修改其他会话数据"],
            failures=[],
            pending_work=["验证第二版摘要"],
        )

        upsert_context_summary_state(
            conversation_id=conversation_id,
            summary=first_summary,
            compressed_through_message_id=first_message_id,
            source_token_count=1200,
            summary_token_count=180,
        )

        first_state = get_context_summary_state(conversation_id)
        assert first_state is not None
        assert parse_context_summary(first_state["summary_json"]) == first_summary
        assert first_state["compressed_through_message_id"] == first_message_id
        assert first_state["source_token_count"] == 1200
        assert first_state["summary_token_count"] == 180
        assert first_state["version"] == 1
        assert first_state["updated_at"] is not None

        second_message_id = add_message(
            conversation_id,
            "assistant",
            "第二批增量测试消息",
        )
        second_summary = ContextSummary(
            task_goal="完成 D5 数据库集成测试",
            completed_work=["已保存第一版摘要", "已合并第二批消息"],
            key_decisions=["摘要和压缩游标原子更新"],
            file_states=[],
            constraints=["不能修改其他会话数据"],
            failures=[],
            pending_work=[],
        )

        upsert_context_summary_state(
            conversation_id=conversation_id,
            summary=second_summary,
            compressed_through_message_id=second_message_id,
            source_token_count=2100,
            summary_token_count=230,
        )

        second_state = get_context_summary_state(conversation_id)
        assert second_state is not None
        assert parse_context_summary(second_state["summary_json"]) == second_summary
        assert second_state["compressed_through_message_id"] == second_message_id
        assert second_state["source_token_count"] == 2100
        assert second_state["summary_token_count"] == 230
        assert second_state["version"] == 2
    finally:
        _delete_test_conversation(conversation_id)

    assert get_context_summary_state(conversation_id) is None


if __name__ == "__main__":
    test_context_summary_state_round_trip_with_mysql()
    print("D5 MySQL context summary integration test passed")
