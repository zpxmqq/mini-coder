from provider import chat_with_deepseek
from tool import read_file
import json

MAX_ITER = 5

def run(messages: list[dict], tools: list[dict]| None = None) -> str:
    iteration = 0
    resp = chat_with_deepseek(messages, tools=tools)
    msg = resp.choices[0].message
    while msg.tool_calls:
        iteration += 1
        if iteration > MAX_ITER:
            return "工具调用次数过多，可能出现死循环，已终止。"
        messages.append(msg)
        for tc in msg.tool_calls:
            name = tc.function.name
            if name == "read_file":
                try:
                    args = json.loads(tc.function.arguments)
                    result = read_file(**args)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                except Exception as e:
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"工具执行失败: {e}"})
            else:
                messages.append({"role":"tool", "tool_call_id": tc.id, "content": f"未知工具:{name}"})      
        resp = chat_with_deepseek(messages, tools=tools)
        msg = resp.choices[0].message
    
    messages.append(resp.choices[0].message)
        
    return resp.choices[0].message.content