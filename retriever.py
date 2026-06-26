from sentence_transformers import SentenceTransformer
from sentence_transformers import util
from torch import Tensor

_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

def embed(texts: str | list[str]) -> Tensor:
    """
    将文本编码为向量。

    输入单个字符串或字符串列表，返回对应的向量(Tensor)。
    意思相近的文本，向量也相近——这是后续相似度召回的基础。
    """

    return _model.encode(texts)

def build_tool_index(tool_schemas: list[dict]) -> list[dict]:
    """
    把工具 schema 列表转成召回用的候选库。

    输入为完整的 tool schema 列表，输出为 list[dict]，每项含两个字段:
    - name: 工具名(召回命中后用它反查对应的完整 schema)
    - text: name+描述拼接(用于向量编码、算相似度)
    """
    tool_index = []
    for tool in tool_schemas:
        func = tool["function"]
        name = func["name"]
        desc = func["description"]
        tool_index.append({
            "name": name,
            "text": f"{name}: {desc}"
        })

    return tool_index

def top_k(query: str, candidates: list[str], k: int) -> list[tuple]:
    """
    通用相似度排序: 返回与 query 最匹配的 k 个候选文本。

    输入为 query 和一批候选文本(candidates), 输出为最匹配的 k 个 (text, score) 配对。
    注意: 本函数不绑定"工具"概念, 只认文本+分数, 任何文本列表都能排序——
    所以调用方(route)要先从 tool_index 抽出 text 再传进来, 拿到结果后自己反查 name。
    """
    query_vec = embed(query)
    candidates_ves = embed(candidates)

    scores = util.cos_sim(query_vec, candidates_ves)[0]
    pairs = zip(candidates, scores)
    pairs_sorted = sorted(pairs, key = lambda x:x[1], reverse = True)
    
    return pairs_sorted[:k]

def route(query: str, tool_index: list[dict], k: int = 3) -> list[str]:
    """
    输入用户问题，返回召回命中的工具名列表
    
    输入是用户问题和 tool_index(build_tool_index 产出的 {name,text} 列表),
    输出是召回命中的工具名列表。
    注意它只输出名称, 后续由 ToolRegistry 用字典把名称翻译成完整 tool schema 传给 LLM,
    再由 LLM 精排决定真正调哪个工具——这是二阶段路由里的"阶段1 召回"。
    """
    candidates = [item["text"] for item in tool_index] 
    results = top_k(query, candidates, k)              
    names = []                                        
    for text, score in results:
        for item in tool_index:
            if text == item["text"]:
                names.append(item["name"])                                                   
    return names

if __name__ == "__main__":
    from tool import read_file_tool, write_file_tool, edit_file_tool, grep_tool, bash_tool
    schemas = [read_file_tool, write_file_tool, edit_file_tool, grep_tool, bash_tool]
    index = build_tool_index(schemas)
    for item in index:
        print(item)