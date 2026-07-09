from core.provider import chat_with_deepseek
from core.tool import ALL_TOOLS
from infra.audit import write_audit_event
from infra.security import can_execute_tool, is_valid_risk_level, needs_confirmation
import json
import uuid

MAX_ITER = 5
TOOL_BY_NAME = {tool.name: tool for tool in ALL_TOOLS}

PENDING_CONFIRMATIONS = {}




def build_confirmation_request(tool_call, tool, arguments: dict, confirmation_id: str | None = None) -> dict:
    """构造待确认工具调用的统一数据结构。"""
    request = {
        "status": "needs_confirmation",
        "tool_call_id": tool_call.id,
        "tool_name": tool.name,
        "arguments": arguments,
        "risk_level": tool.risk_level,
    }
    if confirmation_id is not None:
        request["confirmation_id"] = confirmation_id
    return request


def _store_pending_confirmation(messages: list[dict], tools: list[dict] | None, allowed_risk: str, require_confirmation: bool, tool_call, tool, arguments: dict) -> str:
    """保存等待用户确认的工具调用现场。"""
    confirmation_id = f"confirm_{uuid.uuid4().hex}"
    PENDING_CONFIRMATIONS[confirmation_id] = {
        "messages": messages,
        "tools": tools,
        "allowed_risk": allowed_risk,
        "require_confirmation": require_confirmation,
        "tool_call": tool_call,
        "tool": tool,
        "arguments": arguments,
    }
    return confirmation_id


def confirm_tool_call(confirmation_id: str, approved: bool) -> str | dict:
    """根据用户确认结果继续或拒绝一次待执行的工具调用。"""
    pending = PENDING_CONFIRMATIONS.pop(confirmation_id, None)
    if pending is None:
        write_audit_event("tool_confirmation_missing", {
            "confirmation_id": confirmation_id,
        })
        return {
            "status": "confirmation_not_found",
            "confirmation_id": confirmation_id,
            "message": "未找到待确认的工具调用，可能已经处理过或服务已重启",
        }

    tool_call = pending["tool_call"]
    tool = pending["tool"]
    arguments = pending["arguments"]

    if not approved:
        write_audit_event("tool_confirmation_rejected", {
            "confirmation_id": confirmation_id,
            "tool_call_id": tool_call.id,
            "tool_name": tool.name,
            "risk_level": tool.risk_level,
            "arguments": arguments,
        })
        return {
            "status": "rejected",
            "confirmation_id": confirmation_id,
            "tool_call_id": tool_call.id,
            "tool_name": tool.name,
            "message": "用户拒绝执行该工具调用",
        }

    write_audit_event("tool_confirmation_approved", {
        "confirmation_id": confirmation_id,
        "tool_call_id": tool_call.id,
        "tool_name": tool.name,
        "risk_level": tool.risk_level,
        "arguments": arguments,
    })

    try:
        result = tool.execute(**arguments)
    except Exception as e:
        write_audit_event("tool_execution_failed", {
            "confirmation_id": confirmation_id,
            "tool_call_id": tool_call.id,
            "tool_name": tool.name,
            "risk_level": tool.risk_level,
            "arguments": arguments,
            "error": str(e),
        })
        result = f"工具执行失败: {e}"

    pending["messages"].append(_tool_message(tool_call.id, result))
    return run(
        pending["messages"],
        tools=pending["tools"],
        allowed_risk=pending["allowed_risk"],
        require_confirmation=pending["require_confirmation"],
    )



def _tool_message(tool_call_id: str, content: str) -> dict:
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def run(messages: list[dict], 
        tools: list[dict] | None = None, 
        allowed_risk: str = "high", 
        require_confirmation: bool = False) -> str | dict:
    
    if not is_valid_risk_level(allowed_risk):
        write_audit_event("invalid_allowed_risk", {
            "allowed_risk": allowed_risk,
        })
        return f"权限等级无效: {allowed_risk}，允许值: low, medium, high"

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
            tool = TOOL_BY_NAME.get(name)
            if tool is None:
                write_audit_event("unknown_tool_requested", {
                    "tool_call_id": tc.id,
                    "tool_name": name,
                    "arguments": tc.function.arguments,
                })
                messages.append(_tool_message(tc.id, f"未知工具: {name}"))
                continue

            tool_risk = tool.risk_level
            if not is_valid_risk_level(tool_risk):
                write_audit_event("invalid_tool_risk", {
                    "tool_call_id": tc.id,
                    "tool_name": name,
                    "risk_level": tool_risk,
                })
                messages.append(_tool_message(tc.id, f"工具 {name} 的风险等级无效: {tool_risk}"))
                continue

            if not can_execute_tool(tool_risk, allowed_risk):
                write_audit_event("tool_permission_denied", {
                    "tool_call_id": tc.id,
                    "tool_name": name,
                    "risk_level": tool_risk,
                    "allowed_risk": allowed_risk,
                    "arguments": tc.function.arguments,
                })
                messages.append(_tool_message(
                    tc.id,
                    f"权限不足: 工具 {name} 需要 {tool_risk} 权限，当前只有 {allowed_risk} 权限",
                ))
                continue

            args = None
            try:
                args = json.loads(tc.function.arguments)
                if require_confirmation and needs_confirmation(tool_risk):
                    confirmation_id = _store_pending_confirmation(
                        messages,
                        tools,
                        allowed_risk,
                        require_confirmation,
                        tc,
                        tool,
                        args,
                    )
                    write_audit_event("tool_confirmation_requested", {
                        "confirmation_id": confirmation_id,
                        "tool_call_id": tc.id,
                        "tool_name": name,
                        "risk_level": tool_risk,
                        "allowed_risk": allowed_risk,
                        "arguments": args,
                    })
                    return build_confirmation_request(tc, tool, args, confirmation_id)
                result = tool.execute(**args)
                messages.append(_tool_message(tc.id, result))
            except json.JSONDecodeError as e:
                write_audit_event("tool_arguments_invalid", {
                    "tool_call_id": tc.id,
                    "tool_name": name,
                    "risk_level": tool_risk,
                    "allowed_risk": allowed_risk,
                    "arguments": tc.function.arguments,
                    "error": str(e),
                })
                messages.append(_tool_message(tc.id, f"工具参数 JSON 解析失败: {e}"))
            except Exception as e:
                write_audit_event("tool_execution_failed", {
                    "tool_call_id": tc.id,
                    "tool_name": name,
                    "risk_level": tool_risk,
                    "allowed_risk": allowed_risk,
                    "arguments": args if args is not None else tc.function.arguments,
                    "error": str(e),
                })
                messages.append(_tool_message(tc.id, f"工具执行失败: {e}"))

        resp = chat_with_deepseek(messages, tools=tools)
        msg = resp.choices[0].message

    messages.append(resp.choices[0].message)

    return resp.choices[0].message.content
