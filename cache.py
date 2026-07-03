import hashlib
import redis

r = redis.Redis(host = "127.0.0.1", port = 6379, decode_responses=True)

def get_cache_key(message: str, schemas: list[dict]) -> str:
    """"把用户消息与使用的工具名拼成缓存key"""
    tool_names = sorted(s["function"]["name"] for s in schemas)
    raw = message + "|" + ",".join(tool_names)
    return "cache:" + hashlib.sha256(raw.encode()).hexdigest()[:16]

def check_cache(key: str) -> str | None:
    """"查询缓存，若有则输出，若无则返回None"""
    return r.get(key)

def set_cache(key: str, value: str, ttl: int = 3600) -> None:
    """"设置缓存，默认过期时间为1小时"""
    r.set(key, value, ex = ttl)
