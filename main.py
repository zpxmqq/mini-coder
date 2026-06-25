from provider import init_client
from config import api_key, base_url
from tool import read_file_tool, write_file_tool, edit_file_tool, grep_tool, bash_tool
from agent import run

def main() -> None:

    init_client(api_key, base_url)
    messages: list[dict] = [
        {"role": "system", "content": "你是我的人工智能助手，协助我使用中文解答问题。"},
    ]

    while True:
        user_input = input("请输入你的问题 (输入 'exit' 退出): ")
        if user_input.lower() == "exit":
            break
        messages.append({"role": "user", "content": user_input})
        answer = run(messages, tools=[read_file_tool, write_file_tool, edit_file_tool, grep_tool, bash_tool])
        print(answer)
        
if __name__ == "__main__":
    main()
