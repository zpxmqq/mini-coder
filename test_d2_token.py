"""
D2 路由对比：旧路由（全量 30 工具）vs 新路由（四阶段）
对比：候选工具数、schema token 数
"""

import json
from tool import ALL_TOOLS
from registry import ToolRegistry, _classify_intent, _build_categories

# 初始化
registry = ToolRegistry(ALL_TOOLS)
categories = _build_categories(ALL_TOOLS)

# 测试用例（覆盖各种意图）
TESTS = [
    ("帮我读取 agent.py 的内容", "file"),
    ("搜索 Python 的最新教程", "web"),
    ("查看最近的 git 提交记录", "git"),
    ("当前时间是几点", "system"),
    ("格式化这段 JSON 字符串", "text"),
    ("统计 agent.py 有多少行代码", "file+info"),
    ("在项目中查找所有包含 TODO 的文件", "search+file"),
    ("创建一个新的目录 test_dir", "create+file"),
    ("删除临时文件 temp.txt", "delete+file"),
    ("把这段文字用 Base64 编码", "text"),
    ("计算 (3+5)*2 的结果", "text"),
    ("查看 git diff 看看改了哪些代码", "git"),
    ("获取 https://example.com 的网页内容", "web"),
    ("复制 config.py 到 config.py.bak", "file"),
    ("查看当前环境变量 PATH", "system"),
]

print("=" * 80)
print("D2 路由升级: Token 节省对比")
print("旧路由: 30 工具全量 → embedding top-k → LLM 精排")
print("新路由: 意图分类 → 目录粗筛 → embedding top-k → LLM 精排")
print("=" * 80)

total_old_tools = 0
total_new_tools = 0

for query, expected in TESTS:
    # 旧方案：全量 30 工具
    old_count = len(ALL_TOOLS)

    # 新方案：意图分类 + 目录粗筛
    cats = _classify_intent(query)
    filtered = registry._filter_by_categories(cats)
    new_count = len(filtered)

    total_old_tools += old_count
    total_new_tools += new_count

    reduction = (old_count - new_count) / old_count * 100
    print(f"  {query[:35]:35s}  全量:{old_count:2d} → 粗筛:{new_count:2d}  (-{reduction:.0f}%)  意图:{cats}")

print()
avg_old = total_old_tools / len(TESTS)
avg_new = total_new_tools / len(TESTS)
reduction = (avg_old - avg_new) / avg_old * 100
print(f"  平均: 全量 {avg_old:.0f} 工具 → 粗筛 {avg_new:.0f} 工具, "
      f"候选缩减 {reduction:.0f}%")

# Token 对比: 全量 schemas vs 粗筛后 schemas
print()
print("=" * 80)
print("Schema Token 对比（估算）")
print("=" * 80)

# 全量 schemas 的 JSON 大小
all_schemas_json = json.dumps(
    [t.to_schema() for t in ALL_TOOLS], ensure_ascii=False
)
all_tokens_est = len(all_schemas_json) // 3  # 粗略: 3 字符 ≈ 1 token

total_old_tokens = 0
total_new_tokens = 0

for query, expected in TESTS:
    cats = _classify_intent(query)
    filtered = registry._filter_by_categories(cats)

    filtered_json = json.dumps(
        [t.to_schema() for t in filtered], ensure_ascii=False
    )
    filtered_tokens = len(filtered_json) // 3

    old_tokens = all_tokens_est
    new_tokens = filtered_tokens
    total_old_tokens += old_tokens
    total_new_tokens += new_tokens

    saved = old_tokens - new_tokens
    saved_pct = saved / old_tokens * 100
    print(f"  {query[:35]:35s}  {old_tokens:4d} → {new_tokens:4d} token  节省 {saved:4d} ({saved_pct:.0f}%)")

avg_old_tok = total_old_tokens / len(TESTS)
avg_new_tok = total_new_tokens / len(TESTS)
tok_reduction = (avg_old_tok - avg_new_tok) / avg_old_tok * 100
print()
print(f"  平均: {avg_old_tok:.0f} → {avg_new_tok:.0f} token, 节省 {tok_reduction:.0f}%")
print()
print(f"  一次调用: 从 {avg_old_tok:.0f} token 降到 {avg_new_tok:.0f} token")
print(f"  100 次调用: 从 {avg_old_tok*100:.0f} token 降到 {avg_new_tok*100:.0f} token, 节省 {avg_old_tok*100 - avg_new_tok*100:.0f} token")
