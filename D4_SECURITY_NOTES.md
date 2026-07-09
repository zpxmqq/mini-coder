# D4 Security Notes

## 目标

D4 的目标是给 Coding Agent 加上真实的安全边界。

Agent 可以读文件、写文件、改代码、执行命令，所以不能只相信 LLM 的工具调用请求。LLM 只能提出“我想调用什么工具”，真正是否执行，必须由 Agent Harness 决定。

D4 做的是一条安全执行链路：

```text
LLM 请求工具
  -> 路径白名单限制文件边界
  -> risk_level / allowed_risk 判断权限
  -> medium / high 风险工具要求人工确认
  -> 用户确认后再继续执行
  -> audit log 记录安全决策
```

## 已实现机制

### 1. Workspace 路径白名单

相关文件：

```text
infra/security.py
core/tool.py
tests/test_d4_security.py
```

`resolve_workspace_path(path)` 会把用户传入路径解析成绝对路径，并拒绝访问项目工作区外的路径。

相对路径会基于项目根目录解析：

```text
core/agent.py -> D:\mini_code\core\agent.py
```

越界路径会被拒绝：

```text
..\secret.txt
C:\Users\xxx\secret.txt
```

文件类工具在执行前都会调用路径白名单，包括：

```text
read_file
write_file
edit_file
grep
list_files
create_directory
delete_file
move_file
copy_file
get_file_info
glob_find_files
find_in_files
count_lines
```

### 2. 工具风险等级和请求权限

相关文件：

```text
infra/security.py
core/tool.py
core/agent.py
tests/test_d4_confirmation.py
```

工具声明自己的风险等级：

```text
low     只读或低风险
medium 可能修改文件或改变状态
high    执行命令等高风险行为
```

请求侧传入 `allowed_risk`，Agent Harness 判断当前请求是否有权限执行该工具。

例如：

```text
allowed_risk = low
tool_risk = high
```

结果是拒绝执行，并返回 tool message 给模型：

```text
权限不足: 工具 bash 需要 high 权限，当前只有 low 权限
```

### 3. 人工确认

相关文件：

```text
core/agent.py
infra/security.py
tests/test_d4_confirmation.py
```

当 `run(..., require_confirmation=True)` 时，medium / high 风险工具不会被直接执行。

Agent 会返回确认请求：

```python
{
    "status": "needs_confirmation",
    "confirmation_id": "confirm_xxx",
    "tool_call_id": "call_xxx",
    "tool_name": "edit_file",
    "arguments": {...},
    "risk_level": "medium",
}
```

这里的重点是：

```text
tool_call_id      来自 LLM，用于标识这一次工具调用
confirmation_id   系统自己生成，用于从 pending store 找回暂停现场
```

### 4. 确认后继续执行

相关文件：

```text
core/agent.py
```

待确认工具调用会被保存在内存字典：

```python
PENDING_CONFIRMATIONS = {
    "confirm_xxx": {
        "messages": messages,
        "tools": tools,
        "allowed_risk": allowed_risk,
        "require_confirmation": require_confirmation,
        "tool_call": tool_call,
        "tool": tool,
        "arguments": arguments,
    }
}
```

用户确认后调用：

```python
confirm_tool_call(confirmation_id, approved=True)
```

执行流程：

```text
取出 pending confirmation
  -> 执行原工具
  -> 把工具结果追加为 tool message
  -> 继续 run()
```

用户拒绝时调用：

```python
confirm_tool_call(confirmation_id, approved=False)
```

系统不会执行工具，并返回 `status: rejected`。

### 5. 安全审计日志

相关文件：

```text
infra/audit.py
core/agent.py
tests/test_d4_audit.py
```

`write_audit_event(event, payload)` 会把安全事件追加写入 JSONL 文件：

```text
logs/security_audit.jsonl
```

每一行是一条 JSON 记录，包含：

```text
event
created_at
tool_name
risk_level
allowed_risk
arguments
error
confirmation_id
```

目前记录的事件包括：

```text
invalid_allowed_risk
unknown_tool_requested
invalid_tool_risk
tool_permission_denied
tool_confirmation_requested
tool_confirmation_approved
tool_confirmation_rejected
tool_confirmation_missing
tool_arguments_invalid
tool_execution_failed
```

## 当前分层

```text
infra/security.py
  安全规则：
  - 路径白名单
  - 风险等级是否合法
  - 请求权限是否足够
  - 是否需要人工确认
  - prompt injection 检测

infra/audit.py
  安全事件记录：
  - 只负责写审计日志
  - 不参与安全决策

core/tool.py
  工具定义和工具执行：
  - 声明 risk_level
  - 文件类工具调用路径白名单

core/agent.py
  Agent Harness：
  - 调 LLM
  - 解析 tool_call
  - 调 security 做判断
  - 调 audit 记录事件
  - 执行 / 拒绝 / 暂停 / 继续工具调用
```

## 面试讲法

可以这样介绍 D4：

> 我的 Agent 不是模型想调什么工具就直接执行。LLM 只负责生成 tool call，真正的执行权在 Agent Harness。Harness 会先做路径白名单，保证文件访问不能越过 workspace；再根据工具声明的 risk_level 和请求传入的 allowed_risk 做权限判断；对于 medium / high 风险工具，在开启人工确认时会暂停执行并返回 confirmation_id。用户确认后，系统从 pending store 找回当时的 messages、tool_call 和参数，执行工具后继续 ReAct loop。同时，每个拒绝、确认、执行失败都会写入 audit log，方便事后追溯。

## 当前局限

### 1. pending confirmation 还是内存版

现在 `PENDING_CONFIRMATIONS` 是进程内字典。

局限：

```text
服务重启会丢
多进程部署不能共享
不能跨机器恢复
```

后续接 FastAPI / MySQL 后，应迁移到数据库表。

### 2. audit log 还是文件版

现在审计日志写 JSONL 文件。

优点：

```text
简单
方便本地调试
不用引入数据库依赖
```

局限：

```text
不方便按 conversation_id / tool_name / risk_level 查询
日志轮转、权限控制、集中采集还没做
```

后续服务化后，可以迁移到 MySQL 表或结构化日志系统。

### 3. 权限模型仍然比较粗

当前只有：

```text
low / medium / high
```

后续可以扩展：

```text
按用户角色授权
按工具单独授权
按路径授权
按命令白名单授权
按会话临时授权
```

### 4. bash 安全还不够细

现在 `bash` 已经是 high 风险，并受权限和人工确认控制。

但生产级还应该继续做：

```text
命令白名单
超时限制
工作目录限制
环境变量过滤
敏感输出脱敏
资源限制
```

## 后续深化方向

### 1. Pending confirmation 持久化

新增数据库表：

```text
pending_confirmations
```

字段可以包括：

```text
confirmation_id
conversation_id
tool_call_id
tool_name
arguments_json
risk_level
status: pending / approved / rejected / expired
created_at
resolved_at
```

### 2. Audit log 数据库化

新增数据库表：

```text
security_audit_logs
```

支持按以下维度查询：

```text
conversation_id
tool_name
risk_level
event
created_at
```

### 3. 权限策略对象化

把简单函数升级成 policy 对象：

```python
SecurityPolicy.can_execute(tool, request_context)
SecurityPolicy.needs_confirmation(tool, request_context)
```

这样可以加入用户角色、会话上下文、路径范围等因素。

### 4. 更强的命令执行沙箱

后续可以把 `bash` 从“黑名单 + high 风险”升级成：

```text
白名单命令
固定 workspace cwd
禁止网络
限制超时
限制输出长度
限制环境变量
```

## 当前 D4 验收

已通过：

```text
tests/test_d4_security.py
tests/test_d4_confirmation.py
tests/test_d4_audit.py
py_compile core/tool.py infra/security.py infra/audit.py core/agent.py
```

D4 当前可以暂告一段落。后续如果继续深化安全模块，优先做 pending confirmation 持久化和 audit log 数据库化。
