"""LLM 结构化输出的通用 JSON 语法解析工具。"""

import json


JSON_ROOT_MARKERS = {
    "object": "{",
    "array": "[",
}


def extract_json_payload(raw_text: str, expected_root: str) -> str | None:
    """
    从 LLM 输出中提取第一个完整 JSON 对象或数组字符串。

    输入：可能包含 Markdown 代码块或前后解释文字的 LLM 原始字符串，以及
    expected_root（只能是 object 或 array）。
    输出：符合预期根类型的完整 JSON 字符串；无法解析或根类型不符时返回 None。
    """
    if expected_root not in JSON_ROOT_MARKERS:
        raise ValueError("expected_root 只能是 object 或 array")

    text = raw_text.strip()
    if not text:
        return None

    root_positions = [
        (position, marker)
        for marker in JSON_ROOT_MARKERS.values()
        if (position := text.find(marker)) != -1
    ]
    if not root_positions:
        return None

    start, actual_marker = min(root_positions, key=lambda item: item[0])
    if actual_marker != JSON_ROOT_MARKERS[expected_root]:
        return None

    try:
        _, end = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return None

    return text[start:start + end]


def parse_llm_json_object(raw_text: str) -> dict | None:
    """把 LLM 输出解析为 JSON 对象；不是对象或语法非法时返回 None。"""
    payload = extract_json_payload(raw_text, expected_root="object")
    if payload is None:
        return None

    data = json.loads(payload)
    return data if isinstance(data, dict) else None


def parse_llm_json_array(raw_text: str) -> list | None:
    """把 LLM 输出解析为 JSON 数组；不是数组或语法非法时返回 None。"""
    payload = extract_json_payload(raw_text, expected_root="array")
    if payload is None:
        return None

    data = json.loads(payload)
    return data if isinstance(data, list) else None
