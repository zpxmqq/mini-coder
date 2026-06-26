"""
W3 测试专用的假工具库。

只有 schema，没有真实执行函数——因为 W3 只验证「召回准不准、省多少 token」，
不需要真的运行这些工具。用它们把工具总数撑到 ~30 个，召回才有意义。

注意：这些不是 mini-coder 的正式工具，只用于 Week 2 召回测试。
"""

# 每个假工具最简结构：name + description + 一个参数
def _tool(name: str, desc: str, param: str, param_desc: str) -> dict:
    """小工厂：少写点重复 JSON。给个名字、描述、一个参数，吐出一个合法 schema。"""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    param: {"type": "string", "description": param_desc},
                },
                "required": [param],
                "additionalProperties": False,
            },
        },
    }


FAKE_TOOLS = [
    _tool("send_email", "发送电子邮件给指定收件人", "to", "收件人邮箱地址"),
    _tool("query_database", "在数据库中查询符合条件的记录", "sql", "要执行的 SQL 查询语句"),
    _tool("translate_text", "把一段文本翻译成目标语言", "text", "要翻译的文本"),
    _tool("get_weather", "查询某个城市的实时天气", "city", "城市名称"),
    _tool("create_calendar_event", "在日历中创建一个日程", "title", "日程标题"),
    _tool("send_sms", "发送短信到指定手机号", "phone", "目标手机号"),
    _tool("download_file", "从指定 URL 下载文件到本地", "url", "文件的下载链接"),
    _tool("upload_file", "把本地文件上传到云存储", "path", "本地文件路径"),
    _tool("resize_image", "调整图片的尺寸大小", "path", "图片文件路径"),
    _tool("compress_image", "压缩图片以减小体积", "path", "图片文件路径"),
    _tool("transcribe_audio", "把音频文件转写成文字", "path", "音频文件路径"),
    _tool("text_to_speech", "把文字合成为语音", "text", "要合成的文字"),
    _tool("search_web", "在互联网上搜索关键词", "query", "搜索关键词"),
    _tool("scrape_webpage", "抓取网页的正文内容", "url", "网页地址"),
    _tool("translate_currency", "按实时汇率换算货币金额", "amount", "要换算的金额"),
    _tool("get_stock_price", "查询某只股票的实时价格", "symbol", "股票代码"),
    _tool("create_pdf", "把文本内容生成为 PDF 文件", "content", "PDF 内容"),
    _tool("merge_pdf", "把多个 PDF 文件合并成一个", "paths", "PDF 文件路径列表"),
    _tool("generate_qrcode", "为一段文本生成二维码图片", "text", "二维码内容"),
    _tool("run_sql_migration", "执行数据库结构迁移脚本", "script", "迁移脚本路径"),
    _tool("send_slack_message", "向 Slack 频道发送消息", "channel", "频道名称"),
    _tool("create_github_issue", "在 GitHub 仓库创建一个 issue", "title", "issue 标题"),
    _tool("book_flight", "预订一张机票", "destination", "目的地城市"),
    _tool("calculate_route", "计算两地之间的导航路线", "origin", "出发地"),
    _tool("summarize_text", "把一段长文本总结成摘要", "text", "要总结的文本"),
]


if __name__ == "__main__":
    print(f"假工具数量: {len(FAKE_TOOLS)}")
    for t in FAKE_TOOLS:
        f = t["function"]
        print(f"  {f['name']}: {f['description']}")
