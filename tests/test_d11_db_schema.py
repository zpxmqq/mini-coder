"""D11.1 MySQL 表结构测试。"""

import sys
from pathlib import Path

import pymysql


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_init_db_creates_run_and_trace_tables():
    """init_db 应创建 Run 主表和按顺序保存事件的 Trace 明细表。"""
    from infra.db import DB_CONFIG, init_db

    init_db()

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME IN ('agent_runs', 'trace_events')
            """
        )
        table_names = {row[0] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'trace_events'
              AND INDEX_NAME = 'uq_trace_events_run_sequence'
              AND NON_UNIQUE = 0
            """
        )
        unique_index_column_count = cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()

    assert table_names == {'agent_runs', 'trace_events'}
    assert unique_index_column_count == 2


if __name__ == "__main__":
    test_init_db_creates_run_and_trace_tables()
    print("D11 database schema test passed")
