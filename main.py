from core.provider import init_client
from config import api_key, base_url
from core.tool import ALL_TOOLS
from core.agent import run
from core.registry import ToolRegistry

def main() -> None:

    init_client(api_key, base_url)
    registry = ToolRegistry(ALL_TOOLS)
    messages: list[dict] = [
        {"role": "system", "content": "你是我的人工智能助手，协助我使用中文解答问题。"},
    ]

    while True:
        user_input = input("请输入你的问题 (输入 'exit' 退出): ")
        if user_input.lower() == "exit":
            break
 
        schemas = registry.select(user_input, k = 3) 
        messages.append({"role": "user", "content": user_input})
        answer = run(messages, tools = schemas)
        print(answer)
        
if __name__ == "__main__":
    main()
