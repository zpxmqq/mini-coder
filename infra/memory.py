import math
from datetime import datetime, timezone

from infra.db import get_memories
from core.retriever import top_k


HALF_LIFE_DAYS = {
    "fact": 180,
    "preference": 90,
    "reference": 30,
}
USAGE_BOOST_ALPHA = 0.05


def current_time() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def calculate_decay_score(memory_type: str, updated_at, now: datetime | None = None) -> float:
    """Calculate exponential time decay for a memory type."""
    now = now or current_time()
    timestamp = _normalize_datetime(updated_at)
    if timestamp is None:
        return 1.0

    now = _normalize_datetime(now) or current_time()
    age_seconds = max((now - timestamp).total_seconds(), 0)
    age_days = age_seconds / 86400
    half_life_days = HALF_LIFE_DAYS.get(memory_type, HALF_LIFE_DAYS["fact"])
    return 0.5 ** (age_days / half_life_days)


def calculate_memory_score(memory: dict, semantic_score: float, now: datetime | None = None) -> float:
    """Combine semantic relevance, time decay, and usage count into one score."""
    now = now or current_time()
    updated_at = _normalize_datetime(memory.get("updated_at"))
    last_used_at = _normalize_datetime(memory.get("last_used_at"))
    recency_at = max([t for t in (updated_at, last_used_at) if t is not None], default=None)

    decay_score = calculate_decay_score(
        memory.get("memory_type", "fact"),
        updated_at=recency_at,
        now=now,
    )
    access_count = int(memory.get("access_count") or 0)
    usage_boost = 1 + USAGE_BOOST_ALPHA * math.log1p(access_count)
    return float(semantic_score) * decay_score * usage_boost


def retrieve_memories(query: str, k: int = 5) -> list[dict]:
    """
    检索与 query 语义相似的记忆，返回前 k 条。
    返回值保留 memory_type 和 content，方便上层按类型组织 prompt。
    """
    memories = get_memories()
    if not memories:
        return []

    memory_texts = [m["content"] for m in memories]
    candidate_k = min(len(memory_texts), max(k * 4, k))
    top_k_memories = top_k(query, memory_texts, candidate_k)
    text_to_memory = {m["content"]: m for m in memories}
    now = current_time()

    results = []
    for text, score in top_k_memories:
        memory = text_to_memory.get(text)
        if memory is None:
            continue
        semantic_score = float(score)
        final_score = calculate_memory_score(memory, semantic_score, now=now)
        result = {
            "memory_type": memory.get("memory_type", "fact"),
            "content": memory["content"],
            "score": semantic_score,
            "final_score": final_score,
            "created_at": memory.get("created_at"),
            "updated_at": memory.get("updated_at"),
            "last_used_at": memory.get("last_used_at"),
            "access_count": memory.get("access_count", 0),
        }
        if "id" in memory:
            result["id"] = memory["id"]
        results.append(result)

    results.sort(key=lambda memory: memory["final_score"], reverse=True)
    return results[:k]


def find_similar_memories(
    content: str,
    memory_type: str,
    k: int = 3,
    min_score: float = 0.75,
) -> list[dict]:
    """
    在同类型记忆中召回与新记忆语义相似的候选。

    这里只负责找候选，不决定 skip / replace / keep_both。
    """
    memories = [
        memory for memory in get_memories()
        if memory.get("memory_type", "fact") == memory_type
    ]
    if not memories:
        return []

    memory_texts = [m["content"] for m in memories]
    top_k_memories = top_k(content, memory_texts, k)
    text_to_memory = {m["content"]: m for m in memories}

    results = []
    for text, score in top_k_memories:
        score_value = float(score)
        if score_value < min_score:
            continue
        memory = text_to_memory.get(text)
        if memory is None:
            continue
        result = {
            "memory_type": memory.get("memory_type", memory_type),
            "content": memory["content"],
            "score": score_value,
            "created_at": memory.get("created_at"),
            "updated_at": memory.get("updated_at"),
            "last_used_at": memory.get("last_used_at"),
            "access_count": memory.get("access_count", 0),
        }
        if "id" in memory:
            result["id"] = memory["id"]
        results.append(result)

    return results
