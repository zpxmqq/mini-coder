# mini-coder

从零手写的轻量 AI Coding Agent —— 参考 Claude Code 架构，不复制代码。

终端里给它一个任务，它会自己决定调用哪些工具（读文件 / 写文件 / 改代码 / 搜索 / 执行命令），多步完成后给出结果。

> **项目原则**：不堆功能，每个机制都有真实测出的数字；commit 历史小步公开，每一行都能讲清"为什么这么写"。

---

## 当前进度（2026-06-25）

| Week | 主题 | 状态 |
|---|---|---|
| 1 | ReAct loop + 5 原子工具 | ✅ 完成 |
| 2 | 二阶段工具路由（embedding 召回） | ✅ 完成 |
| 3 | FastAPI 封装 + MySQL 持久化 | ⬜ |
| 4 | Redis 缓存 / 限流 / 重试 | ⬜ |
| 5 | 记忆沉淀闭环 | ⬜ |
| 6 | 权限分级 + Prompt 注入防御 | ⬜ |
| 7 | 离线评测 + ablation | ⬜ |
| 8 | Docker 部署 + 收尾 | ⬜ |

---

## 已完成的核心机制

### 1. ReAct Loop（Week 1）

`while msg.tool_calls` 循环：模型推理 → 调工具 → 把结果回喂 → 再推理，直到模型不再需要工具。

工程边界：
- `MAX_ITER=5` 防止模型陷入死循环烧 token
- 每个工具调用 `try/except` 兜底，单个工具失败不拖垮整个 loop
- 未知工具返回明确提示，避免模型反复幻觉调用

5 个原子工具：`read_file` / `write_file` / `edit_file` / `grep` / `bash`。
其中 `bash` 处理了 Windows GBK 编码坑（`encoding="utf-8", errors="replace"`）+ 危险命令黑名单。

工具调度从 5 个 `if/elif` 重构为字典分发（`TOOL_FUNCTIONS`），加新工具无需改循环逻辑。

### 2. 二阶段工具路由（Week 2）

**问题**：工具变多后，把全部 schema 发给模型会 token 爆炸、且模型易选错。

**方案**：
- **阶段 1 召回**：用 embedding（`bge-small-zh`，本地 CPU）算"用户问题"与"每个工具描述"的余弦相似度，取 top-k 候选
- **阶段 2 精排**：只把候选 schema 交给 LLM 做最终决策

**实测数字**（5 个真工具 + 25 个测试工具 = 30 个，召回 top-5）：

| 指标 | 结果 |
|---|---|
| 召回准确率 | **10/10 = 100%** |
| schema token | 7822 → 1506 字符，**节省 81%** |

> **诚实的局限**：100% 是因为测试工具语义区分度高，语义相近的工具（如 `read_file` vs `open_file`）准确率会下降；k 设太小可能在多工具复合任务中漏掉需要的工具。召回是"粗筛"，精度交给阶段 2 的 LLM。

工具管理封装为 `ToolRegistry` 类（清单 / 索引 / 召回一处管理），工具清单由调用方注入，类不绑定具体工具。

---

## 架构

```
main.py       用户交互（读输入 / 打印）
  ├─ ToolRegistry.select()  → 召回该用哪些工具（registry.py）
  │     └─ retriever.py     → embedding / 余弦相似度 / top-k 召回
  └─ run()                  → ReAct 循环（agent.py）
        ├─ provider.py      → DeepSeek API 调用
        └─ tool.py          → 工具 schema + 执行函数
config.py     配置加载 + 校验（fail-fast）
```

每个文件单一职责，依赖单向。加新工具只需改 `tool.py` 一处。

## 技术栈

Python 3.12 · uv · DeepSeek v4 · OpenAI SDK · sentence-transformers（bge-small-zh）

## 运行

```bash
git clone https://github.com/zpxmqq/mini-coder.git
cd mini-coder
cp .env.example .env          # 填入 DEEPSEEK_API_KEY
uv sync
uv run main.py
```

测试召回：`uv run test_recall.py`

---

> 学习项目，从 Python 接近零基础起步，每一行代码均手写并能逐行解释。
