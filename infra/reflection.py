from core.provider import chat_with_deepseek
from infra.db import add_memory

REFERENCE_PROMPT = """
你是一个记忆提取助手。请从以下对话中提取关于用户的**关键信息**，只提取以下两类：

  1. 长期信息：用户不会经常改变的事实，如学历、学校、专业、研究方向、技术栈偏好、项目名称等
  2. 参考信息：用户的知识来源，如读过的论文、学习的课程、参考的文档、做过的项目等

  输出格式：每行一条，用 "类型：内容" 的格式，例如：
  长期：用户在东南大学读研，研究水声信号处理
  参考：用户学习过 Python 菜鸟教程

  如果对话中没有出现这两类信息，回复 "无"。

  对话内容：
  {对话历史}
  """

def reflect(conversation_id: int, messages: list[dict]) -> str:
    """从对话中反思提取关键信息，存入memories表中"""

    conv_text = "\n".join([
        f"{'用户'if m['role']=='user' else '助手'}: {m['content']}"
        for m in messages if isinstance(m, dict) and m['role'] in ('user', 'assistant')
    ])

    reflect_prompt = REFERENCE_PROMPT.format(对话历史=conv_text)
    reflect_messages = [{"role": "user", "content": reflect_prompt}]

    resp = chat_with_deepseek(reflect_messages)
    result = resp.choices[0].message.content.strip()
    add_memory(conversation_id, result, embedding=None, memory_type="fact")
    return result

