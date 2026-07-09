import subprocess
import os
import requests
import re
import json
import shutil
import base64
import uuid
import glob as glob_mod
from datetime import datetime
from duckduckgo_search import DDGS
from infra.security import ALLOWED_LEVELS, resolve_workspace_path

class Tool:
    def __init__(self, name: str, description: str, parameters: dict, risk_level: str, tags: list = None, examples: list = None, strict: bool = True, execute = None):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.strict = strict
        self.risk_level = risk_level
        self.tags = tags if tags is not None else []
        self.examples = examples if examples is not None else []
        self.execute = execute

    def to_schema(self) ->dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": self.strict,
                "parameters": self.parameters
            }
        }

def _read_file(path: str) -> str:
    """读取指定路径的文件内容，读取前会校验路径是否在工作区内。"""
    try:
        safe_path = resolve_workspace_path(path)
        with open(safe_path, "r", encoding="utf-8") as f:
            return f.read()
    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"文件读取失败: {e}"
    

read_file = Tool(
    name="read_file",
    description="读取文件内容",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要读取的文件路径"
            }
        },
        "required": ["path"],
        "additionalProperties": False
    },
    risk_level="low",
    tags=["file", "read"],
    examples=["读取 agent.py 的内容"],
    execute=_read_file,
)

def _write_file(path: str, content: str) -> str:
    """把内容写入指定文件，写入前会校验路径是否在工作区内。"""
    try:
        safe_path = resolve_workspace_path(path)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return "文件写入成功"
    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"无法写入文件: {e}"

write_file = Tool(
    name="write_file",
    description="写入内容到文件",
    parameters={
        "type": "object",
        "properties": {
            "path": {
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
    },
    risk_level="medium",
    tags=["file", "write"],
    examples=["写入内容到 agent.py"],
    execute=_write_file,
)

def _edit_file(path: str, old_string: str, new_string: str) -> str:
    """在指定文件中替换文本，编辑前会校验路径是否在工作区内。"""
    try:
        safe_path = resolve_workspace_path(path)
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()
            if old_string in content:
                content = content.replace(old_string, new_string)
            else:
                return "文件中未找到指定的旧字符串"

        with open(safe_path, "w", encoding="utf-8") as f_write:
            f_write.write(content)
            return "文件编辑成功"

    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"无法编辑文件: {e}"

edit_file = Tool(
    name="edit_file",
    description="编辑文件内容",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要编辑的文件路径"
            },
            "old_string": {
                "type": "string",
                "description": "要替换的旧字符串"
            },
            "new_string": {
                "type": "string",
                "description": "要替换的新字符串"
            }
        },
        "required": ["path", "old_string", "new_string"],
        "additionalProperties": False
    },
    risk_level="medium",
    tags=["file", "edit"],
    examples=["将 agent.py 中的 'def run' 替换为 'def execute'"],
    execute=_edit_file,
)  

def _grep(path: str, pattern: str) -> str:
    """在指定文件中查找字符串，读取前会校验路径是否在工作区内。"""
    try:
        safe_path = resolve_workspace_path(path)
        with open(safe_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            matched_lines = [line for line in lines if pattern in line]
            if matched_lines:
                return "\n".join(matched_lines)
            return "文件中未找到匹配的字符串模式"

    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"无法读取文件: {e}"

grep = Tool(
    name="grep",
    description="在文件中查找指定字符串",
    parameters={
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
    },
    risk_level="low",
    tags=["file", "search"],
    examples=["在 agent.py 中查找 'def run'"],
    execute=_grep,
)

DANGEROUS_COMMANDS = [
      "rm ", "rmdir", "del ", "format", "fdisk",
      "shutdown", "reboot", "chmod 777",
]

def _bash(command: str) -> str:
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
    
bash = Tool(
    name="bash",
    description="执行bash命令",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的bash命令"
            }
        },
        "required": ["command"],
        "additionalProperties": False
    },
    risk_level="high",
    tags=["system", "command"],
    examples=["执行 'ls -l' 命令"],
    execute=_bash,
)
    
def _list_files(path: str) -> str:
    """列出指定目录下的文件和子目录，访问前会校验路径是否在工作区内。"""
    try:
        safe_path = resolve_workspace_path(path)
        items = os.listdir(safe_path)
        dirs = [f"[目录] {item}" for item in items if os.path.isdir(safe_path / item)]
        files = [item for item in items if not os.path.isdir(safe_path / item)]
        sorted_items = dirs + files
        if sorted_items:
            return "\n".join(sorted_items)
        return f"目录 {safe_path} 为空"
    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"无法列出文件: {e}"

list_files = Tool(
    name="list_files",
    description="列出指定目录下的文件和子目录",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要列出的文件路径"
            }
        },
        "required": ["path"],
        "additionalProperties": False
    },
    risk_level="low",      # 只读，跟 read_file 同级
    tags=["file", "list"],
    examples=["列出 D:\\mini_code 目录下的文件"],
    execute=_list_files,
)

def _create_directory(path: str) -> str:
    """创建指定目录，创建前会校验路径是否在工作区内。"""
    try:
        safe_path = resolve_workspace_path(path)
        os.makedirs(safe_path, exist_ok=True)
        return f"目录 {safe_path} 创建完成"
    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"目录 {path} 创建失败: {e}"
    

create_directory = Tool(
    name="create_directory",
    description="创建指定目录下的文件夹",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要创建的目录路径"
            }
        },
        "required": ["path"],
        "additionalProperties": False
    },
    risk_level="medium",     
    tags=["file", "createt"],
    examples=["创建D:\\mini_code 目录"],
    execute=_create_directory,
)

def _web_fetch(url: str) ->str:
    """访问一个网址，返回网址的纯文本内容"""
    try:
        response = requests.get(url, timeout=10)
        # 去掉 HTML 标签，只留文字（简单版——用正则删掉所有 <...> 标签）
        text = re.sub(r'<[^>]*>', '', response.text)
        # 去掉多余空行
        text = re.sub(r'\n\s*\n', '\n', text)
        if len(text) > 5000:
            text = text[:5000] + "\n...(内容已截断)"
        return text
    except Exception as e:
        return f"无法访问网页: {e}"

web_fetch = Tool(
    name="web_fetch",
    description="获取网页的文本内容",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "要访问的网址"
            }
        },
        "required": ["url"],
        "additionalProperties": False
    },
    risk_level="low",     
    tags=["web", "read"],
    examples=["获取 www.example.com 的网页内容"],
    execute=_web_fetch,
)

def _web_search(query: str, max_results: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return f"未找到与 '{query}' 相关的结果"
        output = []
        for r in results:
            output.append(f"标题: {r['title']}\n链接: {r['href']}\n摘要: {r['body']}\n")
        return "\n".join(output)
    except Exception as e:
        return f"搜索失败: {e}"
    
web_search = Tool(
    name="web_search",
    description="搜索网页，返回相关结果的标题、链接和摘要",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            },
            "max_results": {
                "type": "integer",
                "description": "最多返回的结果数，默认 5 条"
            }
        },
        "required": ["query"],
        "additionalProperties": False
    },
    risk_level="low",
    tags=["web", "search"],
    examples=["搜索 'Python 教程'"],
    execute=_web_search,
)

# ── 更多文件操作 ──

def _delete_file(path: str) -> str:
    """删除指定文件，删除前会校验路径是否在工作区内。"""
    try:
        safe_path = resolve_workspace_path(path)
        os.remove(safe_path)
        return f"文件 {safe_path} 已删除"
    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"无法删除文件: {e}"

delete_file = Tool(
    name="delete_file",
    description="删除指定路径的文件",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "要删除的文件路径"}},
        "required": ["path"], "additionalProperties": False
    },
    risk_level="medium", tags=["file", "delete"],
    examples=["删除 temp.txt"],
    execute=_delete_file,
)

def _move_file(source: str, destination: str) -> str:
    """移动或重命名文件，源路径和目标路径都必须在工作区内。"""
    try:
        safe_source = resolve_workspace_path(source)
        safe_destination = resolve_workspace_path(destination)
        shutil.move(safe_source, safe_destination)
        return f"已将 {safe_source} 移动到 {safe_destination}"
    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"无法移动文件: {e}"

move_file = Tool(
    name="move_file",
    description="移动或重命名文件",
    parameters={
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "源文件路径"},
            "destination": {"type": "string", "description": "目标路径"}
        },
        "required": ["source", "destination"], "additionalProperties": False
    },
    risk_level="medium", tags=["file", "move"],
    examples=["将 old_name.py 重命名为 new_name.py"],
    execute=_move_file,
)

def _copy_file(source: str, destination: str) -> str:
    """复制文件，源路径和目标路径都必须在工作区内。"""
    try:
        safe_source = resolve_workspace_path(source)
        safe_destination = resolve_workspace_path(destination)
        shutil.copy2(safe_source, safe_destination)
        return f"已将 {safe_source} 复制到 {safe_destination}"
    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"无法复制文件: {e}"

copy_file = Tool(
    name="copy_file",
    description="复制文件到目标路径",
    parameters={
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "源文件路径"},
            "destination": {"type": "string", "description": "目标文件路径"}
        },
        "required": ["source", "destination"], "additionalProperties": False
    },
    risk_level="medium", tags=["file", "copy"],
    examples=["备份 config.py 到 config.py.bak"],
    execute=_copy_file,
)

def _get_file_info(path: str) -> str:
    """获取文件基本信息，访问前会校验路径是否在工作区内。"""
    try:
        safe_path = resolve_workspace_path(path)
        stat = os.stat(safe_path)
        size_kb = stat.st_size / 1024
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        atime = datetime.fromtimestamp(stat.st_atime).strftime("%Y-%m-%d %H:%M:%S")
        lines = []
        if str(safe_path).endswith((".py", ".txt", ".md", ".json", ".yaml", ".yml", ".html", ".css", ".js", ".ts")):
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        return (
            f"文件: {safe_path}\n"
            f"大小: {size_kb:.1f} KB\n"
            f"行数: {len(lines)}\n"
            f"修改时间: {mtime}\n"
            f"访问时间: {atime}"
        )
    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"无法获取文件信息: {e}"

get_file_info = Tool(
    name="get_file_info",
    description="获取文件的大小、行数、修改时间等信息",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "文件路径"}},
        "required": ["path"], "additionalProperties": False
    },
    risk_level="low", tags=["file", "info"],
    examples=["查看 agent.py 的详细信息"],
    execute=_get_file_info,
)

def _glob_find_files(pattern: str) -> str:
    """用通配符查找工作区内文件，通配符不能逃出工作区。"""
    try:
        safe_pattern = resolve_workspace_path(pattern)
        matches = glob_mod.glob(str(safe_pattern), recursive=True)
        if not matches:
            return f"未找到匹配 {pattern!r} 的文件"
        return "\n".join(matches[:50])
    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"查找文件失败: {e}"

glob_find_files = Tool(
    name="glob_find_files",
    description="用通配符模式查找文件，如 '*.py' 或 '**/*.json'",
    parameters={
        "type": "object",
        "properties": {"pattern": {"type": "string", "description": "文件匹配模式，支持 * 和 **"}},
        "required": ["pattern"], "additionalProperties": False
    },
    risk_level="low", tags=["file", "search"],
    examples=["查找所有 .py 文件: *.py", "递归查找: **/*.md"],
    execute=_glob_find_files,
)

def _find_in_files(directory: str, pattern: str, file_pattern: str = "*") -> str:
    """在工作区内的指定目录中递归搜索文件内容。"""
    try:
        safe_directory = resolve_workspace_path(directory)
        results = []
        for root, _, files in os.walk(safe_directory):
            for file_name in files:
                if glob_mod.fnmatch.fnmatch(file_name, file_pattern):
                    filepath = os.path.join(root, file_name)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
                            for line_number, line in enumerate(fh.readlines(), 1):
                                if pattern in line:
                                    results.append(f"{filepath}:{line_number}: {line.rstrip()}")
                    except Exception:
                        pass
        if not results:
            return f"在 {safe_directory} 中未找到包含 {pattern!r} 的文件"
        return "\n".join(results[:50])
    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"跨文件搜索失败: {e}"

find_in_files = Tool(
    name="find_in_files",
    description="递归搜索目录下所有文件的内容（类似 grep -r）",
    parameters={
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "要搜索的目录路径"},
            "pattern": {"type": "string", "description": "要搜索的字符串"},
            "file_pattern": {"type": "string", "description": "限定文件类型，如 *.py，默认 *（所有文件）"}
        },
        "required": ["directory", "pattern"], "additionalProperties": False
    },
    risk_level="low", tags=["file", "search"],
    examples=["在项目中搜索所有包含 'TOOL_RISK_LEVELS' 的 .py 文件"],
    execute=_find_in_files,
)

def _count_lines(path: str) -> str:
    """统计文件行数，读取前会校验路径是否在工作区内。"""
    try:
        safe_path = resolve_workspace_path(path)
        with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        empty = sum(1 for line in lines if line.strip() == "")
        return (
            f"文件: {safe_path}\n"
            f"总行数: {len(lines)}\n"
            f"空行: {empty}\n"
            f"有效行: {len(lines) - empty}"
        )
    except ValueError as e:
        return f"超出安全范围: {e}"
    except Exception as e:
        return f"无法统计行数: {e}"

count_lines = Tool(
    name="count_lines",
    description="统计文件的代码行数、空行数",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "文件路径"}},
        "required": ["path"], "additionalProperties": False
    },
    risk_level="low", tags=["file", "info"],
    examples=["统计 agent.py 的代码行数"],
    execute=_count_lines,
)


# ── 更多 Web 工具 ──

def _web_search_news(query: str, max_results: int = 5) -> str:
    """搜索新闻"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
        if not results:
            return f"未找到与 '{query}' 相关的新闻"
        output = []
        for r in results:
            output.append(f"标题: {r['title']}\n来源: {r.get('source', '未知')}\n链接: {r['url']}\n日期: {r.get('date', '未知')}\n")
        return "\n".join(output)
    except Exception as e:
        return f"新闻搜索失败: {e}"

web_search_news = Tool(
    name="web_search_news",
    description="搜索新闻，返回相关新闻的标题、来源、链接和日期",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "新闻搜索关键词"},
            "max_results": {"type": "integer", "description": "最多返回的结果数，默认 5 条"}
        },
        "required": ["query"], "additionalProperties": False
    },
    risk_level="low", tags=["web", "search", "news"],
    examples=["搜索关于 '大语言模型' 的最新新闻"],
    execute=_web_search_news,
)


# ── 系统工具 ──

def _get_current_time(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """获取当前时间"""
    try:
        return f"当前时间: {datetime.now().strftime(format)}"
    except Exception as e:
        return f"获取时间失败: {e}"

get_current_time = Tool(
    name="get_current_time",
    description="获取当前日期和时间",
    parameters={
        "type": "object",
        "properties": {"format": {"type": "string", "description": "时间格式，默认 %Y-%m-%d %H:%M:%S"}},
        "required": [], "additionalProperties": False
    },
    risk_level="low", tags=["system", "time"],
    examples=["获取当前时间", "获取当前日期: format=%Y-%m-%d"],
    execute=_get_current_time,
)

def _get_env_var(name: str) -> str:
    """读取环境变量"""
    try:
        value = os.environ.get(name)
        if value is None:
            return f"环境变量 {name} 未设置"
        return f"{name}={value if 'KEY' not in name.upper() and 'TOKEN' not in name.upper() and 'SECRET' not in name.upper() else '***已隐藏***'}"
    except Exception as e:
        return f"读取环境变量失败: {e}"

get_env_var = Tool(
    name="get_env_var",
    description="读取系统环境变量（敏感值自动隐藏）",
    parameters={
        "type": "object",
        "properties": {"name": {"type": "string", "description": "环境变量名"}},
        "required": ["name"], "additionalProperties": False
    },
    risk_level="low", tags=["system", "env"],
    examples=["读取 PATH 环境变量"],
    execute=_get_env_var,
)

def _get_working_directory() -> str:
    """获取当前工作目录"""
    try:
        return f"当前工作目录: {os.getcwd()}"
    except Exception as e:
        return f"获取工作目录失败: {e}"

get_working_directory = Tool(
    name="get_working_directory",
    description="获取当前工作目录的路径",
    parameters={
        "type": "object",
        "properties": {},
        "required": [], "additionalProperties": False
    },
    risk_level="low", tags=["system", "info"],
    examples=["查看当前在哪个目录下"],
    execute=_get_working_directory,
)


# ── 文本/编码工具 ──

def _json_validate(text: str) -> str:
    """验证 JSON 格式"""
    try:
        data = json.loads(text)
        return f"JSON 格式合法\n类型: {type(data).__name__}\n键数: {len(data) if isinstance(data, dict) else 'N/A'}"
    except json.JSONDecodeError as e:
        return f"JSON 格式错误: {e}"

json_validate = Tool(
    name="json_validate",
    description="验证 JSON 字符串格式是否合法",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "要验证的 JSON 字符串"}},
        "required": ["text"], "additionalProperties": False
    },
    risk_level="low", tags=["text", "json"],
    examples=["验证 '{\"name\": \"Alice\"}' 是否为合法 JSON"],
    execute=_json_validate,
)

def _json_format(text: str) -> str:
    """格式化 JSON"""
    try:
        data = json.loads(text)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f"JSON 格式错误，无法格式化: {e}"

json_format = Tool(
    name="json_format",
    description="格式化 JSON 字符串，使其缩进清晰可读",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "要格式化的 JSON 字符串"}},
        "required": ["text"], "additionalProperties": False
    },
    risk_level="low", tags=["text", "json"],
    examples=["格式化一段压缩的 JSON"],
    execute=_json_format,
)

def _base64_encode(text: str) -> str:
    """Base64 编码"""
    try:
        return base64.b64encode(text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        return f"编码失败: {e}"

base64_encode = Tool(
    name="base64_encode",
    description="将文本编码为 Base64 字符串",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "要编码的文本"}},
        "required": ["text"], "additionalProperties": False
    },
    risk_level="low", tags=["text", "encoding"],
    examples=["将 'Hello World' 编码为 Base64"],
    execute=_base64_encode,
)

def _base64_decode(text: str) -> str:
    """Base64 解码"""
    try:
        return base64.b64decode(text).decode("utf-8")
    except Exception as e:
        return f"解码失败: {e}"

base64_decode = Tool(
    name="base64_decode",
    description="将 Base64 字符串解码为原始文本",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "要解码的 Base64 字符串"}},
        "required": ["text"], "additionalProperties": False
    },
    risk_level="low", tags=["text", "encoding"],
    examples=["解码一段 Base64 字符串"],
    execute=_base64_decode,
)

def _calculate(expression: str) -> str:
    """安全计算数学表达式"""
    try:
        allowed = set("0123456789+-*/()., %^eEijp")
        cleaned = "".join(c for c in expression if c in allowed)
        if not cleaned:
            return "表达式无可计算的数学运算"
        result = eval(cleaned, {"__builtins__": {}}, {"__builtins__": {}})
        return f"结果: {result}"
    except Exception as e:
        return f"计算失败: {e}"

calculate = Tool(
    name="calculate",
    description="安全计算数学表达式（支持基本运算、幂次、括号）",
    parameters={
        "type": "object",
        "properties": {"expression": {"type": "string", "description": "数学表达式，如 '(3 + 5) * 2 / 4' 或 '2**10'"}},
        "required": ["expression"], "additionalProperties": False
    },
    risk_level="low", tags=["text", "math"],
    examples=["计算: '(3 + 5) * 2 / 4'", "计算: '2**10'"],
    execute=_calculate,
)

def _generate_uuid() -> str:
    """生成 UUID"""
    try:
        return f"UUID: {uuid.uuid4()}"
    except Exception as e:
        return f"生成 UUID 失败: {e}"

generate_uuid = Tool(
    name="generate_uuid",
    description="生成一个随机的 UUID（通用唯一标识符）",
    parameters={
        "type": "object",
        "properties": {},
        "required": [], "additionalProperties": False
    },
    risk_level="low", tags=["text", "utility"],
    examples=["生成一个唯一 ID"],
    execute=_generate_uuid,
)


# ── Git 工具 ──

def _git_status(path: str = ".") -> str:
    """查看 git 仓库状态"""
    try:
        result = subprocess.run("git status", shell=True, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", cwd=path)
        return result.stdout or result.stderr or "(无输出)"
    except Exception as e:
        return f"git status 执行失败: {e}"

git_status = Tool(
    name="git_status",
    description="查看 git 仓库的工作区状态（修改、暂存、未跟踪文件）",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "仓库路径，默认当前目录"}},
        "required": [], "additionalProperties": False
    },
    risk_level="low", tags=["git", "info"],
    examples=["查看当前仓库状态"],
    execute=_git_status,
)

def _git_log(count: int = 5) -> str:
    """查看 git 提交日志"""
    try:
        result = subprocess.run(f"git log --oneline -{count}", shell=True, capture_output=True,
                                text=True, encoding="utf-8", errors="replace")
        return result.stdout or "(无提交记录)"
    except Exception as e:
        return f"git log 执行失败: {e}"

git_log = Tool(
    name="git_log",
    description="查看 git 最近的提交记录",
    parameters={
        "type": "object",
        "properties": {"count": {"type": "integer", "description": "显示的提交数量，默认 5 条"}},
        "required": [], "additionalProperties": False
    },
    risk_level="low", tags=["git", "info"],
    examples=["查看最近 5 条提交", "查看最近 10 条提交: count=10"],
    execute=_git_log,
)

def _git_diff(path: str = ".") -> str:
    """查看 git 差异"""
    try:
        result = subprocess.run("git diff", shell=True, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", cwd=path)
        output = result.stdout or "(无差异)"
        if len(output) > 3000:
            output = output[:3000] + "\n...(diff 已截断)"
        return output
    except Exception as e:
        return f"git diff 执行失败: {e}"

git_diff = Tool(
    name="git_diff",
    description="查看 git 工作区相对于上次提交的代码差异",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "仓库路径，默认当前目录"}},
        "required": [], "additionalProperties": False
    },
    risk_level="low", tags=["git", "info"],
    examples=["查看当前修改了哪些代码"],
    execute=_git_diff,
)

def _git_branch() -> str:
    """查看 git 分支"""
    try:
        result = subprocess.run("git branch", shell=True, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        return result.stdout or "(无分支)"
    except Exception as e:
        return f"git branch 执行失败: {e}"

git_branch = Tool(
    name="git_branch",
    description="查看 git 仓库的所有本地分支",
    parameters={
        "type": "object",
        "properties": {},
        "required": [], "additionalProperties": False
    },
    risk_level="low", tags=["git", "info"],
    examples=["查看所有分支"],
    execute=_git_branch,
)


# ── ALL_TOOLS 统一注册 ──

ALL_TOOLS = [
    # 文件操作（13 个）
    read_file,
    write_file,
    edit_file,
    grep,
    list_files,
    create_directory,
    delete_file,
    move_file,
    copy_file,
    get_file_info,
    glob_find_files,
    find_in_files,
    count_lines,
    # Web（3 个）
    web_fetch,
    web_search,
    web_search_news,
    # 系统（4 个）
    bash,
    get_current_time,
    get_env_var,
    get_working_directory,
    # 文本/编码（6 个）
    json_validate,
    json_format,
    base64_encode,
    base64_decode,
    calculate,
    generate_uuid,
    # Git（4 个）
    git_status,
    git_log,
    git_diff,
    git_branch,
]

