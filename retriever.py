from sentence_transformers import SentenceTransformer
from sentence_transformers import util

_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

def embed(texts: list[str]):
    return _model.encode(texts)

def top_k(query, candidates, k):
    query_vec = embed(query)
    candidates_ves = embed(candidates)

    scores = util.cos_sim(query_vec, candidates_ves)[0]
    pairs = zip(candidates, scores)
    pairs_sorted = sorted(pairs, key = lambda x:x[1], reverse = True)
    
    return pairs_sorted[:k]

if __name__ == "__main__":
    tools = [
        "read_file: 读取指定路径的文件内容",
        "write_file: 写入内容到指定路径的文件",
        "bash: 执行系统命令",
    ]
    for desc, score in top_k("帮我读取文件", tools, k=2):
        print(f"{score:.3f}  {desc}")