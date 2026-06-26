from sentence_transformers import SentenceTransformer
from sentence_transformers import util
from torch import Tensor

_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

def embed(texts: str | list[str]) -> Tensor:
    """调用编码函数，将文本编码为向量"""

    return _model.encode(texts)

def build_tool_index(tool_schemas: list[dict]) -> list[dict]:
    """读取tool，将tool转化为工具名称，描述的结构，用来做编码与召回"""
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
    """编码向量，并输出匹配度最高的K个工具"""
    query_vec = embed(query)
    candidates_ves = embed(candidates)

    scores = util.cos_sim(query_vec, candidates_ves)[0]
    pairs = zip(candidates, scores)
    pairs_sorted = sorted(pairs, key = lambda x:x[1], reverse = True)
    
    return pairs_sorted[:k]

def route(query: str, tool_index: list[dict], k: int = 3) -> list[str]:
    """输入用户问题，返回召回命中的工具名列表"""
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