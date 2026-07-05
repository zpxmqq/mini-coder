import re

# 危险模式列表（常量，放函数外面）
_DANGER_PATTERNS = [
    r'忽略.*指令',
    r'system.*prompt',
    r'输出.*prompt',
    r'假装|扮演',
]

def check_prompt_injection(message: str) -> str | None:
    """返回 None = 安全，返回字符串 = 命中的危险模式（用于报错）"""
    for pattern in _DANGER_PATTERNS:
        if re.search(pattern, message):
            return f"检测到注入风险: {pattern}"
    return None