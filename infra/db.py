"""
mini-coder 的数据库模块 —— 用于在 SQLite 中持久化存储对话历史。

后续由 server.py 调用，把每一次 HTTP 对话的 message 存进数据库，
再次请求时就能从数据库中读取历史对话。

用 SQLite（内置，无需额外安装），数据库就是一个文件（mini_coder.db）。
"""

import pymysql
import json

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

    两张表的职责：
    - conversations：存储对话会话
    - messages：存储会话中的具体消息，通过 conversation_id 关联到 conversations
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

def add_message(conversation_id: int, role: str, content: str) -> None:
    """"
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

def get_messages(conversation_id: int) -> list[dict]:
    """输入一个对话ID查出一个对话的所有消息，按时间顺序返回"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages WHERE conversation_id = %s ORDER BY id",
        (conversation_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    messages = []
    for row in rows:
        messages.append({"role": row[0], "content": row[1]})
    return messages

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
