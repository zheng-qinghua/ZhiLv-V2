# 智旅云图 · 多 Agent 架构改造规划

> 目标:把 ai-service 从「单一图 + 两个节点」升级为 **Supervisor + 专家 Agent**(LangGraph 官方模式)。
> 约束:每一步只动 1 个模块 / 几个代码文件,每步结束时服务可运行、行为可验证。
> 前置阅读:`docs/ARCHITECTURE.md`(契约)、`app/chat.py`(现状)、`docs/tutorials/langgraph-tutorial.md` 第 5、6 节。

## 0. 进度

| 步骤 | 状态 | 说明 |
|---|---|---|
| Step 1 骨架与状态拆分 | ✅ 已完成 (2026-09-22) | 新建 `graph/state.py`、`graph/params.py`;`chat.py` 改为引用。冒烟测试与改造前行为一致 |
| Step 2a Supervisor 节点 | ✅ 已完成 (2026-09-22) | `agents/supervisor.py`(7 类 intent 合并抽取)+ `agents/budget.py` + `scripts/probe_chat.py`。**话术集分类命中 15/15** |
| Step 2b 换图 | ✅ 已完成 (2026-09-22) | `agents/chitchat.py` + `graph/builder.py`(路由表)。闲聊/参数齐两条路径与改造前逐项一致 |
| Step 3a RAG 工具化 | ✅ 已完成 (2026-09-22) | `tools/rag_tool.py` 两个工具 + `rag/retrieve.py` 熔断。Milvus 挂时 11.04s → 0.00s |
| Step 3b Retriever 专家 | ✅ 已完成 (2026-09-22) | `agents/retriever.py`(function calling 循环)+ `agents/base.py`(第二个消费者出现,公共件才抽)+ 接上 `guide` 分支。**话术集 15/15,攻略回复带真实资料** |
| Step 4 Budget 专家 | ✅ 已完成 (2026-09-22) | `agents/budget.py` 加 `budget_node` + `block_state`(护栏口径统一);接上 `budget` 分支 |
| Step 5a Java 内部天气接口 | ✅ 已完成 (2026-09-23) | `InternalWeatherController` + `app.ai.service-key`。真 key 实测返回大理 4 天预报(0.51s) |
| Step 5b Weather 专家 | ⬜ 未开始 | |
| Step 6 ~ Step 9 | ⬜ 未开始 | |

### 实施中的偏离记录

- **Step 2 拆成 2a/2b**:先加 supervisor 节点但不改路由,用话术集单独验证分类质量,再换图。好处是分类回归失败时不必回滚图结构。
- **不在 Step 2 建 `agents/base.py`**:当时只有一个回复型节点,抽公共 prompt 是过度设计;等 Step 3 有了 retriever 这第二个消费者再抽。
- **`agents/budget.py` 提前到 Step 2a**:chitchat 要用 `low_block`,而 chitchat 被图引用,不能再反向 import 入口 `chat.py`,否则循环依赖。所以预算模块必须先独立;Step 4 只剩「接分支 + 做成独立节点」。

### 已发现的既有问题(非本次改造引入,待处理)

- ~~**Milvus 不可用时 `rag/retrieve.py:retrieve()` 空转 10.9 秒**~~ → **Step 3a 已修**(`_BREAKER` 熔断,`RAG_BREAKER_TTL_SECONDS` 默认 60s)。注意 TTL 到期后会再真试一次,所以 Milvus 长期挂掉时,每 60 秒仍会有一轮多等 11 秒;这是刻意的(不通就恢复),不是回归。
- **Redis 挂掉时每轮对话白等约 95 秒**(未处理,优先级高):`chat.py:_load_state`/`_save_state` 每次新建连接,`socket_connect_timeout=2` 只约束建立连接,不约束 redis-py 的重试退避。实测 Redis 停机时 load 47.1s + save 48.4s = 每轮 ~95s,而 LLM 本身只要 1s。这与上面 Milvus 那条同源(依赖不可用时慢重试),同一套熔断/短路思路可解:加 socket_timeout、或连续失败后进"不可用"窗口直接走 `_MEM`。**不属 Step 3 范围,单独排期。**
- **验证环境提示**:probe 的耗时读数只有在 Redis、Milvus 都起来时才有意义;否则量到的是重试退避而不是业务耗时。
- **`estimate_min_total` 冷启动约 26~30 秒**(既有行为,Step 4 暴露出来):模型对这条估算 prompt 会先输出一大段看不见的推理,再吐 18 个字符的 JSON(实测 25.7s 出 `{"min_total":1800}`)。按路线缓存 6h,所以**同一路线只慢第一次**,之后 0.00s。Step 4 之后 budget 路由在「回答够不够」时就会触发这个冷启动,比改造前(只在确认护栏时触发)更容易被用户撞上。可选修法:估算结果落 Redis 跨进程复用 / 换更快的估算方式 / 接受 6h 一次。**属设计取舍,留给用户定。**

---

## 1. 为什么要改(现状问题)

现在 `app/chat.py` 的图只有两个节点,`_respond_node` 一个函数里塞了五件事:

| 现状代码 | 混在一起的职责 |
|---|---|
| `chat.py:91` `_extract_node` | 参数抽取(LLM) |
| `chat.py:171` `_respond_node` | RAG 检索 + 预算拦截 + 追问决策 + 回复生成 |
| `chat.py:336` `_estimate_min_total` | 预算估算(LLM),被 respond 内联调用 |
| `chat.py:384` `_generate_from_params` | 行程生成,挂在 handle_turn 的 confirm 分支上,不在图里 |

问题:① 想加一个新能力(比如查天气)只能继续往 respond 里塞 if;② 预算/检索/生成 无法单独测试和调优;③ 生成的行程不回流到图里,没法做「评审」和「改行程」。

## 2. 目标架构

```
                          ┌──────────────────────────────┐
  用户消息 / confirm 按钮 →│  supervisor(路由 + 抽取合一)  │
                          │  一次 LLM 输出 {intent, params}│
                          └───────────────┬──────────────┘
                                          │ 条件边(ROUTES)
     ┌──────────┬───────────┬─────────────┼────────────┬──────────┬──────────┐
     ▼          ▼           ▼             ▼            ▼          ▼          ▼
 chitchat   retriever    weather       budget      planner    reviser   (collect)
  闲聊/追问   攻略检索      天气          预算评估     行程规划     改行程     信息不全
     │          │           │             │            │          │          │
     │          │           │             │            ▼          ▼          │
     │          │           │             │        ┌──────────────────┐      │
     │          │           │             │        │  critic 评审      │      │
     │          │           │             │        │ 规则校验(0 次 LLM)│      │
     │          │           │             │        └────────┬─────────┘      │
     │          │           │             │          pass ↙   ↘ fail         │
     │          │           │             │        END   reviser → critic    │
     └──────────┴───────────┴─────────────┴───────────────────┴──────────────┘
                                          ▼
                                    统一回复节点(共用 prompt 工具)
```

**专家职责**(对齐 `表格.csv`):

| Agent | 职责 | 现状对应 | 类型 |
|---|---|---|---|
| supervisor | 判意图 + 抽参数(合一) | `_extract_node` 扩展 | 新增 |
| chitchat | 闲聊 / 信息不全时追问 | `_respond_node` 主体 | 迁移 |
| retriever | 攻略检索(RAG) | `rag/retrieve.py` 包装成工具 | 迁移 |
| weather | 实时天气 | **新接** Java `AmapWeatherService` | 新增 |
| budget | 预算评估 / 预算护栏 | `_estimate_min_total` + `_low_block` | 迁移 |
| planner | 逐日行程生成 | `llm.generate_trip_plan` | 迁移 |
| critic | 评审挑错 | — | 新增 |
| reviser | 生成后局部修改 | — | 新增 |

## 3. 关键设计决策(本期定死)

| 编号 | 决策 | 理由 |
|---|---|---|
| D1 | **Supervisor 与参数抽取合并为一次 LLM 调用**,输出 `{intent, params, insist_low_budget}` | 每轮仍是 1 次 LLM,不增加对话延迟和成本 |
| D2 | **`action=confirm` 不走 LLM 路由**,直接进 planner 分支 | 保住前端「确认行程」按钮语义与 8 分钟超时预算;也避免多花一次钱 |
| D3 | **天气 Agent 走 Python → Java 内部接口**(`/internal/weather` + `X-AI-Service-Key`) | 天气数据源归 Java(高德 key 在 Java),Python 只做消费;仅在该 Agent 被路由到时才外呼 |
| D4 | **改行程落成一条新行程**(复用 `TripService.createFromPlan`) | Java 零改动;旧版本仍在历史里可查,与「历史记录」语义一致 |
| D5 | **Critic 以确定性规则为主**(天数/city/预算/饮食/节奏),LLM 复核默认关闭 | 便宜、可测、可复现;先解决 80% 的硬伤 |
| D6 | **Reviser 输出完整 TripPlan**,复用 `_normalize_plan` 校验,最多 1 轮 | 返回 patch 更难校验;失败则保留原 plan 并说明,不硬撑 |
| D7 | **不用 `llm.with_structured_output`**,沿用现有「要 JSON + `_extract_json_object` 抠」 | 兼容中转渠道(部分渠道不支持 json_schema);现有代码已验证可行 |
| D8 | **任一专家失败必须降级**,绝不 500:supervisor 失败 → collect;weather 失败 → 正常聊天不提天气;critic 失败 → 当作 pass | 沿用 `chat.py` 现有“不让对话断掉”的风格 |
| D9 | **`/chat` 响应字段向后兼容**,只新增可选 `intent` | Java `ChatAiClient.java:58` 按名取字段,多余字段无影响;前端本期零改动 |

## 4. 状态字段(ChatState 扩展)

保留现有全部字段,新增 5 个:

| 新字段 | 类型 | 作用 |
|---|---|---|
| `intent` | str | 本轮路由结果,用于调试 / 可观测 / 前端展示 |
| `plan` | dict \| None | 最近一次生成的 TripPlan,Reviser 的输入 |
| `critique` | dict \| None | Critic 结果 `{pass: bool, issues: [str]}` |
| `revision_round` | int | 修订环计数,防死循环(上限 1) |
| `agent_trace` | list[str] | 本轮走过的专家顺序,调试用 |

另外 `weather` 字段(Step 5 加):缓存本轮查到/上轮查过的预报,供 Planner 注入。

## 5. 目标目录结构

```
ai-service/app/
├── main.py                   # FastAPI 入口(不变)
├── config.py                 # + JAVA_BASE_URL / AI_SERVICE_KEY / CRITIC_* 开关
├── llm.py                    # 生成逻辑保留,planner 复用
├── chat.py                   # 对外入口 handle_turn + Redis 状态存取 + confirm 路径
├── graph/
│   ├── state.py              # ChatState
│   ├── params.py             # 参数工具(日期/人数/预算口径/缺失判断)  ← 提前拆,避免循环 import
│   └── builder.py            # build_graph() + ROUTES 路由表
├── agents/
│   ├── base.py               # 共用回复 prompt 与 compose_reply()
│   ├── supervisor.py         # 路由 + 抽取
│   ├── chitchat.py           # 闲聊 / 追问
│   ├── retriever.py          # 攻略检索
│   ├── weather.py            # 天气
│   ├── budget.py             # 预算评估 / 护栏
│   ├── planner.py            # 行程规划
│   ├── critic.py             # 评审
│   └── reviser.py            # 改行程
├── tools/
│   ├── rag_tool.py           # RAG 检索工具(function calling)
│   └── weather_tool.py       # 调 Java /internal/weather
└── scripts/
    └── probe_chat.py         # 验证探针:发一轮对话,打印 intent/status/ready/params
```

## 6. 分步实施计划

> 每步结束时:**服务能跑 + 给出一条可复制的验证命令**。不跑通不进下一步。

### Step 1 · 骨架与状态拆分(纯搬运,行为零变化)
- 新建 `app/graph/__init__.py`、`app/graph/state.py`(ChatState + 5 个新字段)
- 新建 `app/graph/params.py`(把 `chat.py` 里 `_to_float/_to_int/_to_date/_missing_params/_is_ready/_resolved_days/_resolved_travelers/_budget_total_of/_route_sig` 原样搬过来)
- 改 `app/chat.py`:删掉这些函数,改成 `from app.graph.params import ...`;`ChatState` 改从 `app/graph/state.py` 导入
- 验证:`python -c "from app.chat import handle_turn"` 无报错;起服务,闲聊一轮,`status` / `ready` / `params` 与改造前一致
- 风险:循环 import(chat → supervisor 尚未存在,暂无;params.py 独立无依赖,安全)

### Step 2 · Supervisor 路由 + 闲聊分支(最小可用图)
- 新建 `app/agents/base.py`(`compose_reply`)、`app/agents/supervisor.py`(单次 LLM 出 `{intent, params, insist_low_budget}`)
- 新建 `app/agents/chitchat.py`(`_respond_node` 主体搬过来,保留 RAG 注入 + 预算提示话术)
- 新建 `app/graph/builder.py`:`START → supervisor → 条件边`,本期只接 `chitchat`(其余 intent 全部回落到 chitchat)
- 新建 `app/scripts/probe_chat.py` 验证探针
- 改 `app/chat.py`:`_GRAPH` 改为 `from app.graph.builder import GRAPH`;`_extract_node`/`_respond_node` 删除
- 验证:`probe_chat.py` 说「你好」→ `intent=chitchat`;说「从北京去大理玩5天」→ `status=await_confirm`;点 confirm → `status=generated`。**与改造前行为完全一致**
- 说明:此步是「换个壳」,风险最高的一段改动集中在这里,做完先停一次,确认无回归再往下

### Step 3 · Retriever 专家(RAG 工具化)✅ 已拆成 3a / 3b 完成
- 新建 `app/tools/rag_tool.py`:把 `rag/retrieve.py` 的 `retrieve` 包成 `@tool`
- 新建 `app/agents/retriever.py`:调工具取攻略 → 组织回复
- 改 `app/graph/builder.py`:接上 `guide` 分支
- 验证:说「大理有什么好吃的」→ 回复里出现指南里的真实店名/菜品,且 `probe` 打印 `intent=guide`

**3a 实际做法(比原计划多的两处)**:
- **做成两个工具而不是一个**:`search_guide`(Milvus 语义检索,答具体问题)+ `get_city_guide`(MySQL 整篇城市指南,答宽泛问题)。实测 MySQL 是通的、`format_guide_by_city` 0.12s 就能拿到 768 字真指南,所以 Milvus 挂着时 retriever 依然答得出东西 —— 两个工具互为兜底,不是重复。
- **`search_guide` 里加了熔断**(原计划只写"包成 @tool"):`_BREAKER` + `RAG_BREAKER_TTL_SECONDS`。实测 Milvus 挂时第一次 11.04s、第二次起 0.00s。
- 工具自己吞异常返回「（没有检索到相关资料）」而不是抛错 —— 模型据此换 `get_city_guide` 再试,链路不断。

**3b 实际做法**:
- 建 `app/agents/base.py`:抽 `trace` / `param_status_text` / `ready_status` / `history_messages` / `with_reply`。**此时才有第二个消费者(chitchat + retriever),符合"出现重复再抽"的约定**(Step 2b 时故意没抽)。
- `agents/chitchat.py` 改为复用 `base.*`,自身只留 chitchat 专属 prompt 与预算拦截分支。
- **没做的一件事**:`retriever` 没有复用 `base.history_messages`,而是自己拼 SystemMessage + `base.history_messages`;这是同一份实现,没有分叉。
- 验证结果:`guide` 两问均 `trace: supervisor→retriever` 且回复带真实菜品(酸辣鱼/乳扇/砂锅米线/喜洲粑粑/凉鸡米线),并主动声明"哪家店、价格、营业时间没有可靠资料就不瞎推荐";话术集 **15/15**;闲聊、参数齐、预算过低拦截(含「就按最省的吧」→ `await_confirm`)三条路径均无回归。

### Step 4 · Budget 专家(预算独立成节点)✅ 已完成
- 新建 `app/agents/budget.py`:`_estimate_min_total` / `_low_block` 从 `chat.py` 迁入,保持缓存与口径不变
- 改 `app/chat.py`:confirm 分支改为调用 `agents.budget.low_block`
- 改 `app/graph/builder.py`:接上 `budget` 分支
- 验证:说「我一共就 1500 块,够去大理 5 天吗」→ `intent=budget`,回复给出最低花费估算;现有「确认被按灰」的预算护栏仍生效

**实际做法与计划的两处差异**:
- `budget.py` 在 Step 2a 已建(为断开循环依赖),本步只**加节点**,没有"迁入"动作。
- **多抽了一个 `block_state()`**:两个节点(chitchat / budget)现在都要做"按住确认"这件事,而同一句话走不同路由必须给出同一个 `min_budget`。原来 `min_budget = round(block["min_total"])` 写在 chitchat 里,现在两处共用一份,数字只在一处 round。`chat.py` 的 confirm 护栏仍用更底层的 `low_block`(它只要 boolean + 文案,不需要状态字段)。
- 关键信息不全时(如只说了"大理 5 天 1500 块"没说出发地)路由到 budget 也能安全应答:节点提示模型"先问清楚,别给数字",实测回复确实只要出发地/人数、没编数字。

**验证结果**:
- `bud-1`「我一共就 1500 块,够去大理 5 天吗」→ `intent=budget`,`trace: supervisor→budget`,反问出发地与人数(不编数字)
- `bud-3`「那我 3000 块够吗」(已补北京)→ `intent=budget`,"还是不够,差大概 1500",并保留「就按最省的吧」的口子
- `bud-ok`「上海出发去桂林 6 天,预算 9000 够吗」→ `intent=budget`,`status=await_confirm`、`ready=true`,引用估算 8400 对比预算
- **口径一致**:`bud-2`「我们从北京出发」被 supervisor 判成 `collect` 走了 chitchat,但 chitchat 的护栏给出 `min_budget=4500`,与 budget 路由给的值完全相同
- 无回归:预算充足(`reg-a`,8000)仍是 `await_confirm` 不被误拦;攻略路由(`reg-b`)仍 `supervisor→retriever` 且带真实菜品

### Step 5 · Weather 专家(唯一跨服务改动)🔶 已拆成 5a / 5b

**5a · Java 内部天气接口 ✅ 已完成**
- 后端新建 `InternalWeatherController`(`GET /internal/weather?city=`,校验 `X-AI-Service-Key`,不要求登录)
- 后端改 `application.properties`:`app.ai.service-key=${AI_SERVICE_KEY:zhilv-internal-dev-key}`
- 注意:`/internal/**` 不在 `/api/**` 下,`SecurityConfig` 的 `anyRequest().permitAll()` 已放行,鉴权在 Controller 内做

实际做法与验证:
- **没动 `SecurityConfig`**:`/internal/weather` 落进 `anyRequest().permitAll()`,校验改由 Controller 自己做(放行≠不鉴权,只是换鉴权方式)。已在 Controller 注释里写明。
- **复用了现有的 `AmapWeatherService`**:它已经能"城市名 → adcode → 逐日预报",内部接口只是薄薄一层转发 + 换鉴权,没重写高德调用。
- **共享密钥给了开发默认值**(与 `app.jwt.secret` 同款):本地零配置可跑,生产必须用 `AI_SERVICE_KEY` 覆盖。Python 侧将用同名默认值,两边不配也能对上。
- 验证(后端带真实 `AMAP_API_KEY` 启动,key 只作进程环境变量,未落任何文件):

| 用例 | 结果 |
|---|---|
| 不带 `X-AI-Service-Key` | 401 `内部接口校验失败` |
| key 不对 | 401 `内部接口校验失败` |
| key 正确 `?city=大理` | 200,真实预报:大理市/云南/532901,4 天(小雨→多云) |
| key 正确但不给 city | 400 `城市不能为空` |
| 原有 `/api/weather/forecast` | 仍 401 要登录(无回归) |

- **顺带发现(既有行为,非本次引入)**:高德地理编码对不存在的地名不报错,而是匹配到别处(实测 `???xyz` 返回了「兴庆区/宁夏」)。即目的地是编造的地名时,天气会静默串到别的城市。weather Agent 的 prompt 里要提醒"资料与目的地不符就别报"。

**5b · Python 侧 Weather 专家 ⬜ 未开始**
- 新建 `app/tools/weather_tool.py`(调 Java)、`app/agents/weather.py`;查到的预报写进 `state["weather"]` 缓存
- 改 `app/graph/builder.py`:接上 `weather` 分支;`app/config.py` 加 `JAVA_BASE_URL` / `AI_SERVICE_KEY`
- 验证:说「大理明天天气怎么样」→ `intent=weather`,回复带真实预报;把 Java 停掉再问 → 回复降级为「暂时查不到天气」,**不报错**

### Step 6 · Planner 专家 + 生成回流到图
- 新建 `app/agents/planner.py`:包 `generate_trip_plan`,产出写进 `state["plan"]`(Reviser 后续要用)
- 改 `app/graph/builder.py`:接上 `plan` 分支;confirm 路径也进图
- 改 `app/chat.py`:confirm 分支改为「跑图 → 取 `state["plan"]`」
- 验证:对话信息齐后说「帮我生成行程」→ 直接 `status=generated`(不再必须点按钮);点按钮仍能生成
- 收益:生成的行程第一次进入会话状态,才可能做 Step 7/8

### Step 7 · Critic + 修订环
- 新建 `app/agents/critic.py`(规则校验:天数、每天 city 非省级、总花费 vs 预算 ±10%、各天 hotel 之和 vs `budget_breakdown.hotel` ±20%、饮食偏好是否落进 `meals.notes`、节奏与每天景点数匹配) + `app/agents/reviser.py`(把 `issues` 回灌给模型重排,最多 1 轮)
- 改 `app/graph/builder.py`:`planner → critic →(pass)END /(fail)reviser → critic`,用 `revision_round` 封顶
- 验证:故意给一个「预算 800 去大理 5 天」的请求,`probe` 打印 `agent_trace=planner→critic→reviser→critic`,最终 plan 的日均花费明显下降;正常请求 `agent_trace=planner→critic` 且不触发 Reviser

### Step 8 · Reviser 专家(用户主动改行程)
- 改 `app/agents/reviser.py`:支持「用户主动改」入口(读 `state["plan"]` + 用户指令),与 Step 7 的「按 issues 修」共用同一个模型调用
- 改 `app/graph/builder.py` + `app/agents/supervisor.py`:接上 `revise` 分支,并在 supervisor 加守卫——`state["plan"]` 为空时把 `revise` 降级为 `chitchat`(回「先把行程生成出来我才能改」)
- 验证:生成完行程后接着说「第 2 天别安排户外,换成室内的」→ `intent=revise`,`status=generated`,Java 落成**一条新行程**(旧的那条仍在历史里)

### Step 9 · 收尾
- 天气影响安排:Planner 的 prompt 里,若 `state["weather"]` 有预报,按天注入(雨天提示室内、高温提示避开正午)
- `docs/ARCHITECTURE.md` 第 4 节目录结构同步为本方案;本文件标记完成情况
- 可选:前端展示 `intent`(气泡小标签「天气专家」),或 Java `ChatTurnResponse` 加 `intent` 字段
- 回归:表单式生成链路(`/generate`)**全程未被触碰**,确认一次

## 7. Java / 前端改动清单(汇总)

| 位置 | 改动 | 步骤 |
|---|---|---|
| `InternalWeatherController.java` | 新建,`/internal/weather`,校验 `X-AI-Service-Key` | S5 |
| `application.properties` | 加 `app.ai.service-key` | S5 |
| `ChatTurnResponse.java` | 可选,加 `intent` | S9 |
| `ChatPanel.vue` | 可选,展示专家标签 | S9 |
| 其余 | **无改动**(Reviser 复用 `createFromPlan`) | — |

## 8. 成本与延迟预算

| 场景 | 改造前 | 改造后 |
|---|---|---|
| 闲聊一轮 | 2 次 LLM(抽取 + 回复) | 2 次(路由抽取合一 + 回复),**持平** |
| 查天气 | 不支持 | 2 次 LLM + 1 次高德 |
| 点确认生成 | 1~3 次 LLM(含重试) | 1~3 次 + Critic 规则校验(0 次 LLM),**持平**;若触发修订环 +1 次 |
| 表单式生成 | 1~3 次 | **完全不变** |

## 9. 风险与对策

| 风险 | 对策 |
|---|---|
| Step 2 是本方案最大的一次改动,可能引入回归 | 该步只做「搬家」+ 路由壳,行为要求与改造前逐项对齐;做完先停一次验收 |
| 合并路由与抽取后,prompt 变长,分类可能被抽取任务带偏 | intent 枚举写死 + 在 prompt 里放在最前要求;`probe_chat.py` 用固定话术集回归 |
| Supervisor 误判 `plan`(信息还不齐) | 守卫:`_missing_params` 非空时强制降级 `collect`(代码判,不信模型) |
| Reviser 输出完整 plan 容易超时/截断 | 复用 `_normalize_plan` + 现有重试;失败则保留原 plan 并回一句说明 |
| 修订环死循环 | `revision_round` 上限 1,写死在 builder 的条件边里 |
| 天气 Agent 外呼拖慢对话 | 只在该分支调用;3 秒连接超时 + 失败静默降级 |
| 中转渠道不支持 json_schema | D7:不用 `with_structured_output`,沿用抠 JSON 的既有做法 |

## 10. 不在本期范围

- SSE 流式(D25 的独立任务,与多 Agent 解耦)
- LangGraph checkpointer(D27;现在仍是 native JSON 存 Redis,够用)
- 专家级别的独立模型/独立温度配置(等有实测收益再说)
- 并行 fan-out(如 Retriever + Weather 同时跑)——收益不足以抵消复杂度
