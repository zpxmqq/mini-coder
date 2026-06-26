"""
W3 召回测试：在 30 个工具（5 真 + 25 假）里，验证召回 top-k 能不能选对工具。

测两个指标：
1. 召回准确率：期望工具进 top-k 的比例
2. token 节省：全量传 30 个 schema vs 召回后传 k 个，省多少
"""

import json

from tool import read_file_tool, write_file_tool, edit_file_tool, grep_tool, bash_tool
from fake_tools import FAKE_TOOLS
from retriever import build_tool_index, route

real_tools = [read_file_tool, write_file_tool, edit_file_tool, grep_tool, bash_tool]
all_tools = real_tools + FAKE_TOOLS          # 30 个
tool_index = build_tool_index(all_tools)

# (用户问题, 期望命中的工具名)
test_cases = [
    ("帮我读取 config.py 的内容", "read_file"),
    ("把结果写到 output.txt 里", "write_file"),
    ("在代码里搜索 subprocess 出现在哪", "grep"),
    ("执行 dir 命令看看当前目录", "bash"),
    ("给张三发一封邮件通知他开会", "send_email"),
    ("查一下北京今天的天气怎么样", "get_weather"),
    ("把这段中文翻译成英文", "translate_text"),
    ("从数据库里查出所有订单记录", "query_database"),
    ("帮我把这张图片压缩一下", "compress_image"),
    ("在网上搜一下这个报错怎么解决", "search_web"),
]

K = 5


def test_accuracy() -> None:
    """指标1：召回准确率"""
    hit = 0
    for query, expected in test_cases:
        names = route(query, tool_index, k=K)
        ok = expected in names
        if ok:
            hit += 1
        mark = "OK " if ok else "MISS"
        print(f"[{mark}] {query}")
        print(f"       期望: {expected}  |  召回: {names}")
    print(f"\n召回准确率: {hit}/{len(test_cases)} = {hit / len(test_cases) * 100:.0f}%")


def test_token_saving() -> None:
    """指标2：token 节省（用 schema 的 JSON 字符长度近似 token）"""
    full_chars = len(json.dumps(all_tools, ensure_ascii=False))
    names = route(test_cases[0][0], tool_index, k=K)
    name_to_schema = {t["function"]["name"]: t for t in all_tools}
    recalled = [name_to_schema[n] for n in names]
    recalled_chars = len(json.dumps(recalled, ensure_ascii=False))

    print(f"\n全量 {len(all_tools)} 个工具 schema: {full_chars} 字符")
    print(f"召回 {K} 个工具 schema:     {recalled_chars} 字符")
    print(f"节省: {(1 - recalled_chars / full_chars) * 100:.0f}%")


if __name__ == "__main__":
    test_accuracy()
    test_token_saving()
