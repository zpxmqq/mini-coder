# mini-coder · 项目指令(给助手 + 给自己)

> 这份文档每周一填本周目标,周末助手做评估。Claude 进入项目自动读取,等于持久化记忆。

---

## 一、项目目标

复刻并精简 Claude Code 架构的轻量 AI Coding Agent。简历主推项目。

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

- [ ] **B1 项目骨架**(2 day-unit / Phase A):`uv init` 切项目模式;`test_api.py` 拆成 `provider.py` + `main.py`;全函数加 type hint
- [ ] **B2 数据结构 + JSON**(2 / A):dict/list/tuple 区别;`json.dumps/loads`;用 Python dict 写出符合 OpenAI 规范的 tool schema
- [ ] **B3 单工具单次调用**(3 / A 末 + C 初):读 DeepSeek function calling 文档 → 实现 `read_file(path) -> str` + schema → 模型选调 → 你 dispatch → 回喂 → 模型出最终答
- [ ] **B4 ReAct 循环**(3 / C):把 B3 包成 `while True` 循环;`MAX_ITER=10` 保命;`try/except` 兜底
- [ ] **B5 其余 4 工具**(4 / C,各 1):`write_file`(对称 read)/ `edit_file`(read+replace+write,old 找不到要报错)/ `bash`(`subprocess.run`,Win 编码坑)/ `grep`(`re` 模块或调系统 ripgrep)
- [ ] **B6 集成 demo + 复盘**(2 / C 末):真实任务"统计 D:/mini_code 所有 .py 文件总行数"应能 grep→read→read→回答;录 1 分钟视频;CLAUDE.md 第五节写 Week 1 评估

总计 16 day-unit ≈ 净可用时间,**几乎无缓冲**。

#### 想消化的知识(每条要能用自己的话讲清楚,不许背)

1. `def` / `return` / 参数;`return` 跟 `print` 完全不是一回事(B1)
2. `import` vs `from X import Y`;为什么要拆文件(B1)
3. dict / list / tuple 区别 + 使用场景(B2)
4. JSON 在 Python 里就是 dict + list 的嵌套;`json.dumps` 把它变字符串(B2)
5. **LLM 调工具的本质:模型不执行任何代码,它只是返回"我想调 X(参数 Y)"的 JSON,执行靠你的 Python 代码**(B3)
6. `with open(...) as f:` 为什么比裸 `open()` 安全(B3)
7. `while True` + `break` 退出条件;为什么 agent 必须有 MAX_ITER(B4)
8. `try / except`:什么时候该 except 什么时候让它崩(B4)
9. `subprocess.run` 返回的 `CompletedProcess` 长啥样;Windows 上 `encoding='gbk'` 的坑(B5)
10. ReAct 名字里 "Re"(Reasoning)和 "Act" 分别对应 loop 里哪几行(B4)

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
| Week 1 | (待填) | | | | |

---

## 六、8 周路线(参考,可动态调整)

| Week | 主题 | 8 周末完成概率 |
|---|---|---|
| 1 | ReAct loop + 5 原子工具(read/write/edit/bash/grep) | 85% |
| 2 | Skill 二阶段路由(embedding 召回 + LLM 精排) | 65% |
| 3 | 主从双 Agent(LangGraph supervisor) | 45%(架构难度大) |
| 4 | 上下文压缩 + DeepSeek 磁盘缓存利用 | 55% |
| 5 | 记忆沉淀闭环(reflection + SQLite) | 55% |
| 6 | 权限分级 + Prompt 注入防御 | 65% |
| 7 | 评测搭建 + ablation(SWE-Lite 子集) | 50%(常被低估) |
| 8 | README 终稿 + demo 视频 + 简历整理 | 80% |

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
- 详细目录树:Day 1 后补

---

## 八、元规则

- **每周一**:用户填第四节"本周目标"
- **每周末**:助手在第五节追加一行评估,并校准第六节概率分布
- **目标动态调整**:不固守初版野心。若 Week N 大幅落后,Week N+1 缩小目标或砍机制
- **用户灵活安排**:某周有事可在周一调小任务量,助手不施压
- **简历最终样子**:随项目实际产出动态校准,不预设
