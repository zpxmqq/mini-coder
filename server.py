from fastapi import FastAPI, Body
from pydantic import BaseModel
from provider import init_client
from config import api_key, base_url
from agent import run
from registry import ToolRegistry
from tool import ALL_TOOLS

init_client(api_key, base_url)
registry = ToolRegistry(ALL_TOOLS)
class ChatRequest(BaseModel):
    message: str
app = FastAPI()

@app.post("/chat")
def chat(request: ChatRequest):

    messages: list[dict] = [
        {"role": "system", "content": "你是我的人工智能助手，协助我使用中文解答问题。"},
    ]
    messages.append({"role": "user", "content": request.message})
    schemas = registry.select(request.message, k = 3) 
    answer = run(messages, tools = schemas)
    return {"reply": answer}
    

