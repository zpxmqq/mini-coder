from infra.db import get_memories
from core.retriever import top_k


def retrieve_memories(query: str, k: int = 5) -> list[dict]:
    """
    检索与 query 语义相似的记忆，返回前 k 条。
    返回值保留 memory_type 和 content，方便上层按类型组织 prompt。
    """
    memories = get_memories()
    if not memories:
        return []

    memory_texts = [m["content"] for m in memories]
    top_k_memories = top_k(query, memory_texts, k)
    text_to_memory = {m["content"]: m for m in memories}

    results = []
    for text, score in top_k_memories:
        memory = text_to_memory.get(text)
        if memory is None:
            continue
        results.append({
            "memory_type": memory.get("memory_type", "fact"),
            "content": memory["content"],
        })

    return results