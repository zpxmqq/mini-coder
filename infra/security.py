import re
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_LEVELS = {
    "low": 1,
    "medium": 2,
    "high": 3,
}
CONFIRMATION_RISK_LEVELS = {"medium", "high"}


def is_valid_risk_level(risk_level: str) -> bool:
    """判断风险等级是否属于系统允许的范围。"""
    return risk_level in ALLOWED_LEVELS


def can_execute_tool(tool_risk: str, allowed_risk: str) -> bool:
    """判断当前请求权限是否足够执行指定风险等级的工具。"""
    return ALLOWED_LEVELS[tool_risk] <= ALLOWED_LEVELS[allowed_risk]


def needs_confirmation(risk_level: str) -> bool:
    """判断指定风险等级的工具是否需要用户人工确认。"""
    return risk_level in CONFIRMATION_RISK_LEVELS


def resolve_workspace_path(path: str) -> Path:
    """把用户传入的路径解析到工作区内，拒绝访问工作区外的路径。"""
    root = WORKSPACE_ROOT.resolve()
    target = Path(path)
    if not target.is_absolute():
        target = root / target
    target = target.resolve()

    if target != root and root not in target.parents:
        raise ValueError(f"path outside workspace: {path}")

    return target


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