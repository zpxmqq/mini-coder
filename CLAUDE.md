# mini-coder · 项目指令(给助手 + 给自己)

> 这份文档每周一填本周目标,周末助手做评估。Claude 进入项目自动读取,等于持久化记忆。

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

## 五、历史周评估(校准工具)

| Week | 起止 | 计划完成度 | 实际产出 | 偏差与原因 | 下周调整 |
|---|---|---|---|---|---|
| Day 0 | 06-05 | n/a | uv 装通 / Hello DeepSeek 跑通 / .env 改造 / 三个 ref repo clone | 用约 5 小时,主要在抄+理解,基础比预想更弱(看不懂 traceback、Python 阅读量极少) | Week 1 不赶进度,优先打基础;每写一段代码必须能答 what/why/alternative |
| Week 1 | 06-06~06-24 | 100%(代码全完成,字典分发重构也做了;录视频可选,未做) | 5 工具(read/write/edit/grep/bash)+ ReAct loop + MAX_ITER + try/except + 危险命令黑名单;复合任务多步调用验证通过;agent.py 已从 5 个 if/elif 重构为 TOOL_FUNCTIONS 字典分发(87→43 行) | 实际有效工作 ~4 天 vs 计划 16 day-unit,大幅超前(Python 基础被低估 + 没抄代码全手写) | Week 2 开始 Skill 二阶段路由(embedding 召回 + LLM 精排);装饰器自动注册工具待工具≥8个再做;bash 安全 Week 6 升级白名单/沙箱;残留 hello_ai.py/test_document.txt 待清理 |
| Week 2 | 06-25~06-25 | ~90%(召回主干+重构+真数字全完成;README 待补) | embedding 二阶段路由:retriever.py(embed/top_k/route)+ ToolRegistry 类封装工具管理;5真+25假=30工具召回测试 **准确率 10/10=100%,token 7822→1506 节省 81%**;架构重构:召回逻辑从 main 抽到 ToolRegistry,ALL_TOOLS/TOOL_FUNCTIONS 集中到 tool.py,加工具只改一处 | 1 天完成(本地 embedding 比预想顺,bge-small-zh CPU 够用);中途文件丢失重写一次(VS Code 重命名翻车) | W4 复盘:README 写两个数字+为什么两阶段;装饰器注册待工具≥8;**召回局限**:k=3 可能漏工具(复合任务需多工具时),100% 是因假工具区分度高,语义相近工具会降——面试要诚实讲 |
| Week 3 | 06-26~07-02 | 100%(FastAPI + DB 持久化全做完;已从 SQLite 迁移到 MySQL) | server.py: FastAPI 把 agent 封成 `/chat` POST 接口 + Pydantic ChatRequest 校验;db.py: init_db / create_conversation / add_message / get_messages 四函数;pymysql 驱动;MySQL 8.4 本地服务 + mini_coder 库 + 专用用户;多轮对话验证通过:第二轮带 conversation_id 能正确回答第一轮的信息 | ~3 个有效工作日;从 `Body()` 迁移到 BaseModel 绕了一圈;端到端测试一次通过;MySQL Windows 安装踩坑:中文路径导致 my.ini 和日志文件写入失败,解决:数据目录放到 `D:\mini_code_temp\` 纯 ASCII 路径 | Week 4: Redis 缓存 + 限流 + provider 超时重试(原计划) |

---

## 六、8 周路线(参考,可动态调整)

> **2026-06-08 重排**:对齐目标岗位 JD,把后端工程化(FastAPI/MySQL/Redis/重试)插进主线,原 Week 3「主从双 Agent」因难度大(45%)+ JD 不要求,移到 stretch backlog(见下表)。**砍 ≠ 删**:前面提前完成就继续做,最终目标仍是全部机制做完。

| Week | 主题 | 8 周末完成概率 |
|---|---|---|
| 1 | ReAct loop + 5 原子工具(read/write/edit/bash/grep) | 85% |
| 2 | Skill 二阶段路由(embedding 召回 + LLM 精排,RAG 雏形) | 65% |
| 3 | **后端封装**:FastAPI 把 agent 封成 HTTP API + SQLite 持久化对话/记忆 ✅ | 100%(已完成) |
| 4 | **后端工程化**:Redis 缓存 + 限流 + provider 层超时重试 + 并发控制 | 65% |
| 5 | 记忆沉淀闭环(reflection + 复用 Week3 的 MySQL) | 55% |
| 6 | 权限分级 + Prompt 注入防御 | 65% |
| 7 | 评测搭建 + ablation(SWE-Lite 子集) | 50%(常被低估) |
| 8 | README 终稿 + **Docker 部署** + demo 视频 + 简历整理 | 80% |

### Stretch backlog(主线提前完成则继续做,目标是全部完成)

| 机制 | 原计划 | 为何移后 | 完成概率 |
|---|---|---|---|
| 主从双 Agent(LangGraph supervisor) | 原 Week 3 | 架构难度大,JD 不要求,性价比低 | 30% |
| 上下文压缩 + DeepSeek 磁盘缓存利用 | 原 Week 4 | 优化向,非 JD 硬需求 | 40% |
| 流式输出 / Web UI | 始终在列 | 体验向,后端 API 做完再说 | 40% |

### 8 周末交付概率分布(初版评估,每周末校准)

| 目标 | 概率 |
|---|---|
| 完整 6 机制 + 完整评测 + 真数字 | **30%** |
| 6 机制 + 部分评测 + 真数字 | **40%** |
| 3-4 机制深做透 + 1-2 stub + 局部评测 | **75%** |
| 至少 1 个能扛追问的核心机制 | **85%** |
| 比 daily-planner 更强且能扛追问的项目 | **65%** |

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
