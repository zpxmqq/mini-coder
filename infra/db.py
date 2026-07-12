"""mini-coder 的 MySQL 持久化模块。"""

import pymysql
import json
from dataclasses import asdict

from infra.context_manager import ContextSummary

DB_CONFIG = {
      "host": "127.0.0.1",
      "port": 3306,
      "user": "mini_coder",
      "password": "mini_coder_2026",
      "database": "mini_coder",
      "charset": "utf8mb4",
  }


def _memory_column_exists(cursor, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'memories'
          AND COLUMN_NAME = %s
        """,
        (column_name,),
    )
    return cursor.fetchone()[0] > 0


def _add_memory_column_if_missing(cursor, column_name: str, column_definition: str) -> None:
    if _memory_column_exists(cursor, column_name):
        return
    cursor.execute(f"ALTER TABLE memories ADD COLUMN {column_name} {column_definition}")


def init_db() -> None:
    """初始化数据库：创建表（如果不存在）。

    核心表的职责：
    - conversations：存储对话会话
    - messages：存储会话中的具体消息，通过 conversation_id 关联到 conversations
    - agent_runs：存储每次 Agent 请求的身份和总体状态
    - trace_events：按顺序存储一次 Run 内发生的执行事件
    """
    conn = pymysql.connect(**DB_CONFIG)          # 连接到 MySQL 数据库（不存在会自动创建）
    cursor = conn.cursor()                   # cursor 就是“在数据库里执行 SQL 的游标”

    # 建「对话表」：存每一次对话会话的基本信息
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,       -- 编号（主键，自动递增，唯一标识一行）
            title VARCHAR(255) DEFAULT '',               -- 标题（默认空字符串）
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- 创建时间（自动填当前时间）
        )
    """)

    # 建「消息表」：存每条消息，通过 conversation_id 关联到上面的对话表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,       -- 编号（主键，自动递增）
            conversation_id INTEGER NOT NULL,            -- 所属对话编号（必填）
            role TEXT NOT NULL,                          -- 角色（必填，user/assistant/system/tool）
            content TEXT NOT NULL,                       -- 内容（必填，消息正文）
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 创建时间（自动填当前时间）
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)  -- 外键约束：conversation_id 必须真实存在
        )
    """)

    # 建「Agent Run 表」：一行对应一次完整的 Agent 请求。
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_runs (
            run_id VARCHAR(80) PRIMARY KEY,
            conversation_id INTEGER NULL,
            parent_run_id VARCHAR(80) NULL,
            status VARCHAR(32) NOT NULL,
            started_at DATETIME(6) NOT NULL,
            finished_at DATETIME(6) NULL,
            CONSTRAINT chk_agent_runs_status CHECK (
                status IN (
                    'running',
                    'needs_confirmation',
                    'completed',
                    'failed',
                    'cancelled'
                )
            ),
            CONSTRAINT fk_agent_runs_conversation
                FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            CONSTRAINT fk_agent_runs_parent
                FOREIGN KEY (parent_run_id) REFERENCES agent_runs(run_id),
            INDEX idx_agent_runs_conversation (conversation_id),
            INDEX idx_agent_runs_parent (parent_run_id),
            INDEX idx_agent_runs_status_started (status, started_at)
        )
    """)

    # 建「Trace 事件表」：同一个 Run 内的 sequence 必须从 1 开始且不能重复。
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trace_events (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            run_id VARCHAR(80) NOT NULL,
            sequence INTEGER NOT NULL,
            event_type VARCHAR(64) NOT NULL,
            iteration INTEGER NULL,
            tool_call_id VARCHAR(255) NULL,
            tool_name VARCHAR(255) NULL,
            success BOOLEAN NULL,
            duration_ms INTEGER NULL,
            payload JSON NOT NULL,
            created_at DATETIME(6) NOT NULL,
            CONSTRAINT chk_trace_events_sequence CHECK (sequence >= 1),
            CONSTRAINT chk_trace_events_iteration CHECK (
                iteration IS NULL OR iteration >= 1
            ),
            CONSTRAINT chk_trace_events_duration CHECK (
                duration_ms IS NULL OR duration_ms >= 0
            ),
            CONSTRAINT fk_trace_events_run
                FOREIGN KEY (run_id) REFERENCES agent_runs(run_id)
                ON DELETE CASCADE,
            CONSTRAINT uq_trace_events_run_sequence
                UNIQUE (run_id, sequence),
            INDEX idx_trace_events_type_created (event_type, created_at)
        )
    """)

    # 建「滚动摘要表」：保存结构化摘要及其覆盖到的最后一条原始消息。
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_context_summaries (
            conversation_id INTEGER PRIMARY KEY,
            summary_json JSON NOT NULL,
            compressed_through_message_id INTEGER NOT NULL,
            source_token_count INTEGER DEFAULT 0,
            summary_token_count INTEGER DEFAULT 0,
            version INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
            FOREIGN KEY (compressed_through_message_id) REFERENCES messages(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            conversation_id INTEGER,
            content TEXT NOT NULL,
            embedding JSON,
            memory_type VARCHAR(50) DEFAULT 'fact',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP NULL,
            access_count INTEGER DEFAULT 0,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
""")

    _add_memory_column_if_missing(
        cursor,
        "updated_at",
        "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
    )
    _add_memory_column_if_missing(cursor, "last_used_at", "TIMESTAMP NULL")
    _add_memory_column_if_missing(cursor, "access_count", "INTEGER DEFAULT 0")
    
    conn.commit()   # 提交所有操作
    conn.close()    # 关闭连接

def add_message(conversation_id: int, role: str, content: str) -> int:
    """
    输入为信息的ID，以及messages的角色，内容。向messages表中插入一条消息，
    返回这个信息的ID
    """
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)", 
        (conversation_id, role, content)
        )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id

def create_conversation(title: str = "") ->int:
    """创建一个新的对话，并返回该对话的ID"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (title) VALUES (%s)", 
        (title,)
        )
    conn.commit()
    conv_id = cursor.lastrowid
    conn.close()
    return conv_id

def get_message_records(conversation_id: int) -> list[dict]:
    """按消息 ID 顺序返回带数据库 ID 的原始消息记录。"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, role, content FROM messages WHERE conversation_id = %s ORDER BY id",
        (conversation_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    records = []
    for row in rows:
        records.append({
            "id": row[0],
            "role": row[1],
            "content": row[2],
        })
    return records


def get_messages(conversation_id: int) -> list[dict]:
    """输入一个对话ID查出一个对话的所有消息，按时间顺序返回。"""
    return [
        {
            "role": record["role"],
            "content": record["content"],
        }
        for record in get_message_records(conversation_id)
    ]


def get_context_summary_state(conversation_id: int) -> dict | None:
    """读取会话的滚动摘要、压缩边界和压缩指标。"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT summary_json,
               compressed_through_message_id,
               source_token_count,
               summary_token_count,
               version,
               updated_at
        FROM conversation_context_summaries
        WHERE conversation_id = %s
        """,
        (conversation_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None

    summary_json = row[0]
    if isinstance(summary_json, bytes):
        summary_json = summary_json.decode("utf-8")
    elif not isinstance(summary_json, str):
        summary_json = json.dumps(summary_json, ensure_ascii=False)

    return {
        "summary_json": summary_json,
        "compressed_through_message_id": row[1],
        "source_token_count": row[2],
        "summary_token_count": row[3],
        "version": row[4],
        "updated_at": row[5],
    }


def upsert_context_summary_state(
    conversation_id: int,
    summary: ContextSummary,
    compressed_through_message_id: int,
    source_token_count: int,
    summary_token_count: int,
) -> None:
    """原子写入滚动摘要和压缩边界；已有记录时更新并增加版本号。"""
    summary_json = json.dumps(asdict(summary), ensure_ascii=False)
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO conversation_context_summaries (
            conversation_id,
            summary_json,
            compressed_through_message_id,
            source_token_count,
            summary_token_count
        ) VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            summary_json = VALUES(summary_json),
            compressed_through_message_id = VALUES(compressed_through_message_id),
            source_token_count = VALUES(source_token_count),
            summary_token_count = VALUES(summary_token_count),
            version = version + 1
        """,
        (
            conversation_id,
            summary_json,
            compressed_through_message_id,
            source_token_count,
            summary_token_count,
        ),
    )
    conn.commit()
    conn.close()

def check_conversation_id(conversation_id: int) -> bool:
    """输入一个ID，检查一个对话ID是否存在"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM conversations WHERE id = %s",
        (conversation_id,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def add_memory(conversation_id: int, content: str, embedding: list[float] | None = None, memory_type: str = "fact") -> int:
    """
    向 memories 表中插入一条记忆，并返回该记忆的 ID
    输入为对话ID，记忆内容，embedding向量，记忆类型（默认是 fact）
    输出为该记忆的 ID
    """
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    embedding_json = json.dumps(embedding) if embedding is not None else None
    cursor.execute(
        "INSERT INTO memories (conversation_id, content, embedding, memory_type) VALUES (%s, %s, %s, %s)",
        (conversation_id, content, embedding_json, memory_type)
    )
    conn.commit()
    memory_id = cursor.lastrowid
    conn.close()
    return memory_id

def update_memory(
    memory_id: int,
    content: str,
    memory_type: str,
    embedding: list[float] | None = None,
) -> None:
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    embedding_json = json.dumps(embedding) if embedding is not None else None
    cursor.execute(
        """
        UPDATE memories
        SET content = %s,
            memory_type = %s,
            embedding = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (content, memory_type, embedding_json, memory_id),
    )
    conn.commit()
    conn.close()

def get_memories() -> list[dict]:
    """
    从 memories 表中获取所有记忆，并返回一个包含字典的列表，
    每个字典包含 id, content、embedding 和 memory_type
    """
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, content, embedding, memory_type, created_at, updated_at, last_used_at, access_count FROM memories"
    )
    rows = cursor.fetchall()
    conn.close()
    memories = []
    for row in rows:
        embedding = json.loads(row[2]) if row[2] is not None else None
        memories.append({
            "id": row[0],
            "content": row[1],
            "embedding": embedding,
            "memory_type": row[3],
            "created_at": row[4],
            "updated_at": row[5],
            "last_used_at": row[6],
            "access_count": row[7],
        })
    
    return memories


def mark_memories_used(memory_ids: list[int]) -> None:
    """Record that selected memories were injected into a prompt."""
    if not memory_ids:
        return

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    placeholders = ", ".join(["%s"] * len(memory_ids))
    cursor.execute(
        f"""
        UPDATE memories
        SET last_used_at = CURRENT_TIMESTAMP,
            access_count = access_count + 1
        WHERE id IN ({placeholders})
        """,
        tuple(memory_ids),
    )
    conn.commit()
    conn.close()

def memory_exists(content: str, memory_type: str) -> bool:
    """检查同类型、同内容的记忆是否已经存在。"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM memories WHERE content = %s AND memory_type = %s",
        (content, memory_type),
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


if __name__ == "__main__":
    init_db()
    print("数据库初始化完成")
