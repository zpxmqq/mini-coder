from core.provider import chat_with_deepseek
from core.tool import ALLOWED_LEVELS, ALL_TOOLS
import json

MAX_ITER = 5

def run(messages: list[dict], tools: list[dict] | None = None, allowed_risk: str = "high") -> str:
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
            for tool in ALL_TOOLS:
                if tool.name == name:
                    func = tool
                    break
            if func is None:
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"未知工具:{name}"})
                continue

            tool_risk = tool.risk_level
            if ALLOWED_LEVELS[tool_risk] > ALLOWED_LEVELS[allowed_risk]:
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"权限不足：工具 {name} 需要 {tool_risk} 级权限，当前只有 {allowed_risk} 级"})
                continue

            try:
                args = json.loads(tc.function.arguments)
                result = tool.execute(**args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            except Exception as e:
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"工具执行失败: {e}"})

        resp = chat_with_deepseek(messages, tools=tools)
        msg = resp.choices[0].message

    messages.append(resp.choices[0].message)

    return resp.choices[0].message.content