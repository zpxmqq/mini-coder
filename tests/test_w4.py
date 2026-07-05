"""
W4 工程化模块测试: 重试、缓存、限流
运行: uv run python test_w4.py
"""

import time
import sys

# ============================================================
# 测试 1: tenacity 重试
# ============================================================
def test_retry():
    from tenacity import retry, stop_after_attempt, wait_fixed

    call_count = 0

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.1))
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("network error")
        return "ok"

    result = flaky_function()
    assert result == "ok", f"Expected 'ok', got {result}"
    assert call_count == 3, f"Expected 3 retries, got {call_count}"
    print("[PASS] Test 1: tenacity retry (failed 2x then succeeded)")


# ============================================================
# 测试 2: Redis cache
# ============================================================
def test_cache():
    from infra.cache import get_cache_key, check_cache, set_cache, r

    fake_schemas = [
        {"function": {"name": "read_file"}},
        {"function": {"name": "grep"}},
    ]

    # 2a: cache miss
    key = get_cache_key("test: read agent.py", fake_schemas)
    r.delete(key)
    result = check_cache(key)
    assert result is None, f"Expected None, got {result}"
    print("[PASS] Test 2a: cache miss returns None")

    # 2b: cache write + hit
    set_cache(key, "test answer", ttl=3600)
    result = check_cache(key)
    assert result == "test answer", f"Expected 'test answer', got {result}"
    print("[PASS] Test 2b: cache write then hit")

    # 2c: same input -> same key
    key2 = get_cache_key("test: read agent.py", fake_schemas)
    assert key == key2, f"Same input should give same key"
    print("[PASS] Test 2c: same input produces same key")

    # 2d: different input -> different key
    key3 = get_cache_key("different question", fake_schemas)
    assert key != key3, "Different input should give different key"
    print("[PASS] Test 2d: different input produces different key")

    r.delete(key)
    print("[PASS] Test 2: Redis cache - all passed\n")


# ============================================================
# 测试 3: rate limit logic
# ============================================================
def test_rate_limit():
    MAX_REQUESTS = 5
    WINDOW = 60

    rate_limit: dict[str, list[float]] = {}

    def is_allowed(ip: str, fake_now: float) -> bool:
        rate_limit.setdefault(ip, [])
        rate_limit[ip] = [t for t in rate_limit[ip] if fake_now - t < WINDOW]
        if len(rate_limit[ip]) >= MAX_REQUESTS:
            return False
        rate_limit[ip].append(fake_now)
        return True

    # 3a: first MAX_REQUESTS should pass
    for i in range(MAX_REQUESTS):
        assert is_allowed("127.0.0.1", float(i)), f"Request {i+1} should pass"
    print(f"[PASS] Test 3a: first {MAX_REQUESTS} requests all pass")

    # 3b: (MAX_REQUESTS+1)th should be blocked
    blocked = not is_allowed("127.0.0.1", float(MAX_REQUESTS))
    assert blocked, f"Request {MAX_REQUESTS+1} should be blocked"
    print(f"[PASS] Test 3b: request {MAX_REQUESTS+1} blocked")

    # 3c: different IP not affected
    assert is_allowed("192.168.1.1", 0.0), "Different IP should pass"
    print("[PASS] Test 3c: different IP not affected")

    # 3d: window expires -> allowed again
    rate_limit["127.0.0.1"] = [0.0, 1.0, 2.0, 3.0, 4.0]
    assert is_allowed("127.0.0.1", 61.0), "After window expiry should pass"
    print("[PASS] Test 3d: window expiry restores access")

    print("[PASS] Test 3: rate limit logic - all passed\n")


# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("W4 Engineering Module Tests")
    print("=" * 50 + "\n")

    try:
        test_retry()
        print()
        test_cache()
        test_rate_limit()

        print("=" * 50)
        print("All W4 tests passed!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Runtime error: {e}")
        sys.exit(1)
