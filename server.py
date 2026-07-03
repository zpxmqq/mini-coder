from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from provider import init_client
from config import api_key, base_url
from agent import run
from registry import ToolRegistry
from tool import ALL_TOOLS
from db import init_db, add_message, create_conversation, get_messages, check_conversation_id
from cache import get_cache_key, check_cache, set_cache
import time

# 限流配置
MAX_REQUESTS_PER_MINUTE = 10
rate_limit: dict[str, list[float]] = {}

init_db()
init_client(api_key, base_url)
registry = ToolRegistry(ALL_TOOLS)
class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None
app = FastAPI()

@app.post("/chat")
def chat(request: ChatRequest, req: Request):
    # 限流检查
    ip = req.client.host if req.client else "unknown"
    now = time.time()
    # 清掉一分钟前的旧记录
    rate_limit.setdefault(ip, [])
    rate_limit[ip] = [t for t in rate_limit[ip] if now - t < 60]
    if len(rate_limit[ip]) >= MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="请求太频繁，请稍后再试")
    rate_limit[ip].append(now)

    messages: list[dict] = [
        {"role": "system", "content": "你是我的人工智能助手，协助我使用中文解答问题。"},
    ]
    #判断是否有历史对话，若无则新建对话
    if request.conversation_id and check_conversation_id(request.conversation_id):
        history = get_messages(request.conversation_id)
        messages.extend(history)
    else:
        request.conversation_id = create_conversation()

    #追加用户消息
    messages.append({"role": "user", "content": request.message})
    add_message(request.conversation_id, "user", request.message)
    schemas = registry.select(request.message, k = 3)

    #检查缓存消息
    cache_key = get_cache_key(request.message, schemas)
    cached = check_cache(cache_key)
    if cached:
        add_message(request.conversation_id, "assistant", cached)
        return {"reply": cached, "conversation_id": request.conversation_id}

    #运行agent 
    answer = run(messages, tools = schemas)

    #存回答
    add_message(request.conversation_id, "assistant", answer)
    set_cache(cache_key, answer)
    return {"reply": answer, "conversation_id": request.conversation_id}
    

