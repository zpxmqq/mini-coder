from fastapi import FastAPI
from pydantic import BaseModel
from provider import init_client
from config import api_key, base_url
from agent import run
from registry import ToolRegistry
from tool import ALL_TOOLS
from db import init_db, add_message, create_conversation, get_messages

init_db()
init_client(api_key, base_url)
registry = ToolRegistry(ALL_TOOLS)
class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None
app = FastAPI()

@app.post("/chat")
def chat(request: ChatRequest):

    messages: list[dict] = [
        {"role": "system", "content": "你是我的人工智能助手，协助我使用中文解答问题。"},
    ]
    #判断是否有历史对话，若无则新建对话
    if request.conversation_id:
        history = get_messages(request.conversation_id)
        messages.extend(history)
    else:
        request.conversation_id = create_conversation()

    #追加用户消息
    messages.append({"role": "user", "content": request.message})
    add_message(request.conversation_id, "user", request.message)

    #运行agent
    schemas = registry.select(request.message, k = 3) 
    answer = run(messages, tools = schemas)

    #存回答
    add_message(request.conversation_id, "assistant", answer)
    return {"reply": answer, "conversation_id": request.conversation_id}
    

