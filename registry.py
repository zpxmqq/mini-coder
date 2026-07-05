from retriever import build_tool_index, route

# ── D2.2: 按 tags 自动分组 ──
# 一个工具可能属于多个分类（如 web_search 同时在 ["web", "search"]）

def _build_categories(all_tools):
    """遍历 ALL_TOOLS，按 tags 自动生成 TOOL_CATEGORIES"""
    categories = {}
    for tool in all_tools:
        for tag in tool.tags:
            categories.setdefault(tag, [])
            categories[tag].append(tool)
    return categories


# ── D2.3: 意图分类器（关键词 + 规则，不调 LLM）──

_INTENT_KEYWORDS = {
    "file":    ["文件", "读", "写", "编辑", "查看代码", "列出", "创建目录",
                "删除文件", "复制到", "移动", "行数", "代码统计", "通配符",
                "递归查找", "文件信息"],
    "web":     ["搜索", "网络", "查一下", "网上", "浏览器", "打开网址", "新闻",
                "网页", "链接", "URL"],
    "git":     ["commit", "提交", "git", "分支", "差异", "diff", "log", "仓库",
                "状态", "status"],
    "system":  ["执行", "命令", "时间", "日期", "环境变量", "当前目录", "bash"],
    "text":    ["json", "base64", "编码", "解码", "计算", "uuid", "格式化",
                "数学"],
    "info":    ["查看", "统计", "大小", "修改时间", "多少行"],
    "search":  ["查找", "包含", "匹配", "grep"],
    "edit":    ["替换", "修改为", "改成", "改为"],
    "create":  ["创建", "新建", "生成"],
    "delete":  ["删除", "移除"],
}

def _classify_intent(query: str) -> set[str]:
    """阶段 1：关键词匹配 → 返回命中的分类集合"""
    matched = set()
    for category, keywords in _INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in query:
                matched.add(category)
                break  # 命中一个关键词就够了
    return matched


# ── D2.4: 四阶段路由 ──

class ToolRegistry:

    def __init__(self, all_tools):
        self.all_tools = all_tools
        self.schemas = {t.name: t.to_schema() for t in all_tools}
        self.categories = _build_categories(all_tools)
        # 全量 index 保留，作为 fallback
        self.full_index = build_tool_index(all_tools)

    def _filter_by_categories(self, categories: set[str]) -> list:
        """阶段 2：目录粗筛——只返回命中分类的工具"""
        if not categories:
            return self.all_tools  # 没命中关键词，用全量兜底
        result = set()
        for cat in categories:
            if cat in self.categories:
                result.update(self.categories[cat])
        return list(result) if result else self.all_tools

    def select(self, query, k=3):
        # 阶段 1：意图分类
        categories = _classify_intent(query)

        # 阶段 2：目录粗筛
        candidates = self._filter_by_categories(categories)

        # 阶段 3：embedding top-k（只对粗筛后的工具嵌入）
        index = build_tool_index(candidates)
        names = route(query, index, k)

        # 阶段 4：返回 schema（LLM 精排由 agent.py 调用时自动完成）
        return [self.schemas[n] for n in names]


if __name__ == "__main__":
    from tool import ALL_TOOLS
    print(f"总工具数: {len(ALL_TOOLS)}")
    registry = ToolRegistry(ALL_TOOLS)

    tests = [
        ("帮我读取 agent.py 的内容", "file"),
        ("搜索 Python 教程", "web"),
        ("查看 git 提交记录", "git"),
        ("执行 echo hello 命令", "system"),
        ("格式化这段 JSON", "text"),
        ("这个文件多少行", "file+info"),
        ("在项目中查找 TODO", "search"),
    ]
    for query, expected in tests:
        schemas = registry.select(query, k=3)
        names = [s["function"]["name"] for s in schemas]
        print(f"\nQuery: '{query}' (期望命中: {expected})")
        print(f"  返回: {names}")