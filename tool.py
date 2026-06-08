read_file_tool = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取文件内容",
        "strict": True,
        "parameters":{
            "type": "object",
            "properties":{
                "path":{
                    "type": "string",
                    "description": "要读取的文件路径"
                }
            },
            "required": ["path"],
            "additionalProperties": False
        }
    }
}

def read_file(path: str) -> str:
    """
    该函数用于读取指定路径的文件内容。

    path参数是要读取的文件的路径。函数会尝试打开文件并读取其内容，如果成功则返回文件内容的字符串表示。如果文件不存在或无法读取，则返回错误信息。
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"无法读取文件: {e}"