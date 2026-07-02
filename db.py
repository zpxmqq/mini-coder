"""
mini-coder 的数据库模块 —— 用于在 SQLite 中持久化存储对话历史。

后续由 server.py 调用，把每一次 HTTP 对话的 message 存进数据库，
再次请求时就能从数据库中读取历史对话。

用 SQLite（内置，无需额外安装），数据库就是一个文件（mini_coder.db）。
"""

import sqlite3

DB_PATH = "mini_coder.db"

def init_db() -> None:
    """初始化数据库：创建表（如果不存在）。

    两张表的职责：
    - conversations：存储对话会话
    - messages：存储会话中的具体消息，通过 conversation_id 关联到 conversations
    """
    conn = sqlite3.connect(DB_PATH)          # 连接到 SQLite 文件（不存在会自动创建）
    cursor = conn.cursor()                   # cursor 就是“在数据库里执行 SQL 的游标”

    # 建「对话表」：存每一次对话会话的基本信息
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,       -- 编号（主键，自动递增，唯一标识一行）
            title TEXT DEFAULT '',                       -- 标题（默认空字符串）
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- 创建时间（自动填当前时间）
        )
    """)

    # 建「消息表」：存每条消息，通过 conversation_id 关联到上面的对话表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,       -- 编号（主键，自动递增）
            conversation_id INTEGER NOT NULL,            -- 所属对话编号（必填）
            role TEXT NOT NULL,                          -- 角色（必填，user/assistant/system/tool）
            content TEXT NOT NULL,                       -- 内容（必填，消息正文）
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 创建时间（自动填当前时间）
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)  -- 外键约束：conversation_id 必须真实存在
        )
    """)

    conn.commit()   # 提交所有操作
    conn.close()    # 关闭连接

def add_message(conversation_id: int, role: str, content: str) -> None:
    """"向messages表中插入一条消息，返回这个信息的ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)", 
        (conversation_id, role, content)
        )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id

def create_conversation(title: str = "") ->int:
    """创建一个新的对话，并返回该对话的ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (title) VALUES (?)", 
        (title,)
        )
    conn.commit()
    conv_id = cursor.lastrowid
    conn.close()
    return conv_id

def get_messages(conversation_id: int) -> list[dict]:
    """查出一个对话的所有消息，按时间顺序返回"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
        (conversation_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    messages = []
    for row in rows:
        messages.append({"role": row[0], "content": row[1]})
    return messages


if __name__ == "__main__":
    init_db()
    print("数据库初始化完成")
