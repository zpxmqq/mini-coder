# mini-coder · 项目指令(给助手 + 给自己)

> 这份文档每周一填本周目标,周末助手做评估。Claude 进入项目自动读取,等于持久化记忆。
>
> **状态来源优先级（2026-07-12）**：当前进度和执行顺序以 `AGENTS.md` 为准；各模块细节以 `D3_MEMORY_NOTES.md`、`D4_SECURITY_NOTES.md`、`D5_CONTEXT_NOTES.md` 为准；本文件保留更完整的历史计划，发生冲突时不覆盖前两者。

---

## 一、项目目标

**一个带完整后端工程化的 AI Agent 服务。** 简历主推项目。

- **内核**:复刻并精简 Claude Code 架构的 ReAct agent(工具调用 + 记忆 + RAG)
- **外层**:生产级后端(FastAPI 接口 + MySQL 持久化 + Redis 缓存/限流 + 重试/并发),可部署、可调用、有评测数字
- **一句话**:从零实现的 AI Agent 后端服务——内核是 ReAct 工具调用 agent,外层 FastAPI 封装成 API,配 MySQL 持久化、Redis 缓存限流,Docker 部署,并搭离线评测验证效果

> **为什么从"纯 agent"扩成"agent + 后端"**:目标岗位(AI 应用开发 / AI 后端)的 JD 普遍要求"把 Demo 封装成可调用的 API""用过 MySQL/Redis""接口设计 + 缓存策略 + 重试"。纯 agent 项目只覆盖一半,会被后端面问穿。内核不变,外面包一层后端,一个项目同时打两个面。

- **不是**:堆功能、demo 跑通即止、抄完算数
- **是**:每个机制有真实测出的数字、能扛面试官追问、GitHub commit 历史就是"真做过"的证据

时间窗口:2026-06-06 起 ~ 2026-08 月底,共约 8 周。

---

## 二、用户当前水平(实事求是)

- Python:**接近零基础**。看不懂 traceback、代码 mental model 未建立、抄码为主
- 工程惯例:**第一次接触**(.env / .gitignore / 虚拟环境 / SDK 模式)
- 已有相关背景:水声通信信号处理(MATLAB)、LLM 应用层面认知(daily-planner 经验)
- 学习态度:好——会反思、会问 why、能 calibrate 自我评估

**含义**:节奏慢一点,基础扎一点,不许跳步。

---

## 三、助手(Claude)行为准则

### 严禁
- "9 月面试官想招的人"、"科学家直觉"、"90% 的人没有"等过度归因式鼓励
- 把抄代码包装成"主动学习的优点"
- 假装能力——看到不会的不承认知识可能过时
- 给"甜美图景",只讲成功路径不讲概率
- 装腔的 emoji / 营销话术

### 应做
- 抄代码 = 没消化。直接说"这步你还没消化",不修饰
- 做错 = 说错在哪。不绕弯,不"鼓励里包错误"
- 不确定的知识 = 明说"我也可能错,你查文档"
- 时间/难度评估 = 带**概率分布**,不只给"肯定能"
- 每周末做 calibrated 进度评估,写进第五节评估表

---

## 四、本周目标(每周一更新)

### Week 1 · 2026-06-06 ~ 2026-06-30(扩展窗口,含期末)

> 因 6/23 期末考,Week 1 从标准 7 天扩到 25 天。三段式:
> - **Phase A** 6/6 – 6/16(11 天,1–2h/日):项目骨架 + Python 基础 + 摸通 tool_use API
> - **Phase B** 6/17 – 6/23(7 天,期末优先):闲时看文档,不写代码
> - **Phase C** 6/24 – 6/30(7 天,4–6h/日):实现 5 工具 + ReAct loop + demo
>
> 净有效工作日 ~15–18 天 vs 原计划 7 天,完成概率 **70–80%**(原 CLAUDE.md 写 85% 在新时间线下基本合理)。

#### 想做完的任务(按能力块,不按天;day-unit = 一个有效工作日)

- [x] **B1 项目骨架**(2 day-unit / Phase A):`uv init` 切项目模式;`test_api.py` 拆成 `provider.py` + `main.py`;全函数加 type hint ✅ 6/7
- [x] **B2 数据结构 + JSON**(2 / A):dict/list/tuple 区别;`json.dumps/loads`;用 Python dict 写出符合 OpenAI 规范的 tool schema ✅ 6/8(实际 0.5 天,LeetCode 基础已覆盖)
- [x] **B3 单工具单次调用**(3 / A 末 + C 初):读 DeepSeek function calling 文档 → 实现 `read_file(path) -> str` + schema → 模型选调 → 你 dispatch → 回喂 → 模型出最终答 ✅ 6/8
- [x] **B4 ReAct 循环**(3 / C):把 B3 包成 `while msg.tool_calls` 循环;`MAX_ITER=5` 保命;`try/except` 兜底 ✅ 6/8(agent.py 拆分完成,if→while 改好)
- [x] **B5 其余 4 工具**(4 / C,各 1):`write_file`(对称 read)/ `edit_file`(read+replace+write,old 找不到要报错)/ `bash`(`subprocess.run`,Win 编码坑)/ `grep`(`re` 模块或调系统 ripgrep) ✅ 6/24
    - [x] `write_file` ✅ 6/24
    - [x] `edit_file` ✅ 6/24(读→判断 old 在不在→replace→写回,读写两个独立 with 块避免 Windows 文件占用)
    - [x] `grep` ✅ 6/24(readlines + list comprehension 逐行匹配)
    - [x] `bash` ✅ 6/24(subprocess.run + `encoding="utf-8", errors="replace"` 解决 GBK 坑;`stdout or "(无输出)"` 防 None;DANGEROUS_COMMANDS 黑名单)
- [x] **B6 集成 demo + 复盘**(2 / C 末):复合任务"读 agent.py 的 import + grep tool.py 是否用 subprocess"→模型连续调 read_file→grep 两步且串联推理 ✅ 6/24

总计 16 day-unit ≈ 净可用时间,**几乎无缓冲**。

> **进度更新 6/8**：B1–B4 完成，实际耗时 ~2.5 天 vs 计划 10 day-unit。超前进度约 4 天。
> - B2 快是因为 LeetCode 基础覆盖了 dict/list，CLAUDE.md 原先"接近零基础"低估了
> - B3 密集迭代 4–5 轮改对，没卡壳
> - Phase A 剩余 8 天：做 `write_file` + `edit_file` 即可，bash/grep 留 Phase C（避免期末夹断）
> - 第一次 commit 已推 GitHub: https://github.com/zpxmqq/mini-coder

#### 想消化的知识(每条要能用自己的话讲清楚,不许背)

1. ✅ `def` / `return` / 参数;`return` 跟 `print` 完全不是一回事(B1) — 能口头讲清
2. ✅ `import` vs `from X import Y`;为什么要拆文件(B1) — 五文件架构画得出箭头
3. ✅ dict / list / tuple 区别 + 使用场景(B2) — LeetCode 已覆盖
4. ✅ JSON 在 Python 里就是 dict + list 的嵌套;`json.dumps` 把它变字符串(B2)
5. ✅ **LLM 调工具的本质:模型不执行任何代码,它只是返回"我想调 X(参数 Y)"的 JSON,执行靠你的 Python 代码**(B3) — 能用自己的话讲
6. ✅ `with open(...) as f:` 为什么比裸 `open()` 安全(B3) — 能讲清"自动关文件"
7. ✅ `while msg.tool_calls` 退出条件;为什么 agent 必须有 MAX_ITER(B4) — 写到 agent.py 里了
8. ✅ `try / except`:什么时候该 except 什么时候让它崩(B4) — 包了 json.loads + 执行函数
9. `subprocess.run` 返回的 `CompletedProcess` 长啥样;Windows 上 `encoding='gbk'` 的坑(B5)
10. ✅ ReAct 名字里 "Re"(Reasoning)和 "Act" 分别对应 loop 里哪几行(B4) — 能画出分支图

#### 验收标准

- ✅ 5 个工具单独跑测试都过
- ✅ ReAct loop 能完成**需要至少 3 次工具调用**的复合任务
- ✅ 能向不懂技术的人 5 分钟讲清"我做了什么 / 怎么工作 / 为什么要循环"
- ✅ 从 `agent.py` 随便挑 5 行,能逐行讲清在干嘛、为什么这么写、不这么写会怎样
- ✅ commit 历史是小步迭代,不是一次 1000 行 dump

#### 已知风险 / 不确定

| 风险 | 概率 | 对策 |
|---|---|---|
| 期末后动力滑坡(6/24 不想动) | 高 | 6/23 当天**只做一件极简事**:重跑 Hello DeepSeek,维持"还在轨道"信号 |
| 抄 smolagents | 高 | **6 月禁止打开 `mini_code_refs/`**(物理隔离 > 意志力)。7 月做 Skill 路由时再读 |
| DeepSeek function calling 跟 OpenAI 有微妙差异 | 中 | 留 1 day-unit 缓冲;卡 >90min 来问 |
| Windows bash 工具中文乱码 | 中 | 提前知道是 `gbk` 编码坑,撞上不会以为是代码错 |
| JSON schema 写错,模型不调工具也不报错 | 中 | 学会 `print(resp.model_dump_json(indent=2))` 看完整响应 |
| 想加流式/Web UI 冲动 | 低-中 | Week 1 一律不做,Week 4+ 再说 |

---

### Week 2 · 2026-06-25 ~ 2026-06-26(实际 1 天完成)

> 原计划 7 天,实际 1 天。本地 embedding 跑得比预想顺,bge-small-zh CPU 够用,无需复杂配置。

#### 想做完的任务

- [x] **R1 retriever.py**(1 day-unit):`embed()` 把文本转向量;`build_tool_index()` 从 schema 列表建候选库;`top_k()` 通用余弦相似度排序(不绑工具概念);`route()` 输入问题返回命中工具名列表 ✅ 6/25
- [x] **R2 ToolRegistry 类**(0.5):OOP 封装 — `__init__` 接收 ALL_TOOLS → 建 schemas dict + index;`select()` 调 route → 翻译成 schema list ✅ 6/25
- [x] **R3 假工具构造 + 召回测试**(0.5):25 个假工具 schema(天气/翻译/搜索等)+ 10 个测试用例,验证召回准确率 **100%**,token **7822→1506 节省 81%** ✅ 6/25

#### 想消化的知识

1. ✅ embedding 是什么:把文本映射到高维向量空间,语义相近的向量余弦相似度高 — 能讲清
2. ✅ 二阶段路由:粗筛(embedding top-k)→ 精排(LLM 选工具),为什么比全量 schema 塞 prompt 省 token
3. ✅ OOP 基础:`class` / `__init__` / `self` 是什么,为什么 ToolRegistry 比散装函数好

#### 验收标准

- ✅ 召回准确率有真数字(不是"跑通了")
- ✅ 工具增删只改 `tool.py` 一处,registry 自动感知
- ✅ 能解释"为什么不是 100% 就安全"——k=3 可能漏工具,语义相近工具会降分

---

### Week 3 · 2026-06-27 ~ 2026-07-02(~3 个有效工作日)

> 第一次接触网络(HTTP/FastAPI)和数据库(SQL/SQLite→MySQL),新概念密度高。

#### 想做完的任务

- [x] **W1 FastAPI 接口**(1 day-unit):`server.py` + `/chat` POST + Pydantic `ChatRequest` 校验 + `uvicorn` 启动 ✅ 6/27
- [x] **W2 Pydantic 纠错**(0.3):`Body()` 参数 422 报错 → 改用 BaseModel,理解 Pydantic 校验机制 ✅ 6/27
- [x] **W3 agent 接入 HTTP**(0.2):server.py 调 `registry.select()` + `run()` 返回 `{"reply": answer}` ✅ 6/27
- [x] **W4 SQLite 持久化**(1):`db.py`: `init_db()` 建表 + `create_conversation()` + `add_message()` + `get_messages()` ✅ 6/28
- [x] **W5 server.py 集成 DB**(0.5):`ChatRequest` 加 `conversation_id` 可选字段;chat() 逻辑:有 id 查历史 / 无则新建;对话自动入库 ✅ 7/1
- [x] **W6 MySQL 迁移**(1.5):Windows 装 MySQL 8.4(中文路径踩坑,最终放 `D:\mini_code_temp\`);`sqlite3`→`pymysql`;`?`→`%s`;`AUTOINCREMENT`→`AUTO_INCREMENT`;建库 `mini_coder` + 专用用户 ✅ 7/2

#### 想消化的知识

1. ✅ HTTP 请求/响应:POST 方法、JSON body、状态码 200/404/422/500 — 能用 Swagger `/docs` 自己测试
2. ✅ FastAPI 装饰器:`@app.post("/chat")` 把函数注册为 HTTP 接口;路径参数 vs 查询参数 vs 请求体
3. ✅ Pydantic BaseModel:类型校验 + 可选字段(`int | None = None`) + 自动生成 JSON Schema
4. ✅ SQL 基础:CREATE TABLE / INSERT INTO / SELECT / FOREIGN KEY — 能口头讲清四句话分别干什么
5. ✅ cursor + commit 模式:为什么 `execute()` 后要 `commit()`;`lastrowid` 拿到刚插入的行 ID
6. ✅ SQLite vs MySQL 连接差异:文件 vs 独立服务;占位符 `?` vs `%s`;建表语法微小差异

#### 验收标准

- ✅ HTTP → DB 端到端通:第一轮不带 conv_id 自动创建,第二轮带 conv_id 能回答上一轮信息
- ✅ MySQL 本地服务正常运行,`mini_coder` 库可连接
- ✅ db.py 接口不变,上层 server.py 无感知切换数据库(这就是抽象层的价值)

#### 踩坑记录

| 坑 | 现象 | 根因 | 解决 |
|---|---|---|---|
| Body() 422 | FastAPI 收 JSON body 报 422 | `Body()` 不能直接映射到 `str` | 换 Pydantic BaseModel |
| MySQL 中文路径 | my.ini/日志文件写入失败 | Windows 用户名是中文,"C:\Users\张朋祥\" 含非 ASCII | 数据目录放 `D:\mini_code_temp\` |
| redis-py 8.x 不兼容 | `HELLO` 命令报错 | redis-py 8.x 需要 Redis 6+,Win 只有 3.0 | 降级到 redis-py 4.6 |
| TEXT DEFAULT '' | MySQL 报 1101 错误 | MySQL 严格模式不允许 TEXT 有默认值 | 改 VARCHAR(255) |

---

### Week 4 · 2026-07-03 ~ 2026-07-09(计划)

#### 前置学习(7/3,不写代码)

- [x] 读 gptme 项目结构:对比 agent loop 怎么写、工具怎么注册、跟 mini-coder 的差异
- [x] 读 smolagents tool 注册方式:装饰器模式 vs 我们的手动字典
- [x] Redis 概念:SET/GET/EXPIRE,理解"能过期的全局 dict"
- [x] tenacity 文档 Quick Start

#### 想做完的任务

- [x] **E1 provider 超时重试**(0.5 day-unit):`tenacity` 库,`@retry(stop_after_attempt(3), wait_exponential)` 装饰 `chat_with_deepseek` ✅ 7/4
- [x] **E2 Redis 缓存**(1):`cache.py`: `get_cache_key(message + schemas → sha256)` / `check_cache` / `set_cache`;TTL 1 小时 ✅ 7/4
- [x] **E3 限流**(1):固定窗口计数器,同一 IP 每分钟最多 10 次请求;`HTTPException(429)` ✅ 7/4
- [x] **E4 验证 + 数字**(0.5):`test_w4.py` 12 个测试全部通过(重试 1/缓存 4/限流 4/综合 3) ✅ 7/4

---

### Week 5 · 2026-07-05 ~ 2026-07-11(计划)

> 目标: 复现 Claude Code 的记忆机制——对话中自动提取知识 → 存 MySQL → 新对话 embedding 检索 → 注入上下文。
> 这是八周里设计难度最高的一周(原评估完成概率 55%)，不是调包，是设计问题。

#### 想做完的任务

- [x] **E1 db.py 加 memories 表**(0.5 day-unit):`init_db()` 加 `memories` 表(含 embedding JSON 列) + `add_memory()` + `get_all_memories()` 两个函数 ✅ 7/5
- [x] **E2 新建 memory.py — 记忆检索**(1 day-unit):`retrieve_memories(query, k=5) -> list[str]` — 从 DB 拿所有记忆 → 用 `retriever.top_k()` 做语义检索 → 返回相关内容列表 ✅ 7/5
- [x] **E3 新建 reflection.py — 自动反思**(1.5 day-unit):`reflect_on_conversation(conversation_id, messages)` — 调 LLM(复用 provider.py)，用"反思 prompt"提取对话中关键事实 → 存 memories 表 ✅ 7/5
- [x] **E4 server.py 集成 + 测试**(1 day-unit):请求时注入记忆到 system prompt / 回答后触发反思 / `test_w5.py` 9 测试全过 ✅ 7/5

#### 想消化的知识

1. 为什么检索用 embedding 而不是 SQL LIKE？语义匹配 vs 关键词匹配的区别
2. 反思 prompt 怎么写（不是写代码，是写自然语言指令）
3. 什么时候触发反思？每 N 轮？对话结束时？按重要性判断？设计权衡
4. LLM 输出不稳定怎么办（解析失败、输出空值）
5. embedding 向量如何在 MySQL 里存（JSON 类型）
6. 同一个 `embed() + top_k()` 之前检索工具、现在检索记忆——用途不同但代码一样

#### 验收标准

- [ ] 同一对话多轮后，系统自动提取用户偏好/事实存进 memories 表
- [ ] 新对话能基于之前对话提取的记忆回答个性化问题（如"我之前说我叫什么名字？"）
- [ ] `test_w5.py` 覆盖记忆存储 + 检索 + 反思至少 3 个场景
- [ ] 能解释"为什么选 k=5""反思触发条件为什么这么设计"

#### 文件改动

| 文件 | E1 | E2 | E3 | E4 | 改动量 |
|---|---|---|---|---|---|
| db.py | x | | | | +25行 |
| memory.py | | x | | | 新建 ~40行 |
| reflection.py | | | x | | 新建 ~50行 |
| server.py | | | | x | +10行 |
| test_w5.py | | | | x | 新建 ~50行 |

---

### Week 6 · 2026-07-06 ~ 2026-07-12(计划)

> 目标: 权限分级 + Prompt 注入防御。当前任何用户都能调 bash 删文件、send 伪系统指令骗 system prompt。
> 面试后端安全追问必答题——最小权限原则、注入防御怎么设计。

#### 想做完的任务

- [x] **E1 工具 risk_level 分级**(0.5 day-unit):`tool.py` 加 `TOOL_RISK_LEVELS` 字典(low/medium/high) + `agent.py` 的 `run()` 加 `allowed_risk` 参数,执行前检查 ✅ 7/4
- [x] **E2 server.py 加 permission_level**(0.5 day-unit):`ChatRequest` 加 `permission_level` 字段(默认 user),user 级限 low,admin 级全放行 ✅ 7/4
- [x] **E3 Prompt 注入防御**(1 day-unit):① system prompt 加固(抗注入指令) ② `security.py` 正则检测,拦截"忽略指令/输出 system prompt"类攻击 ✅ 7/4
- [x] **E4 测试**(0.5 day-unit):`test_w6.py` 6 测试全过(权限 4 + 注入检测 2) ✅ 7/4

#### 想消化的知识

1. 最小权限原则（Principle of Least Privilege）——为什么默认是 user 而不是 admin
2. 为什么 bash 比 write_file 危险？write_file 能覆盖文件，bash 能删文件 + 改系统 + 网络外发
3. Prompt 注入的本质是什么？LLM 无法区分"系统指令"和"用户数据"
4. 为什么正则预检不调 LLM？省钱 + 零延时 + 不受 LLM 幻觉影响
5. 安全是深度防御——prompt 层 + 代码层 + 权限层,不能只靠一层

#### 验收标准

- [x] user 级别调 bash 被拒绝,admin 级别能执行 ✅
- [x] prompt 注入关键词被拦截(400) ✅
- [x] 正常对话不受影响 ✅
- [x] `test_w6.py` 6 测试全过 ✅

#### 文件改动

| 文件 | E1 | E2 | E3 | E4 | 改动量 |
|---|---|---|---|---|---|
| tool.py | x | | | | +10行(TOOL_RISK_LEVELS + ALLOWED_LEVELS) |
| agent.py | x | | | | +10行(allowed_risk 参数 + 权限检查) |
| server.py | | x | x | | +14行(permission_level 字段 + 注入检查 + system prompt 加固) |
| security.py | | | x | | 新建 17行(正则检测) |
| test_w6.py | | | | x | 新建 185行(6 测试) |

---

## 五、历史周评估(校准工具)

| Week | 起止 | 计划完成度 | 实际产出 | 偏差与原因 | 下周调整 |
|---|---|---|---|---|---|
| Day 0 | 06-05 | n/a | uv 装通 / Hello DeepSeek 跑通 / .env 改造 / 三个 ref repo clone | 用约 5 小时,主要在抄+理解,基础比预想更弱(看不懂 traceback、Python 阅读量极少) | Week 1 不赶进度,优先打基础;每写一段代码必须能答 what/why/alternative |
| Week 1 | 06-06~06-24 | 100%(代码全完成,字典分发重构也做了;录视频可选,未做) | 5 工具(read/write/edit/grep/bash)+ ReAct loop + MAX_ITER + try/except + 危险命令黑名单;复合任务多步调用验证通过;agent.py 已从 5 个 if/elif 重构为 TOOL_FUNCTIONS 字典分发(87→43 行) | 实际有效工作 ~4 天 vs 计划 16 day-unit,大幅超前(Python 基础被低估 + 没抄代码全手写) | Week 2 开始 Skill 二阶段路由(embedding 召回 + LLM 精排);装饰器自动注册工具待工具≥8个再做;bash 安全 Week 6 升级白名单/沙箱;残留 hello_ai.py/test_document.txt 待清理 |
| Week 2 | 06-25~06-25 | ~90%(召回主干+重构+真数字全完成;README 待补) | embedding 二阶段路由:retriever.py(embed/top_k/route)+ ToolRegistry 类封装工具管理;5真+25假=30工具召回测试 **准确率 10/10=100%,token 7822→1506 节省 81%**;架构重构:召回逻辑从 main 抽到 ToolRegistry,ALL_TOOLS/TOOL_FUNCTIONS 集中到 tool.py,加工具只改一处 | 1 天完成(本地 embedding 比预想顺,bge-small-zh CPU 够用);中途文件丢失重写一次(VS Code 重命名翻车) | W4 复盘:README 写两个数字+为什么两阶段;装饰器注册待工具≥8;**召回局限**:k=3 可能漏工具(复合任务需多工具时),100% 是因假工具区分度高,语义相近工具会降——面试要诚实讲 |
| Week 3 | 06-26~07-02 | 100%(FastAPI + DB 持久化全做完;已从 SQLite 迁移到 MySQL) | server.py: FastAPI 把 agent 封成 `/chat` POST 接口 + Pydantic ChatRequest 校验;db.py: init_db / create_conversation / add_message / get_messages 四函数;pymysql 驱动;MySQL 8.4 本地服务 + mini_coder 库 + 专用用户;多轮对话验证通过:第二轮带 conversation_id 能正确回答第一轮的信息 | ~3 个有效工作日;从 `Body()` 迁移到 BaseModel 绕了一圈;端到端测试一次通过;MySQL Windows 安装踩坑:中文路径导致 my.ini 和日志文件写入失败,解决:数据目录放到 `D:\mini_code_temp\` 纯 ASCII 路径 | Week 4: Redis 缓存 + 限流 + provider 超时重试(原计划) |
| Week 4 | 07-03~07-04 | 100%(tenacity 重试 + Redis 缓存 + 限流 + test_w4.py 12 测试全过) | provider.py: @retry 装饰器;cache.py: Redis 缓存层(sha256 key + TTL);server.py: 固定窗口限流(10次/分钟/ip) + 缓存集成 + conv_id 存在性校验;test_w4.py: 12 个单元测试(重试1/缓存4/限流4) | 模型按计划一天完成(计划 ~3 day-unit);缓存 key 设计经历两轮修正(messages → request.message);W4 原计划"前置学习 1 天+代码 3 天",实际前置学习已在前几天完成 | Week 5: 记忆沉淀闭环(reflection + 复用 MySQL) |
| Week 5 | 07-05 | 100%(记忆存储 + 检索 + 反思 + test_w5.py 9 测试全过) | db.py: memories 表(JSON embedding) + add_memory/get_memories;memory.py: retrieve_memories(query, k=5) 语义检索,复用 retriever.top_k;reflection.py: LLM 反思 prompt 提取用户知识;server.py: 请求时注入记忆 + 回答后触发反思(≥6条消息) | 一天完成;ChatCompletionMessage 混入 messages 导致 isinstance 过滤;W5 原评估完成概率 55% 被低估——retriever 复用节省了大量工作 | Week 6: 权限分级 + Prompt 注入防御 |
| Week 6 | 07-04 | 100%(权限分级 + 注入防御 + test_w6.py 6/6 全过) | tool.py: TOOL_RISK_LEVELS + ALLOWED_LEVELS;agent.py: allowed_risk 参数 + 权限检查;security.py: 新建,正则检测 4 种注入模式;server.py: ChatRequest 加 permission_level + system prompt 加固 + 注入检查前置;6 测试(2 纯数据 + 2 LLM 端到端 + 2 注入检测) | 同一天完成;permission_level="user" 传进 agent 却查 ALLOWED_LEVELS["user"] KeyError——概念混淆:用户角色(user/admin)和风险等级(low/medium/high)是两套体系,没对齐;注入检查初版放在建对话之后,攻击请求能在 DB 留垃圾行——先安检再干活 | 第二阶段 D1-D2 |
| 深化 D1-D2 | 07-05 | 100%(Tool 类化 + 30 工具 + 四阶段路由) | D1: Tool 基类(name/description/parameters/risk_level/tags/examples/execute/to_schema);5 旧工具迁移 + 25 新工具(文件13/Web3/系统4/文本6/Git4);删除散装字典 TOOL_FUNCTIONS/TOOL_RISK_LEVELS,联动改 agent.py/registry.py/retriever.py。D2: 意图分类(_classify_intent,关键词匹配不调 LLM)+ 目录粗筛(按 tags 从 30→5-10 候选)+ embedding top-k + LLM 精排四阶段路由;7 条手工测试全部命中正确工具 | 30 工具一次性批量写的,用户读代码理解而非手写;D2 拆分到"工具分类/路由"层面而非完整 Skill 编排层——真正的 Skill=工具编排留给 D7 主从 Agent;路由数字(30 工具下四阶段准确率)待 W7 评测系统化 | D0: Capability 架构 |
| 深化 D0 | 07-05 | 100%(Capability 协议 + AgentPipeline) | capability.py: Capability 基类(on_request/on_response 两个钩子)+ PipelineContext 数据类 + AgentPipeline(按序编排);builtin_capabilities.py: SecurityCapability/ConversationCapability/MemoryCapability/CacheCapability/ReflectionCapability;server.py chat() 从手动堆砌 50 行缩到 30 行 Pipeline 编排 | D0 架构为后续所有深化打基础——D3 Memory、D4 Security、D9 RAG 都只需新建 Capability 类并注册,不再改 core | D3: 记忆升级（开始模块化重构） |
| 回退到 D0 | 07-06 | 100%(安全回退完成) | 返回 D0 版本（五层架构，2284 行 23 文件） | 用户感觉功能一下子加太多，无从下手；将所有深化内容保存为补丁 D:\mini_code_d3_d11.patch (113KB)，恢复说明 evaluation/rollback_summary.txt | 按补丁文件逐步恢复，按 CL 历史逐个 cherry-pick |
| 重建 D3 | 07-07~07-08 | 100%(链路完成，效果数字待评测) | typed memory、公共 JSON 解析、完全去重、embedding 相似召回、LLM merge、时间衰减、使用次数和多因子重排；MySQL 状态追踪与测试通过 | 复杂语义冲突仍依赖 LLM；当前证明控制流正确，未证明真实去重准确率 | D4 安全深化；详见 D3_MEMORY_NOTES.md |
| 重建 D4 | 07-09 | 100%(计划功能完成) | workspace 路径白名单、risk 权限、人工确认、pending resume、工具失败回喂、audit log；D4 回归通过 | 安全职责从 agent 中继续拆到 security/audit；确认状态和审计仍未数据库化 | D5 上下文治理；详见 D4_SECURITY_NOTES.md |
| 重建 D5 | 07-10~07-12 | 100%(工程链路完成，摘要效果待评测) | D5.0~D5.7：消息职责分离、token 预算、轮次窗口、七字段摘要、公共 LLM 输出校验、Capability、MySQL 滚动摘要与 message_id 游标、分块滚动压缩；真实 MySQL upsert/version/cleanup 通过 | 旧四步计划没有覆盖重复全量摘要和摘要器自身溢出，因此扩展到 D5.7；真实 LLM 保真率和 20+ 轮压缩数字尚未测试 | D6；详见 D5_CONTEXT_NOTES.md |

---

## 六、第二阶段：系统深化（2026-07-04 ~ 2026-09 初，约两个月）

> W1-W6 主线和 D0-D5 深化已经完成。当前系统具备 ReAct、30 工具、FastAPI、MySQL、Redis、Capability Pipeline、记忆、安全和上下文治理，但评测数字、流式接口、可观测性、主从 Agent 和特色 RAG 仍未完成。
>
> 第二阶段目标：**把系统做厚**——增加工具、升级架构、补齐简历上每条亮点背后都能扛追问的能力。

### 架构目标：可组合的能力协议（贯穿所有深化方向）

> 当前问题：每个模块（Security/Memory/Cache/Reflection）在 `server.py` 的 `chat()` 里手动堆砌。加一个新能力要在 3-4 个地方改代码。
>
> 新架构三层抽象：

| 抽象 | 职责 | 例子 |
|---|---|---|
| **Tool 类** | 工具自描述（name/description/parameters/risk_level/tags/examples）+ execute | `WebSearchTool`、`ListFilesTool` |
| **Capability 协议** | 可插拔的能力模块，统一 `on_request`/`on_response` 接口 | `MemoryCapability`、`SecurityCapability`、`CacheCapability` |
| **AgentPipeline** | 编排层，把 Capability 串成流水线，替代 `chat()` 的手动拼接 | 限流→安检→记忆→缓存→agent→反思 |

> 面试价值：**"我设计了一套可组合的能力协议，每个安全/记忆/缓存模块遵循统一接口，Pipeline 按需编排，增加能力只需新建 Capability 类——不需要改 agent 核心逻辑。"**

---

### 深化清单（按优先级）

#### 第一波：做厚基础（1-2 周）

##### D1 · 加工具 + Tool 类化

| 子任务 | 说明 | 消化什么 |
|---|---|---|
| D1.1 设计 Tool 基类 | `name`/`description`/`parameters`/`risk_level`/`tags`/`examples`/`execute()`——每个工具是一个自描述对象 | 为什么类比散装 dict+函数好：一处定义、自描述、可扩展 |
| D1.2 迁移现有 5 工具 | read/write/edit/grep/bash 从散装改为 Tool 类实例 | 重构不改行为——验证抽象层是否正确 |
| D1.3 加 `list_files` | 列出目录文件，参数：path | 工具的基本模式：输入→处理→返回字符串 |
| D1.4 加 `create_directory` | 创建目录，参数：path | 同上 |
| D1.5 加 `web_search` | 调搜索 API，参数：query | 第一个外部 API 工具——需要网络、错误处理、结果截断 |
| D1.6 加 `web_fetch` | 读 URL 内容，参数：url | 搭配 search 用，agent 能"搜→读→总结" |

**验收**：9 个工具（5 旧 + 4 新）全部 Tool 类化，ToolRegistry 通过 tags 筛选工具子集

##### D2 · Skill 体系升级

| 子任务 | 说明 | 消化什么 |
|---|---|---|
| D2.1 Tool 加 tags + examples | 每个工具标注分类标签（file/web/system/search）+ 2-3 个使用示例 | 元信息如何帮助路由——tags 做粗筛，examples 帮 LLM 理解使用场景 |
| D2.2 Skill 目录分层 | `ALL_TOOLS` → `TOOL_CATEGORIES`（file_tools/web_tools/system_tools），支持按分类注册和检索 | 目录分层的工程意义：工具多了之后按域筛选减少候选集 |
| D2.3 意图分类器 | 用户 query 进来先判断"要做什么类型的操作"（读文件？搜索？执行命令？），再选对应工具目录 | query 意图识别不是黑魔法——关键词+embedding 就够了 |
| D2.4 路由升级 | 意图分类 → 目录粗筛 → embedding top-k → LLM 精排（完整四阶段） | 每一层为什么存在、各解决什么问题 |

**验收**：路由准确率在 30+ 工具规模下保持 >90%，token 节省有对比数字

---

#### 第二波：已有模块纵深（1-2 周）

##### D3 · 记忆升级

| 子任务 | 说明 | 消化什么 |
|---|---|---|
| D3.1 MemoryCapability | 把 memory.py 的逻辑封成 Capability 类（`on_request` 注入记忆） | 理解协议模式——所有能力模块长一样 |
| D3.2 记忆自动分类 | reflection 提取时让 LLM 打标签（fact/preference/skill/task），存入 `memory_type` | 为什么分类重要——不同类型记忆有不同的检索优先级和使用场景 |
| D3.3 记忆去重 | 新记忆跟已有记忆做语义相似度比较，重复的合并而不是新增 | embedding 的另一个用途：不只是检索，还能判断"是不是已经知道了" |
| D3.4 时间衰减 | 旧记忆的检索分数按时间打折，越久越不重要 | 引入时间维度——不是所有记忆平等 |
| D3.5 增量索引 | 不再每次 `get_memories()` 扫全表，维护一个内存索引 + 新增时更新 | 性能意识——数据量大了全表扫描不可接受 |

**验收**：50 条记忆中重复的不超过 3 条，旧记忆排序低于新记忆，检索延迟 <50ms

##### D4 · 安全升级

| 子任务 | 说明 | 消化什么 |
|---|---|---|
| D4.1 SecurityCapability | 把注入检测+权限检查封成 Capability 类（`on_request` 安检） | 协议复用 |
| D4.2 路径白名单 | write_file/edit_file/bash 限制在 `D:\mini_code\` + 用户指定安全目录，越界拒绝 | 为什么最小权限还要加路径限制——权限只管"能不能用这个工具"，不管"用在哪" |
| D4.3 人工确认机制 | high 级工具在 user 模式下触发"此操作有风险，确认执行？"，前端弹窗确认后才执行 | 安全最后一公里——代码拦不住的要交给人判断 |

**验收**：write_file 写 `C:\Windows\` 被拒绝（路径越界）；bash 在 user 模式下弹确认

---

#### 第三波：新能力（2-3 周）

##### D5 · 分层上下文压缩

> **2026-07-11 状态：D5.0~D5.7 工程链路已完成。** 原四步方案已被实际实现替代，详细数据流、测试和限制见 `D5_CONTEXT_NOTES.md`。

| 子任务 | 实际实现 | 当前状态 |
|---|---|---|
| D5.0 会话职责统一 | ConversationCapability 统一加载和持久化，移除 server 重复写消息 | 完成 |
| D5.1 消息分层 | `messages`、`conversation_messages`、带 ID 的 `conversation_records` 分离 | 完成 |
| D5.2 上下文预算 | 分别估算 messages 和 tool schemas token，按阈值触发 | 完成；启发式估算 |
| D5.3 轮次窗口 | 最近 N 轮和当前 user 保留原文，较早完整轮次进入压缩区 | 完成 |
| D5.4 结构化摘要 | 七字段 ContextSummary + 通用 JSON 语法校验 + D5 业务校验 | 完成 |
| D5.5 Capability 接入 | Conversation 后、Memory 前重建主 Agent 输入 | 完成 |
| D5.6 滚动持久化 | MySQL 保存摘要、message_id 游标、token 指标和 version | 完成；真实 MySQL 测试通过 |
| D5.7 分块压缩 | 摘要独立预算、轮次优先分块、超长消息切片、逐块滚动合并 | 完成 |

**已验收**：格式、窗口、分块、失败回退、游标、版本递增和真实 MySQL 往返。

**未验收**：20+ 轮真实 LLM 压缩率、摘要语义保真率、压缩前后任务成功率。因此暂时不能对外声称“token 增长已从线性变为亚线性”或“压缩率 >50%”。

##### D6 · 流式输出 SSE

| 子任务 | 说明 | 消化什么 |
|---|---|---|
| D6.1 provider 流式 | `chat_with_deepseek` 加 `stream=True`，返回 generator | OpenAI SDK 的 stream 模式——每次 yield 一个 chunk |
| D6.2 `/chat/stream` 端点 | SSE 格式，前端 EventSource 消费 | HTTP 流式协议——不是 WebSocket，是单向推送 |
| D6.3 Pipeline 适配 | AgentPipeline 支持 streaming 模式，Capability 可以注册 `on_chunk` 回调 | 协议扩展——加新模式不改旧逻辑 |

**验收**：前端打字机效果，首个 token 延迟 <1s

---

#### 第四波：反馈记录 + 可观测性（D10 + D11）

##### D10 · 反馈记录（精简后与 D11 联动）

> **2026-07-11 决策：砍掉“反馈驱动路由权重自动调整”。** 当前项目没有足够真实反馈样本和离线评测保护，自动改权重容易放大噪声，不能为了简历使用“自进化”说法。

保留的工程范围：

| 子任务 | 说明 | 与 D11 的关系 |
|---|---|---|
| D10.1 反馈接口 | `/feedback` 保存点赞/踩、原因和对应 run_id | 反馈必须能关联一次 trace |
| D10.2 基础分析 | 按任务类型、工具、失败阶段统计负反馈 | 用 trace 判断是路由、工具还是模型回答问题 |
| D10.3 查询接口 | 查询单次 run 的反馈和执行链路 | 与 trace 查询共同完成问题回溯 |

明确不做：

```text
根据少量点赞/踩自动修改 registry.select() 权重
没有离线回归保护就让线上反馈直接改变行为
把普通反馈统计包装成自进化系统
```

**验收**：一次负反馈能通过 run_id 定位对应工具调用链和失败阶段。

##### D11 · 可观测性（链路追踪）

> 来源：业界标配（LangSmith/Logfire/Phoenix），没有 trace 的 agent 是黑盒——面试必问"出问题了怎么排查"。
>
> 当前执行顺序中 D10 和 D11 合并开发：先有 run_id 和 trace，反馈才有可定位对象。

| 子任务 | 说明 | 消化什么 |
|---|---|---|
| D11.1 Trace 数据结构 | `AgentTrace`：run_id / iteration / tool_name / tool_args / tool_result / duration_ms / success / timestamp | 每一轮 tool call 都是一条 trace，结构化存储 |
| D11.2 埋点 | 在 `agent.py` 的 `run()` 里加 trace 记录（调工具前后各打一个点） | 埋点不是事后补——要在核心循环里预留 |
| D11.3 traces 表 + 查询 | `db.py` 加 `traces` 表 + `get_traces(run_id)` 查询 | 排查问题时 SQL 一查就能看到 agent 的完整执行路径 |
| D11.4 Trace 可视化页面 | `/admin/traces` 页面：时间线展示每个 run 的工具调用链（调了什么 → 耗时 → 成功/失败） | 面试能讲"我做了可观测性面板，能回溯每次 agent 调用的完整路径" |
| D11.5 告警规则 | 单次 run 超过 5 轮 tool call 或单工具耗时 >10s → 前端标红 | 不是事后排查，是主动发现问题 |

**验收**：跑一次 agent → `/admin/traces` 能看到完整调用链（每一步工具名 + 耗时 + 成功/失败）

---

#### 第五波：主从 Agent 与框架对比（3-4 周）

##### D7 · 主从双 Agent

| 子任务 | 说明 | 消化什么 |
|---|---|---|
| D7.1 SubAgent 工具 | 把"调用子 agent"包装成一个 Tool——主 agent 通过 tool call 来 spawn 子 agent | 为什么用 tool call 而不是独立的 agent 通信协议——复用现有基础设施，减少复杂度 |
| D7.2 子 agent 隔离 | 子 agent 只能访问主 agent 授权的工具子集 + 路径范围 | 权限传递——主 agent 的权限不等于子 agent 的权限 |
| D7.3 结果最小化 | 子 agent 只返回结构化结果摘要，不返回完整对话历史 | 防止 token 爆炸——子 agent 内部循环不应该污染主 agent 上下文 |
| D7.4 LangGraph supervisor 实现 | 用 LangGraph 的 StateGraph 重写主从模式做对比 | 自实现 vs 框架——同样的功能，不同实现方式的 trade-off |

**验收**：主 agent 能 spawn 子 agent 读文件并只返回摘要；自实现和 LangGraph 版本有对比

##### D8 · LangChain/LangGraph 封装层

| 子任务 | 说明 | 消化什么 |
|---|---|---|
| D8.1 agent_langgraph.py | 用 LangGraph 的 `create_react_agent` 重写 agent loop | 框架替你做了什么——`agent` node + `tools` node + conditional edge |
| D8.2 自实现 vs LangGraph 对比 | 同一组测试用例跑两个版本：延迟/代码量/token 消耗/错误处理差异 | 框架不是银弹——我们的自实现更轻量（42 行），框架在复杂路由上有优势 |
| D8.3 跑同一批测试 | 用 test_w1.py 的复合任务在两边跑，出对比数字 | 有数字的对比才有说服力 |

**验收**：对比表完整（延迟/代码量/功能覆盖/错误处理），能讲清"什么时候用框架什么时候自己写"

#### 第六波：RAG 特色深化

##### D9 · RAG 能力（完整框架后集中实现）

> RAG 是 Agent 最常见的知识能力之一，跟 Memory 不同：Memory 是系统自动提取的长期知识，RAG 是用户主动提供、可以追溯来源的文档知识。当前决定先完成可投递框架，再集中实现和学习 RAG，而不是在主线中快速堆一个普通向量检索 Demo。

| 子任务 | 说明 | 消化什么 |
|---|---|---|
| D9.1 文档摄取 | 上传文档、解析、清洗、切片并保存来源元数据 | chunk 边界、overlap 和文档结构如何影响召回 |
| D9.2 混合检索 | embedding 语义召回 + 关键词/BM25 召回 | 单一路向量检索在哪些 query 上会失败 |
| D9.3 重排与引用 | 对候选片段重排，回答中返回文档和片段来源 | 怎样降低“召回相关但回答无依据” |
| D9.4 RAGCapability | 检索结果通过 Capability 注入，不污染真实 conversation | RAG、Memory、Context 三者如何协作 |
| D9.5 评测 | 构造问答集，测 Recall@K、MRR、答案正确率、引用准确率和延迟 | 用数字证明特色机制有效，而不是只展示能回答 |

**验收**：普通向量召回、混合检索和重排方案有同一数据集上的对比数字；回答能够返回可核对的来源。

---

#### 第零层：工程定位与场景验证（贯穿整个深化过程）

> **这不是代码模块，是"串故事"的层。** 面试官不指望简历项目有真实用户，但会判断你脑子里有没有生产意识。Demo 思维的人讲"我做了什么功能"，工程思维的人讲"我做了这个功能，同时知道它在什么情况下会崩、崩了怎么降级"。

##### 用户画像

> 面向个人开发者（而非团队/企业）的自托管编码助手。核心使用场景：代码重构、bug 定位、新功能添加、项目代码理解。

| 角色 | 需求 | 示例 query |
|---|---|---|
| 个人开发（1 人） | 理解已有代码、修复 bug、加小功能 | "agent.py 第 26 行 KeyError 了，帮我定位并修复" |
| 学习场景 | 解释代码逻辑、对比方案 | "这个函数为什么用 try/except 包？不包会怎样？" |
| 代码维护 | 重构、加 type hint、清理冗余 | "给 tool.py 的所有函数加完整的 docstring" |

**不面向的**：多仓库协同、CI/CD 集成、权限复杂的多人团队协作。

##### 3 个端到端验证场景

| 场景 | 输入 | 期望输出 | 量化指标 |
|---|---|---|---|
| S1 Bug 修复 | 给一段有 bug 的代码 + error trace，如 agent.py KeyError | agent 调 read_file 读代码 → grep 定位 → edit_file 修复 → bash 跑测试验证 | 最多 3-4 轮 tool call，修复后可运行 |
| S2 重构 | 一个 100+ 行的模块，要求"提取公共逻辑，加 type hint" | agent 读 → 分析重复模式 → edit_file 提取函数 → 写回 | 重构后代码可运行，type hint 完整 |
| S3 新功能添加 | "参考 tool.py 的模式，加一个 new_tool" | agent 读已有工具 → 理解模式 → write_file 写新工具 → 注册到 ALL_TOOLS | 新工具 schema 格式一致、execute 有 try/except |

**这 3 个场景不是"测过一次就算"——每一次深化后重跑，看数字是否变好。**

##### 边界定义（面试话术——"不做什么"比"做什么"更重要）

| 维度 | 明确做 | 明确不做 | 面试怎么讲 |
|---|---|---|---|
| 文件操作 | project_dir 内任意路径 | 系统目录（C:\Windows、/etc）→ D4 路径白名单拦截 | "路径白名单限制在项目目录，越界直接拒绝——不是 bash 黑名单，是文件系统层面的硬限制" |
| 命令执行 | 简单命令（echo/ls/git status） | 删除（rm/del）、修改系统配置（chmod 777/shutdown）→ DANGEROUS_COMMANDS 黑名单 | "bash 工具做了两层防护：shell 层黑名单拦截危险命令，加上权限分级——user 默认不能调 bash" |
| 网络访问 | web_search / web_fetch 两个工具 | 其他任意 HTTP 请求（agent 不能随便发网络请求） | "网络能力限定在搜索和文档读取，不是通用 HTTP client——减少 SSRF 和敏感数据外泄风险" |
| 数据持久化 | MySQL conversations/messages/memories/traces | 不做数据自动清理（保留给用户手动管理） | "数据库不自动删数据——因为用户可能想回看历史对话。清理策略留给使用者决定" |
| 并发 | 单 request 内串行工具调用 | 不做并发工具调用（一个 tool call 完成再做下一个） | "没有并行工具调用——因为工具之间可能有文件依赖，串行执行保证一致性" |

##### 失败模式与降级策略（面试话术——"这个依赖挂了会怎样"）

| 故障 | 系统行为 | 实现方式 | 面试怎么讲 |
|---|---|---|---|
| DeepSeek API 挂了 | 返回 500，提示"LLM 服务不可用，请稍后重试" | provider.py `@retry` 3 次后抛异常，server.py catch → HTTP 500 | "三次指数退避重试后再失败才返回 500，不会无脑重试到超时" |
| DeepSeek API 返回乱码/非预期格式 | try/except 包 json.loads，解析失败返回错误信息 | agent.py 的 json.loads(tc.function.arguments) | "LLM 生成的 tool call 参数不可靠——我用 try/except 兜底，解析失败不会整个 loop 崩，只反馈错误给模型让它重试" |
| Redis 挂了 | 缓存自动 skip，不影响核心功能（只是变慢） | cache.py `check_cache`/`set_cache` 加 try/except，连接失败返回 None | "缓存的定位是优化层不是必需层——Redis 不可用时 check_cache 返回 None，走完整 LLM 调用，系统降级但不崩溃" |
| MySQL 挂了 | 写操作失败返回错误响应，不丢数据（请求者知道失败了） | db.py 每个函数可以加 try/except，当前未加（TODO） | "当前 DB 层还没有降级策略，如果需要生产化，会在 db.py 函数内加 try/except，连不上时抛明确错误而不是让 FastAPI 炸 500" |
| 用户输入超长 | system prompt + 对话历史 + tool schemas 超过模型 context | D5 上下文压缩作为对策 | "超过阈值时触发滑动压缩——不暴力截断，而是对旧对话生成结构化摘要替代原文" |

> 注意：MySQL 降级是诚实说的——"当前还没做，但如果要上生产会这么做"。面试官欣赏诚实 > 假装完美。

##### Demo vs 工程项目面试话术对比

| 面试官问 | Demo 回答（扣分） | 工程回答（加分） |
|---|---|---|
| "这个项目解决了什么问题？" | "实现了一个 AI agent，能调工具" | "面向个人开发者的自托管编码助手。三个核心场景：bug 修复、代码重构、新功能添加。定义了每个场景的验收标准和失败模式" |
| "你怎么验证 agent 是不是做对了？" | "工具调成功了，没有报错" | "我在三个端到端场景上跑了一遍，每个场景有成功率和 token 消耗基线。场景不是'调 read_file 成功'，而是完整的任务——比如给定 bug 代码 + error trace，agent 定位并修复、验证可运行" |
| "系统出问题了怎么排查？" | "看报错日志" | "每次 agent run 都有完整的 trace 记录——调了什么工具、参数是什么、耗时多少、成功/失败——在 /admin/traces 面板可以回溯完整调用链。出问题时先看 trace，不是先看代码" |
| "Redis/MySQL 挂了会怎样？" | "额……会报错吧" | "我的设计分层——Redis 是优化层，挂了自动 skip，系统降级但不崩溃，走完整 LLM 调用。DeepSeek API 三次指数退避重试后才返回 500。MySQL 当前还没做降级，如果上生产会在 db 层加 try/except 返回明确错误" |
| "这个项目的边界在哪？不做什么？" | "能做很多事，基本都能做" | "明确不做的事：不操作用户系统目录（路径白名单拦截）、不执行删除类命令（黑名单 + user 权限封 bash）、不做并发工具调用（保证文件依赖一致性）、不自动清理数据库（保留给用户管理）" |

##### 简历-面试对照表

> 简历上写了什么 ≠ 面试能讲什么。每条简历 bullet 背后必须有话术。

| 简历 bullet | 面试能展开的点 | 会被追问的点（提前准备） |
|---|---|---|
| Skill 分层路由系统 | 四阶段路由流程、token 节省数字、RAG 作为一个 Skill | "k 值怎么选的？""embedding 模型为什么用 bge？""30 工具 100% 准确率，100 工具会掉到多少？" |
| 自适应记忆沉淀 | 反思触发时机、去重逻辑、时间衰减公式 | "去重阈值怎么定的？""时间衰减参数调优过吗？""跟 RAG 的区别是什么？" |
| 分层上下文压缩 | 压缩触发条件、结构化笔记格式、滑动窗口大小 | "压缩后的摘要质量怎么评估？""压缩率怎么算的？""有没有对比过不压缩的效果？" |
| 主从双 Agent | 权限传递、结果最小化、自实现 vs LangGraph | "为什么用 tool call 而不是独立通信协议？""子 agent 崩了主 agent 怎么感知？" |
| 多层安全审查 | 四层：正则→权限→路径白名单→人工确认 | "正则被绕过怎么办？""人工确认怎么实现的？""注入检测误拦了怎么处理？" |
| 全链路可观测 | trace 数据结构、面板、告警规则 | "跟 LangSmith 的区别？""trace 数据量大了怎么办？""怎么区分正常慢和异常慢？" |
| 离线评测 | ablation 方法、样本构造、结果对比 | "样本怎么构造的？""为什么不用 SWE-bench？""评测结果的置信度？" |

---

#### 第五波：评价 + 交付（由助手快速完成）

| 任务 | 说明 |
|---|---|
| 评测 | 对路由准确率、缓存命中率/延迟对比、注入拦截率、记忆检索召回率做 ablation |
| Docker | Dockerfile + docker-compose.yml（FastAPI + MySQL + Redis 一键启动） |
| README | 架构图 + 各模块数字 + 快速开始 |
| 简历整理 | 3-5 条 bullet，每条带数字 |

---

### 深化清单总览

| 编号 | 方向 | 预计工作量 | 简历对应 | 当前状态 / 完成概率 |
|---|---|---|---|---|
| D1 | 加工具 + Tool 类化 | 已投入 | 工具体系基础 | 已完成 |
| D2 | Skill 体系升级 | 已投入 | 分层路由 | 已完成，效果数字待统一评测 |
| D3 | 记忆升级 | 已投入 | 记忆沉淀闭环 | 工程链路完成，效果数字待评测 |
| D4 | 安全升级 | 已投入 | 权限与安全审查 | 计划功能完成，安全评测待补 |
| D5 | 上下文治理 | 已投入 | 滚动结构化压缩 | D5.0~D5.7 完成，语义评测待补 |
| D6 | 流式 SSE | 1-2 天 | —（体验向） | 85% |
| D10 | 反馈记录 | 与 D11 合并 | 问题定位辅助 | 85%；自动调权重已砍 |
| D11 | 可观测性 | 2-3 天 | 执行链路回溯 | 80% |
| D7 | 主从双 Agent | 5-6 天 | 主从双 Agent 协作 | 45% |
| D8 | LangGraph 封装 | 2-3 天 | —（对比加分） | 75% |
| D9 | RAG 特色深化 | 5-7 天 | 可追溯知识检索 | 60% |
| 评测 | 出数字 | 2-3 天 | 离线评测体系 | — |
| 交付 | Docker+README+简历 | 2-3 天 | — | — |

**当前剩余量级**：完成 D6、D10+11、D7、D8 和首轮交付约需 12-18 个有效工作日；RAG 特色深化和专项评测另需约 7-12 个有效工作日。最大风险仍是 D7 和真实评测，不再把已完成的 D5 计入风险。

---

### 简历最终瞄准（每条做完后能扛 3-5 轮追问）

| 简历 bullet | 对应深化 | 可量化的数字 |
|---|---|---|
| Skill 分层路由系统：意图识别→目录粗筛→embedding top-k→LLM 精排，在工具规模增长时控制候选噪声 | D1+D2 | 路由准确率、候选缩减率、token 节省率 |
| 自适应记忆沉淀：执行→反思→分类存储→去重→时间衰减→按需复用闭环，跨会话上下文复用 | D3 | 检索召回率、去重准确率、检索延迟 |
| 滚动上下文治理：按 token 阈值切分旧轮次，生成七字段结构化摘要，以 MySQL message_id 游标增量合并，并在超长输入下分块压缩 | D5 | 关键状态保留率、压缩率、任务成功率、额外延迟 |
| 可追溯 RAG：文档摄取→混合召回→重排→引用返回，并通过统一数据集比较不同检索方案 | D9 | Recall@K、MRR、答案/引用准确率、延迟 |
| 主从双 Agent：主 Agent 统一规划+权限分发，子 Agent 以 Tool Call 被控执行，自实现 vs LangGraph 对比 | D7+D8 | 代码量对比、延迟对比 |
| 多层安全审查：规则过滤+路径白名单+权限分级+人工确认+审计记录 | D4 | 注入拦截率、误拦率、越权阻断率 |
| 全链路可观测：Agent Trace 记录每轮工具调用的耗时/成功/失败，支持可视化回溯与异常告警 | D11 | 平均迭代轮次、工具调用成功率 |
| 离线评测：自建任务样本，路由/缓存/记忆/安全的联合 ablation 对比 | 评测 | 各模块 ablation 数字 |

---

### 2026-07-12 校准后的交付概率

| 目标 | 概率 |
|---|---|
| 7 月内完成 D6、D10+11、D7、D8 和可投递的 README/简历初稿 | **60%** |
| 7 月内完成上述框架，但 D7 降级为单个受控 SubAgent demo | **80%** |
| 8 月底完成有混合检索、重排、引用和评测数字的特色 RAG | **55%** |
| 8 月底至少完成可投递框架 + 一个有真实对比数字的核心亮点 | **85%** |

---

## 七、项目结构约定

- repo:`D:\mini_code\`
- references:`D:\mini_code_refs\`(smolagents / anthropic-cookbook / gptme)
- 包管理:uv
- 主模型:`deepseek-v4-pro`(代理 / 工具调用 / 推理)
- 辅模型:`deepseek-v4-flash`(便宜对比 / 简单分类)
- 配置:`.env`(本地)+ `.env.example`(提交)

### 技术栈(随路线推进逐步引入,现已有 ✅)

| 层 | 技术 | 引入时机 |
|---|---|---|
| LLM 调用 | OpenAI SDK + DeepSeek ✅ | Week 1 |
| Agent 内核 | 自写 ReAct loop ✅ | Week 1 |
| 检索 | embedding + 向量召回 | Week 2 |
| 接口层 | FastAPI ✅ | Week 3 |
| 持久化 | MySQL 8.4 ✅(pymysql, 本地服务; Week 3 先 SQLite 验证 schema, 后迁移 MySQL) | Week 3 |
| 缓存/限流 | Redis | Week 4 |
| 部署 | Docker | Week 8 |
| 评测 | pytest + 自建任务集 | Week 7 |

- 详细目录树:后端层引入(Week 3)后补

---

## 八、元规则

- **每周一**:用户填第四节"本周目标"
- **每周末**:助手在第五节追加一行评估,并校准第六节概率分布
- **目标动态调整**:不固守初版野心。若 Week N 大幅落后,Week N+1 缩小目标或砍机制
- **用户灵活安排**:某周有事可在周一调小任务量,助手不施压
- **简历最终样子**:随项目实际产出动态校准,不预设
