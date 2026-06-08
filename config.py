import os
from dotenv import load_dotenv

load_dotenv()

api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

if not api_key or api_key.startswith("sk-在这里"):
    raise RuntimeError(
        "DEEPSEEK_API_KEY 未配置。\n"
        "请打开项目下的 .env 文件,把这一行的占位符换成真实 key:\n"
        "    DEEPSEEK_API_KEY=sk-...你的真实key..."
    )