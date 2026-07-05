from openai import OpenAI
from openai.types.chat import ChatCompletion
from tenacity import retry, stop_after_attempt, wait_exponential

client: OpenAI | None = None

def init_client(api_key: str, base_url: str) -> None:
    """
    该函数初始化OpenAI客户端，设置API密钥和基础URL。

    api_key是访问Deep Seek API所需的密钥，base_url是API的基础URL。
    通过调用OpenAI类并传入api_key和base_url参数，可以创建一个客户端实例，用于后续与Deep Seek API进行交互。
    """
    global client
    client = OpenAI(api_key=api_key, base_url=base_url)

@retry(
        stop = stop_after_attempt(3),
        wait = wait_exponential(multiplier=1, min=1, max=10),
)
def chat_with_deepseek(messages:list[dict], tools:list[dict]|None=None)->ChatCompletion:
    """
    该函数向deep seek发送聊天请求并返回ChatCompletion对象。

    messages参数是一个包含聊天消息的列表，每条消息是一个字典，包含角色（system、user或assistant）和内容。
    
    返回ChatCompletion对象，通过resp.choices[0].message.content可以获取模型生成的回复内容。
    """
    assert client is not None, "客户端未初始化"
    resp = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=messages,
        temperature = 0.01,
        stream=False,
        tools=tools,
    )
    return resp


