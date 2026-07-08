from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def install_fake_retriever():
    from types import ModuleType

    fake_retriever = ModuleType("core.retriever")
    fake_retriever.top_k = lambda query, candidates, k: [(text, 1.0) for text in candidates[:k]]
    sys.modules["core.retriever"] = fake_retriever


def test_reference_memories_decay_faster_than_facts():
    install_fake_retriever()
    from infra.memory import calculate_decay_score

    now = datetime(2026, 7, 8, tzinfo=timezone.utc)
    updated_at = now - timedelta(days=30)

    fact_score = calculate_decay_score("fact", updated_at=updated_at, now=now)
    reference_score = calculate_decay_score("reference", updated_at=updated_at, now=now)

    assert fact_score > reference_score
    assert reference_score == 0.5


def test_access_count_boosts_memory_score():
    install_fake_retriever()
    from infra.memory import calculate_memory_score

    now = datetime(2026, 7, 8, tzinfo=timezone.utc)
    updated_at = now - timedelta(days=10)

    unused = {"memory_type": "fact", "updated_at": updated_at, "access_count": 0}
    used_often = {"memory_type": "fact", "updated_at": updated_at, "access_count": 10}

    assert calculate_memory_score(unused, semantic_score=0.8, now=now) < calculate_memory_score(
        used_often,
        semantic_score=0.8,
        now=now,
    )


def test_retrieve_memories_reranks_by_final_score():
    install_fake_retriever()
    sys.modules.pop("infra.memory", None)
    import infra.memory as memory_module

    now = datetime(2026, 7, 8, tzinfo=timezone.utc)
    old = now - timedelta(days=180)
    recent = now - timedelta(days=1)

    old_get_memories = memory_module.get_memories
    old_top_k = memory_module.top_k
    old_now = memory_module.current_time
    try:
        memory_module.get_memories = lambda: [
            {
                "id": 1,
                "memory_type": "reference",
                "content": "old but semantically close note",
                "updated_at": old,
                "last_used_at": None,
                "access_count": 0,
            },
            {
                "id": 2,
                "memory_type": "reference",
                "content": "recent but slightly less close note",
                "updated_at": recent,
                "last_used_at": None,
                "access_count": 0,
            },
        ]
        memory_module.top_k = lambda query, candidates, k: [
            ("old but semantically close note", 0.95),
            ("recent but slightly less close note", 0.80),
        ]
        memory_module.current_time = lambda: now

        results = memory_module.retrieve_memories("note", k=2)

        assert [memory["id"] for memory in results] == [2, 1]
        assert results[0]["final_score"] > results[1]["final_score"]
    finally:
        memory_module.get_memories = old_get_memories
        memory_module.top_k = old_top_k
        memory_module.current_time = old_now


if __name__ == "__main__":
    test_reference_memories_decay_faster_than_facts()
    test_access_count_boosts_memory_score()
    test_retrieve_memories_reranks_by_final_score()
    print("memory scoring tests passed")
