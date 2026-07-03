from db import get_memories
from retriever import top_k

def retrieve_memories(query:str, k: int = 5) -> list[dict]:
    """
    检索与 query 语义相似的记忆，返回前 k 条
    输入为 query 和 k，输出为  content 
    """
    memories = get_memories()
    if not memories:
        return []
    memories_texts = [m["content"] for m in memories]
    top_k_memories = top_k(query, memories_texts, k)

    return [text for text, score in top_k_memories]
