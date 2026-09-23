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
| Step 5b Weather 专家 | ✅ 已完成 (2026-09-23) | `tools/weather_tool.py` + `agents/weather.py`;工具循环提到 `base.tool_loop`。**话术集 15/15,回复带真实预报且日期算对(今天/明天/后天)** |
| 插队:Redis 可靠性修复 | ✅ 已完成 (2026-09-23) | 见下方"既有问题"第 2 条。Redis 挂时每轮 95s → ~2s,且停机期间对话不再丢 |
| Step 6 Planner 专家 | ✅ 已完成 (2026-09-23) | `agents/planner.py`(生成逻辑从 chat.py 上移)+ 接上 `plan` 分支;confirm 路径改为直接调 planner 节点。**话术集 15/15,两条生成入口的字段与话术完全一致** |
| Step 7 Critic + 修订环 | ✅ 已完成 (2026-09-23) | `agents/critic.py`(8 条纯规则)+ `agents/reviser.py`(首轮生成复用同一链路,只多传 feedback)。**正常请求 `planner→critic` 不触发修订;低预算请求 `planner→critic→reviser→critic`** |
| Step 8 Reviser 主动改行程 | ✅ 已完成 (2026-09-23) | `revise` 分支接上;reviser 一个节点吃两种触发(critic 的 issues / 用户指令),靠 `intent` 区分。「没行程就想改」的守卫从 supervisor 挪到 reviser |
| Step 9 收尾 | ⬜ 未开始 | |

### 实施中的偏离记录

- **Step 2 拆成 2a/2b**:先加 supervisor 节点但不改路由,用话术集单独验证分类质量,再换图。好处是分类回归失败时不必回滚图结构。
- **不在 Step 2 建 `agents/base.py`**:当时只有一个回复型节点,抽公共 prompt 是过度设计;等 Step 3 有了 retriever 这第二个消费者再抽。
- **`agents/budget.py` 提前到 Step 2a**:chitchat 要用 `low_block`,而 chitchat 被图引用,不能再反向 import 入口 `chat.py`,否则循环依赖。所以预算模块必须先独立;Step 4 只剩「接分支 + 做成独立节点」。
- **Step 5b 从「直接查 params.destination」改成 function calling**:实测 supervisor 对天气问句的目的地抽取不稳(「大理明天天气怎么样」4 次里 1 次抽不到 → 节点不知道该查哪个城市,只能回「查不到」)。改由模型读对话定城市后,构造「params 为空 + 话里有城市名」的用例连测 3 次全部答对。代价是多一轮 LLM(~1.5s),换来的是抽取抖动不再影响可用性。
- **`base.tool_loop` 提到公共处**:retriever 和 weather 各要一份工具循环(第二个消费者出现),所以按既有约定上移;retriever 自身删掉本地循环,行为不变(tw-3 复测仍带真实菜品)。
- **Step 8 把「没行程就想改」的守卫从 supervisor 挪到 reviser**:原计划写在 supervisor。但 supervisor 是路由、不产出话术,它只能把 `revise` 降级成 `chitchat`,而 chitchat 会顺着用户的话答「好的,第 2 天全安排室内」——**像是答应了改一份不存在的行程**。守卫的目的本来就是"回一句正确的话",所以该放在会说话的那个节点里。
- **Step 7 新增 `GENERATE_GRAPH`(生成专用图)**:Step 6 让 confirm 直接调 `planner_node`,Step 7 一加 critic 就暴露了问题 —— **点按钮绕开 supervisor 的同时把质检也绕开了**,同一个请求会因入口不同产出不同质量的行程。改法是再加一张只含 `planner→critic→reviser` 的图,和主图**共用节点函数与 `should_revise` 判断**,重复的只有 4 行接线、没有重复的逻辑。(没选"让 supervisor 对空消息放行"那种写法:那等于让路由器在一个分支上说谎。)
- **Step 6 的 confirm 路径不进图**:原计划写的是"confirm 路径也进图",实现时改成直接调 `planner_node`。理由:点按钮没有新消息,supervisor 对空消息会判成 `collect`、把 `status` 打回 `collecting`,confirm 就废了。走同一份节点代码,行为一致,还省一次 LLM 分类调用。
- **Step 6 把护栏从 chat.py 搬进 `planner_node`**:参数齐否、预算过低这两道判断原来只在 chat.py 的 confirm 分支里。搬进来之后「对话里说生成」和「点按钮」共用一份,不会两边改歪;副作用是**对话路径现在也会被预算护栏拦住**(原计划没提,属预期内的收紧)。
- **Step 5b 没做 `state["weather"]` 缓存**:原计划把预报写进该字段给 planner 复用,但天气改走工具后节点手里没有"这次查的是哪个城市"的确切记录(城市由模型定,可能一次查多个)。与其加一层 last-fetch 全局态,不如让 Step 9 的 planner 直接调 `fetch_forecast(destination)`(实测 0.4s,确定性,不依赖模型)。`ChatState.weather` 字段暂留空,Step 9 再定去留。

### 已发现的既有问题(非本次改造引入,待处理)

- ~~**Milvus 不可用时 `rag/retrieve.py:retrieve()` 空转 10.9 秒**~~ → **Step 3a 已修**(`_BREAKER` 熔断,`RAG_BREAKER_TTL_SECONDS` 默认 60s)。注意 TTL 到期后会再真试一次,所以 Milvus 长期挂掉时,每 60 秒仍会有一轮多等 11 秒;这是刻意的(不通就恢复),不是回归。
- ~~**Redis 挂掉时每轮对话白等约 95 秒**~~ → **已修 (2026-09-23)**。两个独立原因叠加:
  1. **redis-py 8.x 默认带重试退避**:只设 `socket_connect_timeout` 时,连接失败会被重试并逐次拉长等待,实测停机时单次 op 要 27s。加 `retry=None` 后降到 ~1s。
  2. **`localhost` 会先试 IPv6(::1) 再试 IPv4**:两次各等满一个 connect timeout,所以每次 op 的实际代价是"超时 × 2"。默认超时从 2s 降到 `REDIS_SOCKET_TIMEOUT_SECONDS=0.5`。
  合起来:`_load_state`/`_save_state` 各一次读写 → 每轮 ~2s(原 ~95s)。client 也改为复用(原来每轮新建连接)。
  顺带修掉一个**测出来的真 bug**:历史只存在 Redis 里,Redis 一挂「读不到 → 当成新会话」,**停机当轮就把对话清空了**(实测第 3 轮反过来问用户刚给过的出发地)。现加进程内镜像 `_STATE` + 脏标记 `_DIRTY`:写 Redis 失败就标脏,读时优先本地,Redis 恢复后下一轮自动写回并清标记。端到端复测:停机前 2 轮正常 → 停机后第 3/4 轮对话继续、params 不丢 → Redis 恢复后 `zhilv:chat:e2e-x` 里 10 条消息 + 完整 params 全在,回同步成功。
- **话术集命中率本身是抖的(12~15/15),别把单次 15/15 当成回归基线**:Step 7 改完复测,同代码连跑三次得到 15→14→13→12 中不同的组合,**每次挂的话术都不一样**。原因在 `supervisor_node` 那次 LLM 分类(`temperature=0.3`),不在路由代码 —— 已用 git 确认 `supervisor.py` / `graph/params.py` 在 Step 6/7 全程未被改动。
  最常挂的两条是「就按最省的安排吧」「帮我生成行程吧」(在没有任何参数时)。注意 `_apply_guards` 会把"没有行程时的 `revise`"降级成 `chitchat`,所以模型把「按最省的安排」读成"改行程"时会落到 chitchat,而 probe 期望 `collect` —— 这条期望值本身也偏严。
  想稳住的话有两条路(都未做,留用户定):给 supervisor 单独降到 `temperature=0`;或把 probe 的话术期望改宽(plan/revise/collect 在无参数时都算过)。
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

**5b · Python 侧 Weather 专家 ✅ 已完成**
- 新建 `app/tools/weather_tool.py`(调 Java)、`app/agents/weather.py`
- 改 `app/graph/builder.py`:接上 `weather` 分支;`app/config.py` 加 `JAVA_BASE_URL` / `AI_SERVICE_KEY`
- 验证:说「大理明天天气怎么样」→ `intent=weather`,回复带真实预报;把 Java 停掉再问 → 回复降级为「暂时查不到天气」,**不报错**

实际做法:
- **没做 `state["weather"]` 缓存**(理由见上面偏离记录),`chat.py` 未改。
- `fetch_forecast()` 用标准库 `urllib`(不引新依赖),401/400/502/超时/Java 没起全在一个 `except` 里返回 `None`。
- 预报文本里给「今天」那条打上 `(今天)` 标记 —— 让模型算"明天/后天"时不依赖它自己的日期直觉。
- 星期的口径核对过:高德 `week` 字段 = ISO 星期(2026-09-23 返回 `3`,Python `isoweekday()` 也是 3),所以直接映射成周一~周日,没有偏移。

验证结果:

| 用例 | 结果 |
|---|---|
| 「大理明天天气怎么样」 | `intent=weather`,5.3s,「明天(9月24日 周四)多云,14~25℃,西南风」,**与预报一致** |
| 「后天会下雨吗」(承接上一轮) | 3.2s,正确算成 9月25日 周五 多云,**未答错日子** |
| params 为空但话里有城市名(模拟抽取失败)×3 | 3/3 都查到并答对 —— 这正是改用 function calling 要解决的问题 |
| Java 停机 | 6.8s,「暂时查不到大理的天气数据…建议打开天气 App」,**无异常、status 正常** |
| 攻略路由(回归) | 仍 `supervisor→retriever`,回复带真实菜品 |
| 话术集 | **15/15** |

- 耗时参考(Redis 正常时):weather ~3~5s、retriever ~3~4s、chitchat ~1.6s、budget 冷启动 ~25s(估算缓存)。

### Step 6 · Planner 专家 + 生成回流到图 ✅ 已完成 (2026-09-23)

原计划:
- 新建 `app/agents/planner.py`:包 `generate_trip_plan`,产出写进 `state["plan"]`(Reviser 后续要用)
- 改 `app/graph/builder.py`:接上 `plan` 分支;confirm 路径也进图
- 改 `app/chat.py`:confirm 分支改为「跑图 → 取 `state["plan"]`」

实际做法:
- **`_generate_from_params` / `_gen_rag_context` 从 `chat.py` 上移到 `agents/planner.py`**(仍为模块私有)。和 Step 2a 挪 `budget.py` 同一个理由:planner 节点要被 `graph/builder.py` 引用,而 `chat.py` 引用 builder —— 生成逻辑留在 chat 里就会循环 import。**这也是本项目第二次用「第二个消费者出现才上移」这条惯例。**
- **护栏(参数齐否 + 预算过低)从 chat.py 的 confirm 分支搬进 `planner_node`**:两条入口共用一份判断,不再有两处可能改歪。chat.py 的 confirm 分支只剩"调节点 → 组装响应 → 写回状态"。
- **confirm 没进图,而是直接调 `planner_node`**(偏离原计划"跑图"),原因:点按钮时没有新消息可喂 supervisor,让它对空消息分类会把 `intent` 判成 collect、把 `status` 打回 collecting,confirm 直接失效。走同一个节点函数反而更稳,`agent_trace=['planner']` 也如实反映"只过了 planner"。
- **`build_graph` 的 `plan` 分支只挂 `planner → END`**:Step 7 会在中间插 critic,现在不做预留。
- **顺手补的两个 bug**(验证时暴露):
  1. 图的 `plan` 分支跑通后,`handle_turn` 的返回里**没带 `plan` 字段** —— 只有 confirm 分支带了。表现是 `status=generated` 但前端拿不到行程。已补。
  2. `state["plan"]` **没进 Redis**(两处 `_save_state` 都只写 messages/params/insisted_sig)。这样下一轮 reviser 手里没有行程,Step 8 会直接做不成。已在两处写入 `plan`,并复测 Redis 里确实有。

验证结果:

| 用例 | 结果 |
|---|---|
| 对话信息齐后说「帮我生成行程」 | `intent=plan`、`agent_trace=['supervisor','planner']`、`status=generated`,plan 标题「上海出发·大理苍山洱海5日舒适之旅」,days=5 |
| 点「确认行程」按钮(无消息) | `agent_trace=['planner']`、`status=generated`,46.1s;**与对话路径的 reply 文案、返回字段逐项一致** |
| 信息不全时点确认 | **0.0s**、`status=collecting`、回复「还缺关键信息…还差:出发地、目的地、出行时间」,**未调 LLM** |
| 预算过低时走「帮我生成行程」 | 1.2s、`status=budget_low`、`min_budget=4200`,**与点确认的拦截口径一致**(原来只有 confirm 会拦) |
| 接受「就按最省的吧」后再生成 | 护栏放行 → `status=generated`;随后点确认 **0.1s**(命中 LLM 结果缓存) |
| `state["plan"]` 落 Redis | ✅ `zhilv:chat:s6-b` 的 state keys = `insisted_sig/messages/params/plan`,plan 4 天完整 |
| 话术集(回归) | **15/15**,「帮我生成行程吧」在参数不全时正确回落 collect→chitchat |

- 耗时参考:planner 生成一轮 46~71s(生成 5 天行程本身就要这么多,Redis/图编排只占 ~0.1s);confirm 命中缓存时 0.1s。

### Step 7 · Critic + 修订环 ✅ 已完成 (2026-09-23)

原计划:
- 新建 `app/agents/critic.py`(规则校验:天数、每天 city 非省级、总花费 vs 预算 ±10%、各天 hotel 之和 vs `budget_breakdown.hotel` ±20%、饮食偏好是否落进 `meals.notes`、节奏与每天景点数匹配) + `app/agents/reviser.py`(把 `issues` 回灌给模型重排,最多 1 轮)
- 改 `app/graph/builder.py`:`planner → critic →(pass)END /(fail)reviser → critic`,用 `revision_round` 封顶

实际做法(critic 是**纯规则、不调模型**;reviser 复用首轮那条生成链路):
- **"总花费 vs 预算 ±10%"这条按原样写会永远不触发**:实测模型会把 `estimated_budget` 直接写成和 `budget` 一模一样(预算 600 → 预估也写 600)、`budget_breakdown` 四项之和也凑成 600。改成两条能真正触发的:
  - **总花费 vs 路线最低估算**(复用 `budget.estimate_min_total`,护栏那步已算过并缓存 6h,这里通常 0 秒):低于最低估算的 80% 判"这个价钱排不出能走的行程"。
  - **总花费 vs 预算 +10%**:模型无视预算硬排高档行程时抓它。
  - 两条**互斥**:用户预算本身就低于最低估算时(600 元玩大理 5 天),模型只有"编低价"和"照现实写"两条路,后者不该被骂 —— 所以那种情况只保留"花太少"那条,否则两条相反的意见会把模型来回拉扯,改出来更差。
- **reviser 从 `params` 重建 TripRequest,不改手里的 plan**:`hotel_level` 和 `dietary_preferences` 不在 TripPlan 契约里,从 plan 反推会丢,而丢的正好是 critic 要审的两项。为此把 planner 里的请求构建提成公开的 `planner.build_request`(第三个消费者:planner / critic 的对照 / reviser)。
- **reviser 没另写 prompt**:`llm.generate_trip_plan` 里本来就有"上次未通过校验"那段(原本给 JSON 解析失败重试用),新加一个 `feedback` 参数灌 issues 就够,字段口径和初版天然一致。**`feedback` 必须进缓存 key**,否则"按质检意见重排"会命中原始那版缓存、原样返回没改过的行程。
- **planner 的三条"没生成"出口(参数不全/预算护栏/生成失败)显式写 `plan: None`**:否则上一轮的旧行程会留给 critic 去审,用户这轮只是补参数,却可能触发一次莫名其妙的"重排"。旧行程在 Redis 里仍在(chat 写回用 `out["plan"] or state["plan"]`)。
- **新增 `GENERATE_GRAPH`(见偏离记录)**:点「确认行程」也要过 critic,不能因为绕开 supervisor 就连质检一起绕开。

验证结果:

| 用例 | 结果 |
|---|---|
| 正常请求(8000 元/大理 5 天/2 人)对话生成 | `agent_trace=['supervisor','planner','critic']`,**未触发 reviser** |
| 正常请求点「确认行程」 | `['planner','critic']` —— 确认路径现在也有质检(改之前只有 planner) |
| 低预算(600 元/大理 5 天/3 人)对话生成 | **`['supervisor','planner','critic','reviser','critic']`** ← 文档要的那条,152.8s |
| 修订后的 plan | 由"凑成 600 的假行程"变成 8430 元的现实行程,tips 明写「600元预算远不足以覆盖上海—大理往返大交通和5晚舒适型住宿,建议至少准备约8400元/3人」——正是 feedback 里要求的"如实排 + 说明够不够" |
| 规则单元测试 | 省级 city / 排 7 个景点 / 某天 0 景点 / 住宿明细对不上 / day_index 不连续 / 饮食偏好没落地 —— 6 种注入缺陷全部报出;正常 plan 无 issue |
| 饮食偏好规则 | 修掉一个自造 bug:`不吃辣` 剥掉前缀得到单字「辣」,被 `len(t)>=2` 过滤掉,导致这条规则永远判"没落地"。现 `不吃辣→{不吃辣,辣}`、`素食→{素食}`,两个方向都对 |
| 修订环封顶 | reviser 自己 +1、`should_revise` 校验上限 1,`reviser→critic` 最多转一圈(上表那条 trace 已证明会停) |

- ⚠️ **与文档预期不同的一点**:文档写的是"最终 plan 的日均花费明显下降"。按上面的重构,低预算场景下修订的效果是**花费上升**(从编造的 600 → 现实的 8430),因为"假"的那一版本来就是靠编低价凑出来的。哪种行为更合理请用户定:现在是"宁可真而贵,不假而省钱"。

### Step 8 · Reviser 专家(用户主动改行程) ✅ 已完成 (2026-09-23)

原计划:
- 改 `app/agents/reviser.py`:支持「用户主动改」入口(读 `state["plan"]` + 用户指令),与 Step 7 的「按 issues 修」共用同一个模型调用
- 改 `app/graph/builder.py` + `app/agents/supervisor.py`:接上 `revise` 分支 + 守卫

实际做法:
- **一个节点吃两种触发,靠 `intent` 区分**:`intent=="revise"` 是 supervisor 判出的用户主动改,否则是 critic 下游那条。两条都走 `generate_trip_plan` + `build_request`,只是 feedback 正文不同 —— 不另写 prompt,字段口径与首轮一致。
- **用户主动改时把当前行程 JSON 一起喂进去**,并要求"做最小改动、没被要求改的部分保持原样"。不给的话模型会推倒重来:用户说"第 2 天换室内的",结果 5 天全变样,他前面认可的安排全没了。行程 JSON 过长时退化成文字摘要。
- **`_feedback_for` 之前只管 issues**:Step 7 那条 prompt 的标题写死「上次生成未通过校验」,对"用户主动要求"语义不对(模型会以为自己在修 bug 而不是执行指令),改成中性的「这次必须落实的调整要求」。
- **轮次上限只约束 critic 那圈自动重排**,用户主动改不受 `revision_round` 限制(他改几次是他的事)。

验证结果:

| 用例 | 结果 |
|---|---|
| 生成完说「第 2 天别安排户外,换成室内的」 | `intent=revise`、`['supervisor','reviser','critic']`、`status=generated`;day2 由「洱海生态廊道×2 + 喜洲古镇」换成「大理古城室内街区 + 五华楼」,**day1 原样保留** |
| 再说「第 4 天减到 1 个景点」 | day4 由 3 个景点减到 1 个,其余天不动 —— "最小改动"这个要求在起作用 |
| 还没有行程就要求改 | `intent=revise`、`status=collecting`、3.4s(不生成),回复「我得先有一份行程才能改。你先告诉我『从哪出发、去哪里、什么时候去、玩几天』…」 |
| Java 落成一条新行程 | ⏳ 属全链路测试范围(前端→Java→Python),Step 9 之后统一验 |

- **修掉两个只有这条路径才会暴露的 bug**:
  1. **`status` 被兜底成 `collecting`**:用户主动改这条路是 `supervisor → reviser`,**没有 planner 走过**,而 `status` 一直是 planner 写的 —— 没人写就一路默认成 collecting,前端不会打开行程页。Step 7 那条没暴露是因为上游 planner 已经写过 `generated`,把问题盖住了。现由 reviser 自己写 `status/ready`。
  2. **"没行程就想改"的话术是错的**:守卫按计划放在 supervisor,只能降级成 chitchat,而 chitchat 会顺着用户的话答「好的,第 2 天全安排室内」—— **像是答应了改一份并不存在的行程**。守卫挪进 `reviser_node`,由它回正确的话。

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
