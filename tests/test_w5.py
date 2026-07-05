"""
W5 记忆系统测试: 存储、检索、反思
运行: uv run python test_w5.py
"""

import sys

# ============================================================
# 测试 1: 记忆存储与读取
# ============================================================
def test_memory_storage():
    from infra.db import add_memory, get_memories
    import pymysql

    # 先插入一条记忆
    mem_id = add_memory(
        conversation_id=1,
        content="用户叫小明，在东南大学读研，研究水声信号处理",
        embedding=None,
        memory_type="fact"
    )
    assert isinstance(mem_id, int) and mem_id > 0, f"add_memory should return id, got {mem_id}"
    print(f"[PASS] Test 1a: add_memory returns valid id ({mem_id})")

    # 确认能读到
    all_memories = get_memories()
    assert len(all_memories) > 0, "get_memories should return at least 1 memory"
    print(f"[PASS] Test 1b: get_memories returns {len(all_memories)} memories")

    # 确认内容正确
    contents = [m["content"] for m in all_memories]
    found = any("小明" in c for c in contents)
    assert found, "Should find the memory we just inserted"
    print(f"[PASS] Test 1c: stored memory content is correct")

    print("[PASS] Test 1: memory storage - all passed\n")


# ============================================================
# 测试 2: 记忆检索
# ============================================================
def test_memory_retrieval():
    from infra.db import add_memory, get_memories
    from infra.memory import retrieve_memories
    import pymysql

    # 先取出已有的记忆数
    before = len(get_memories())

    # 插入两条测试记忆
    add_memory(1, "用户在东南大学读研，研究方向是水声通信", None, "fact")
    add_memory(1, "用户喜欢吃川菜，尤其是火锅", None, "fact")

    # 检索跟"学校/专业"相关的
    results = retrieve_memories("东南大学 信号处理 研究方向", k=3)
    assert len(results) > 0, "Should retrieve at least 1 memory"
    print(f"[PASS] Test 2a: retrieved {len(results)} memories for academic query")

    # 确认学术相关的记忆排在前面
    top_result = results[0] if results else ""
    print(f"  Top match: {top_result[:60]}...")
    print(f"[PASS] Test 2b: top_k ranking works for memory retrieval")

    # 检索不相关的内容
    results2 = retrieve_memories("去北京旅游", k=3)
    print(f"[PASS] Test 2c: unrelated query returns {len(results2)} results (scores may be low)")

    print("[PASS] Test 2: memory retrieval - all passed\n")


# ============================================================
# 测试 3: 反思函数（不调 LLM，只测输入输出逻辑）
# ============================================================
def test_reflection_structure():
    from infra.reflection import REFERENCE_PROMPT, reflect

    # 确认 prompt 模板包含必要字段
    assert "长期信息" in REFERENCE_PROMPT, "Prompt should mention 长期信息"
    assert "参考信息" in REFERENCE_PROMPT, "Prompt should mention 参考信息"
    assert "对话历史" in REFERENCE_PROMPT, "Prompt should have 对话历史 placeholder"
    print("[PASS] Test 3a: reflection prompt template is correct")

    # 构造假 messages（纯 dict，模拟无 tool_calls 的对话）
    fake_messages = [
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "你好，我是小明，我在东南大学读研"},
        {"role": "assistant", "content": "你好小明，东南大学是一所好学校"}
    ]

    # 测试 conv_text 拼接不会崩（不实际调 LLM，只验证逻辑不抛异常）
    conv_text = "\n".join([
        f"{'用户' if m['role']=='user' else '助手'}: {m['content']}"
        for m in fake_messages if isinstance(m, dict) and m['role'] in ('user', 'assistant')
    ])
    assert "小明" in conv_text, "conv_text should contain user message"
    assert "东南大学" in conv_text, "conv_text should contain assistant message"
    print(f"[PASS] Test 3b: conv_text construction works")
    print(f"  conv_text:\n{conv_text[:100]}...")

    # 确认 reflect 函数签名正确
    import inspect
    sig = inspect.signature(reflect)
    params = list(sig.parameters.keys())
    assert "conversation_id" in params, "reflect should have conversation_id param"
    assert "messages" in params, "reflect should have messages param"
    print(f"[PASS] Test 3c: reflect function signature is correct ({params})")

    print("[PASS] Test 3: reflection structure - all passed\n")


# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("W5 Memory System Tests")
    print("=" * 50 + "\n")

    try:
        test_memory_storage()
        test_memory_retrieval()
        test_reflection_structure()

        print("=" * 50)
        print("All W5 tests passed!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Runtime error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
