import subprocess

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
   
write_file_tool = {
    "type": "function",
    "function":{
        "name": "write_file",
        "description": "写入内容到文件",
        "strict": True,
        "parameters":{
            "type": "object",
            "properties":{
                "path":{
                    "type": "string",
                    "description": "要写入的文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "要写入文件的内容"
                }
            },
            "required": ["path", "content"],
            "additionalProperties": False
        }
    }
}

def write_file(path: str, content: str) -> str:
    """
    该函数用于将指定内容写入到指定路径的文件中。

    path参数是要写入的文件的路径，content参数是要写入的内容。函数会尝试打开文件并写入内容，如果成功则返回成功信息。如果文件无法写入，则返回错误信息。
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return "文件写入成功"
    except Exception as e:
        return f"无法写入文件: {e}"
    
edit_file_tool = {
    "type": "function",
    "function":{
        "name": "edit_file",
        "description": "编辑文件内容",
        "strict": True,
        "parameters":{
            "type": "object",
            "properties":{
                "path": {
                    "type": "string",
                    "description": "要编辑的文件路径"
                },
                "old_string":{
                    "type": "string",
                    "description": "要替换的旧字符串"
                },
                "new_string":{
                    "type": "string",
                    "description": "要替换的新字符串"
                }
            },
            "required": ["path", "old_string", "new_string"],
            "additionalProperties": False
        }
    }
}

def edit_file(path: str, old_string: str, new_string: str) -> str:
    """
    该函数用于在指定路径的文件中查找并替换指定的字符串。

    path参数是要编辑的文件的路径，old_string参数是要替换的旧字符串，new_string参数是要替换的新字符串。函数会尝试打开文件并进行替换操作，如果成功则返回成功信息。如果文件无法编辑，则返回错误信息。
    """
    try:
        with open(path, "r", encoding = "utf-8") as f:
            content = f.read()
            if old_string in content:
                content = content.replace(old_string, new_string)
            else:
                return "文件中未找到指定的旧字符串"
            
        with open(path, "w", encoding = "utf-8") as f_write:
                f_write.write(content)
                return "文件编辑成功"
        
    except Exception as e:
        return f"无法编辑文件: {e}"

grep_tool = {
    "type": "function",
    "function": {
        "name": "grep",
        "description": "在文件中查找指定字符串",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
               "path": {
                   "type": "string",
                   "description": "要查找的文件路径"
                },
                "pattern": {
                    "type": "string",
                    "description": "要查找的字符串模式"
                }
            },
            "required": ["path", "pattern"],
            "additionalProperties": False
        }
    }
}

def grep(path: str, pattern: str) -> str:
    """
    该函数用于在指定路径的文件中查找指定的字符串模式。

    path参数是要查找的文件的路径，pattern参数是要查找的字符串模式。函数会尝试打开文件并查找匹配的行，如果成功则返回匹配行的字符串表示。如果文件无法读取或没有找到匹配行，则返回错误信息。
    """
    try:
        with open(path, "r", encoding = "utf-8") as f:
            lines = f.readlines()
            matched_lines = [line for line in lines if pattern in line]
            if matched_lines:
                return "\n".join(matched_lines)
            else:
                return "文件中未找到匹配的字符串模式"
            
    except Exception as e:
        return f"无法读取文件: {e}"
    
bash_tool = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "执行bash命令",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的bash命令"
                }
            }
        },
        "required": ["command"],
        "additionalProperties": False
    }
}

DANGEROUS_COMMANDS = [
      "rm ", "rmdir", "del ", "format", "fdisk",
      "shutdown", "reboot", "chmod 777",
]

def bash(command: str) -> str:
    """
    该函数用于执行指定的bash命令。
    
    command参数是要执行的bash命令。函数会尝试执行命令并返回命令的输出结果。如果命令执行失败，则返回错误信息。
    """
    try:
        # 危险命令黑名单（先在函数外面定义 DANGEROUS_COMMANDS）
        for keyword in DANGEROUS_COMMANDS:
            if keyword in command.lower():
                return f"拒绝执行: 命令含危险关键词 '{keyword}'"
            
        result = subprocess.run(command, shell = True, capture_output = True, text = True, encoding="utf-8", errors="replace")
        if result.returncode == 0:
            return result.stdout or "(命令执行成功，无输出)" 
        else:
            return f"命令执行失败: {result.stderr}"
    except Exception as e:
        return f"无法执行命令: {e}"
    
ALL_TOOLS = [
    read_file_tool, 
    write_file_tool, 
    edit_file_tool, 
    grep_tool, 
    bash_tool
]

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "grep": grep,
    "bash": bash,
}

TOOL_RISK_LEVELS = {
    "read_file": "low",
    "grep": "low",
    "write_file": "medium",
    "edit_file": "medium",
    "bash": "high",
}

ALLOWED_LEVELS = {
    "low": 1,
    "medium": 2,
    "high": 3
}