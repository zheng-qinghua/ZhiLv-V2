# CLAUDE.md · 智旅云图 复现版

本项目是「智旅云图」的 1:1 复现版,融合自研项目「智旅助手」的 AI 能力,采用新技术栈。开发前先读 docs/ARCHITECTURE.md 和 docs/PHASE1_TASKS.md。

## 项目定位

- **表单式规划**(沿用源项目):填固定表单生成行程。
- **对话式规划**(新增):与 AI Agent 多轮对话生成行程。
- **两模式互斥**、下游统一:生成/保存/历史走同一套流程。
- 最终产物统一为 **TripPlan**(见 docs/ARCHITECTURE.md 3.2 的 JSON schema)。

## 技术栈与架构(不可偏离)

| 层 | 技术 | 职责 |
|---|---|---|
| `frontend/` | Vue 3 + Vite + TS + ant-design-vue | 沿用源项目技术栈 |
| `backend/` | Spring Boot 4 + Java 17 | **所有业务**。认证、行程 CRUD、导出、天气、编排路由 |
| `ai-service/` | Python FastAPI + LangGraph + LangChain | **所有 AI**。对话 Agent、RAG、LLM 生成、结构化行程输出 |
| Redis | Spring Data Redis | 会话状态(LangGraph checkpointer)、缓存 |
| MySQL 8 | JPA | 唯一业务库,**只有 Spring Boot 写库** |

**硬性规则**:
1. AI 相关逻辑只放 `ai-service/`(Python);Java 不写 LLM/RAG/Agent 代码。
2. Python 服务不直接操作业务库,只做"生成"和"对话",持久化全由 Spring Boot 完成。
3. Spring Boot ↔ Python 用 **REST + SSE** 通信,不引入消息队列(一期)。
4. 会话状态归 Python(LangGraph checkpointer + Redis);Spring Boot 只存 session↔user 映射和历史消息。
5. 认证归 Spring Boot(Spring Security + JWT),Python 用内部 Header 校验。

## 统一行程模型(改字段必须三处同步)

`docs/ARCHITECTURE.md` 第 3.2 节的 TripPlan JSON 是跨服务契约。改它时**同时改**:
- `frontend/src/types/trip.ts`
- `backend/.../dto/TripPlan.java`
- `ai-service/app/models/*.py`

三处不一致视为 bug。

## 目录速览

```
docs/           架构 + 任务清单 + 学习教程(Spring Boot/Redis/LangGraph)
frontend/       Vue 3 前端(views: Home 规划页 / Result 展示 / History 历史)
backend/        Spring Boot(controller/service/repository/entity/dto/ai/common)
ai-service/     FastAPI + LangGraph(graph/agents/rag/models)
.claude/skills/ 项目级 skills(full-output-enforcement 等)
```

参考源:`C:\Users\20243\Desktop\智旅云图 源项目\zhilv-yuntu`(被复现对象)、`C:\Users\20243\Desktop\Agent Param`(智旅助手,AI 逻辑参考)。

## 常用命令

```bash
# 后端
cd backend && ./mvnw spring-boot:run
# 前端
cd frontend && npm run dev
# AI 服务
cd ai-service && uvicorn app.main:app --reload --port 8100
# 一键起全部
docker compose up
```

## 开发规范

- 后端分层:Controller → Service → Repository,禁止跳过层直接操作 DAO。
- 统一返回 `ApiResponse`,异常用全局 `@RestControllerAdvice`,不裸抛。
- 配置外置到环境变量,本地用 `application-dev.yml`。
- 前端 API 调用封装在 `src/services/`,不散落各处。
- Python:结构化输出一律用 Pydantic 模型,禁止裸返回 dict。
- 代码只写必要注释(为什么),不写过程注释;不造不必要的抽象。

## 学习状态(用户)

用户正在**边做边学** Spring Boot 和 Redis(零基础),LangGraph 有 Python/LangChain 基础。解释技术点时用"从入门到能用"的分寸,讲清原理但深入源码;涉及用户不会的知识点,先给最短必要概念,再落到代码。

## 开发节奏

- **四周冲刺计划**是当前主推进路线(见 docs/FOUR_WEEK_PLAN.md):28 天逐日任务,每次给 Claude 的任务 ≤2 个模块/文件,vibe coding 方式。
- docs/PHASE1_TASKS.md 是原分期清单(内容与新规划重叠),按新规划执行。
- 用户零基础、边做边学:涉及用户不会的技术,先讲最短必要概念再给代码,代码解释用"零基础能懂"的话。
- 用户要求:每个任务只做 1~2 个模块/文件,不越界扩展。
