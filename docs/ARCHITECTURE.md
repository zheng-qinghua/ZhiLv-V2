# 智旅云图 复现版 · 架构设计

## 1. 项目愿景

在 1:1 复现源项目「智旅云图」(zhilv-yuntu) 的基础上,融合自研项目「智旅助手」(Agent Param) 的 AI 能力,用新技术栈重写:

- **表单式规划**(源项目原有):填写固定表单生成行程,保持不变。
- **对话式规划**(新增):与 AI Agent 多轮对话生成行程。
- **两种方式互斥**:一次规划只能选其一,防止信息不一致导致行程规划出错。
- **下游统一**:无论哪种方式生成,前端行程展示、保存、历史管理走同一套流程。

## 2. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vue 3 + Vite + TS)              │
│           沿用源项目技术栈 · 新增聊天面板组件                   │
│        规划页:  [表单模式] / [对话模式]  二选一                 │
└───────────────┬───────────────────────────┬─────────────────┘
                │ HTTPS/JWT                 │ HTTPS/JWT
┌───────────────▼───────────────────────────▼─────────────────┐
│              Backend (Spring Boot 4 + Java 17)              │
│   职责: 认证 · 行程 CRUD · 用户 · 编排路由 · 导出 · 天气       │
│   分层: Controller → Service → Repository → MySQL            │
│   ┌──────────────────────────┐                              │
│   │ Redis: 会话状态 · 缓存     │                              │
│   └──────────────────────────┘                              │
└───────────────┬───────────────────────────▲─────────────────┘
                │ REST + SSE(流式)          │
┌───────────────▼───────────────────────────┴─────────────────┐
│            AI Service (Python + LangGraph)                  │
│   职责: 对话 Agent · RAG 检索 · LLM 生成 · 结构化行程输出      │
│   组件: 多轮对话图 · 检索器 · 向量库(Milvus) · 工具调用         │
└─────────────────────────────────────────────────────────────┘
       数据库: MySQL 8 (业务数据)        向量/缓存: Redis
```

## 3. 核心设计决策(不可随意更改)

### 3.1 AI 全归 Python,业务全归 Java

| 归属 | 内容 |
|---|---|
| **Java (Spring Boot)** | 用户认证、行程持久化、历史管理、导出、天气、地图、编排路由、所有不涉及 LLM 的业务 |
| **Python (LangGraph)** | 对话 Agent、意图识别、信息抽取、RAG 检索、LLM 调用、结构化行程生成、工具调用 |
| **Redis** | 聊天会话状态(配合 LangGraph checkpointer)、热点缓存、后续可做任务队列 |
| **MySQL** | 唯一业务数据库,只有 Spring Boot 写库,Python 服务不直接操作业务库 |

**规则:Python 服务只负责"生成"和"对话",不落业务库。** 所有持久化由 Spring Boot 完成,避免两服务写库导致的事务混乱。

### 3.2 统一行程模型(关键中的关键)

两种模式必须产出**完全相同的行程 JSON 结构**,下游才能复用。这个 schema 在 Spring Boot 和 Python 之间共享,是跨服务契约。

```jsonc
// TripPlan —— 统一行程模型
{
  "id": 123,
  "title": "杭州三日游",
  "destination": "杭州",
  "departure": "北京",          // 出发城市(每单必填,与 destination 平行;预算口径含往返大交通)
  "start_date": "2026-09-01",
  "end_date": "2026-09-03",
  "day_count": 3,
  "travelers": 2,
  "budget": 3000,
  "budget_breakdown": { "tickets": 900, "hotel": 1200, "meals": 600, "transport": 300 },
  "estimated_budget": 3000,
  "preferences": ["美食", "文化"],
  "pace": "适中",
  "special_notes": "想看日落",
  "summary": "行程概述",
  "tips": ["提示1", "提示2"],
  "days": [
    {
      "day_index": 1,
      "date": "2026-09-01",
      "theme": "西湖文化一日",
      "city": "杭州",          // 当天主要活动所在城市(模块7 地图按天定位用)
      "spots": [
        {
          "name": "西湖",
          "description": "推荐理由",
          "location": { "lat": 30.24, "lng": 120.15 },
          "duration": "2h",
          "image_url": "...",
          "estimated_cost": 90        // 门票估算(元,免费景点为 0)
        }
      ],
      "meals": [
        { "name": "楼外楼", "notes": "推荐西湖醋鱼", "estimated_cost": 180 }
      ],
      "transport": { "mode": "步行", "note": "...", "estimated_cost": 12 },
      "hotel": { "name": "杭州某某酒店", "level": "舒适型", "estimated_cost": 400 },  // 当晚住宿,旧数据可能没有
      "note": "当天备注"
    }
  ],
  "source": "FORM | CHAT",   // 生成来源
  "created_at": "..."
}
```

**注意**:表单式输入的 `TripRequest`(出发地/目的地/日期/预算/偏好等字段)和最终保存的 `TripPlan`(每日安排)是两种结构。对话式在信息抽齐后,本质是凑齐一份 `TripRequest`,然后走**同一条生成管线**,产出 `TripPlan`。每单必填 `departure`(出发城市),与 `destination` 平行;预算口径为含往返大交通的总预算。

### 3.3 规划入口互斥

- 规划页只允许选择一种模式,一旦进入某模式,另一种不可用。
- 表单模式 → 提交 `TripRequest` → Spring Boot 转发 Python 生成。
- 对话模式 → 多轮对话 → Python Agent 信息抽齐 → 内部调用生成 → 返回 `TripPlan`。
- 两种模式的产物都以 `TripPlan` 进入同一套展示/保存接口。

### 3.4 Spring Boot ↔ Python 通信

- **同步 REST + SSE(Server-Sent Events)**:LLM 生成耗时数秒到数十秒,SSE 让前端流式看到生成过程。
- Spring Boot 通过 HTTP 客户端(WebClient/RestClient)调用 Python 服务,把 SSE 流透传给前端。
- **第一阶段不引入消息队列**,等出现多用户并发排队需求再上 Redis Stream / RabbitMQ。
- 服务发现:第一阶段用固定地址 + 环境变量(`ai.service.url`),不引入注册中心。

### 3.5 会话状态归属

- **多轮对话的会话状态归 Python 侧管理**,用 LangGraph checkpointer + Redis 持久化。
- Spring Boot 只保存"会话与用户的映射"(session_id ↔ user_id)及消息历史落库(用于历史记录页)。
- 避免两边各存一份完整上下文。

## 4. 目录结构

```
智旅云图 复现/
├── claude.md                      # Claude 项目指令(开发规范)
├── docker-compose.yaml            # 本地一键启动所有服务
├── .claude/
│   └── skills/                    # 项目级 Claude skills
├── docs/
│   ├── ARCHITECTURE.md            # 本文档
│   ├── PHASE1_TASKS.md            # 第一期任务清单
│   └── tutorials/                 # 学习教程(Spring Boot / Redis / LangGraph)
├── frontend/                      # Vue 3 + Vite + TS(沿用源项目)
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue           # 规划页(表单/对话切换)
│   │   │   ├── Result.vue         # 行程展示页(复用)
│   │   │   └── History.vue        # 历史记录页(复用)
│   │   ├── components/
│   │   │   ├── planner-form/      # 表单式规划组件
│   │   │   ├── chat-panel/        # 对话式规划组件(新增)
│   │   │   └── trip-card/         # 行程卡片(两种模式共用)
│   │   ├── services/              # API 封装
│   │   └── types/                 # TS 类型(与统一行程模型对齐)
│   └── package.json
├── backend/                       # Spring Boot 4 + Java 17
│   ├── pom.xml
│   └── src/main/java/com/zhilv/
│       ├── ZhilvApplication.java
│       ├── config/                # 安全、Redis、WebClient、CORS 配置
│       ├── controller/            # REST 控制器
│       ├── service/               # 业务逻辑(含 AI 客户端)
│       ├── repository/            # 数据访问层
│       ├── entity/                # JPA 实体(对应 MySQL 表)
│       ├── dto/                   # 请求/响应对象(含 TripPlan)
│       ├── ai/                    # Python AI 服务客户端(SSE 透传)
│       └── common/                # 统一响应体、异常处理、工具
├── ai-service/                    # Python FastAPI + LangGraph
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                # FastAPI 入口(仅作为服务载体)
│   │   ├── graph/                 # LangGraph 图定义(状态、节点、边)
│   │   ├── agents/                # 工具、提示词、Agent 逻辑
│   │   ├── rag/                   # 检索器、向量库、攻略索引
│   │   ├── models/                # 结构化输出 Pydantic 模型
│   │   └── config.py              # LLM API 配置
│   └── tests/
└── scripts/                       # 启动/初始化脚本
```

## 5. 服务职责映射(对照源项目)

源项目后端模块 → 复现版归属:

| 源项目模块 | 复现版归属 | 说明 |
|---|---|---|
| `api/routes/trip.py` | Spring Boot `controller` + `service` | 表单式行程生成编排 |
| `api/routes/export.py` | Spring Boot `service` | 行程导出 |
| `api/routes/weather.py` | Spring Boot `service` | 天气查询 |
| `models/db_models.py` | Spring Boot `entity` + MySQL | 表结构迁移 |
| `services/cache_service.py` | Spring Boot + Redis | 缓存改用 Redis |
| `services/city_resolver_service.py` | Spring Boot `service` | 城市解析(纯业务) |
| `services/map_service.py` | Spring Boot `service` | 地图数据 |
| `services/place_candidate_service.py` | Spring Boot `service` | 景点候选(业务侧) |
| `agents/trip_planner_agent.py` | Python `agents` + `graph` | LLM 行程生成(留在 Python) |
| `rag/*` | Python `rag` | 攻略检索(留在 Python) |
| `agents/tools/rag_tool.py` | Python `agents` | Agent 工具(留在 Python) |

**关键理解**:"替换 FastAPI"实际上是**拆分**:纯业务迁到 Spring Boot,AI 相关留在 Python 并升级为 LangGraph。

## 6. 认证方案

- **Spring Security + JWT**,与源项目/智旅助手的 token 协议兼容(BCrypt 密码哈希)。
- 前端 axios 拦截器携带 `Authorization: Bearer <token>`。
- Redis 可选存 token 黑名单/登录态,第一阶段可只做 JWT 无状态认证。
- 认证只属于 Spring Boot;Python 服务被调用时通过内部 Header(`X-AI-Service-Key`)校验,不暴露给前端。

## 7. 数据流

### 表单式
```
前端表单 → POST /api/trips (TripRequest)
  → Spring Boot 校验/落库草稿
  → POST ai-service /generate (TripRequest)
  → Python 检索 RAG + 调 LLM → 返回 TripPlan(JSON)
  → Spring Boot 落库 TripPlan
  → 返回前端 → Result.vue 渲染
```

### 对话式
```
前端聊天面板 → POST /api/chat (sessionId, message)
  → Spring Boot 转发 ai-service /chat (SSE 流式)
  → Python LangGraph 多轮图:
      收集信息 → 不够则追问 → 抽齐 → 生成 TripPlan → 完成事件
  → SSE 流透传前端,前端流式渲染
  → 生成完成 → 前端跳转 Result.vue(复用)
```

## 8. 统一行程模型 & 前端 TS 类型

`frontend/src/types/trip.ts` 与 `backend dto/TripPlan` 与 `ai-service/models` 三处字段必须保持一致。**改一处,同步另两处。** 建议以本文档第 3.2 节的 JSON 为准。

## 9. 部署

- 本地开发:5 个服务经 `docker-compose.yaml` 编排:frontend、backend、ai-service、redis、mysql。
- 环境变量:LLM API Key(DeepSeek/OpenAI 兼容)、DB 连接、AI 服务地址,统一放 `.env`。
- 第一阶段目标:本地 `docker compose up` 一条命令全部起跑。

## 10. 技术选型速查

| 层 | 选型 | 理由 |
|---|---|---|
| 前端 | Vue 3 + Vite + TS + ant-design-vue | 沿用源项目,不换 |
| 后端 | Spring Boot 4 + Java 17 | 生态成熟、适合业务后端 |
| ORM | Spring Data JPA(或 MyBatis-Plus,二选一,不混用) | 快速开发 |
| 缓存/会话 | Redis (Spring Data Redis) | 会话状态、缓存 |
| AI 编排 | Python + LangGraph + LangChain | 多轮有状态对话的行业标准 |
| 向量检索 | Milvus | 独立向量数据库服务,可扩展;替代源项目 ChromaDB 与智旅助手 FAISS |
| LLM | DeepSeek(OpenAI 兼容) | 沿用两个源项目 |
| 数据库 | MySQL 8 | 沿用源项目 |
| 认证 | Spring Security + JWT | 兼容现有前端 |
| 通信 | REST + SSE | 流式 + 简单 |
