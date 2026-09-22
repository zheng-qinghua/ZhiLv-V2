# 智旅云图 复现版 · 第一期任务清单

> 总目标分三期(见 docs/ARCHITECTURE.md)。本文件是**第一期**的可执行任务清单,按顺序执行,每个任务带完成标准。做完一期再进二期。

## 第一期目标

跑通完整最小链路:**前端 → Spring Boot → MySQL + Redis → Python AI 服务**,实现**表单式行程生成**全流程(1:1 复现源项目的核心功能),同时搭好对话式的基础设施。

## 环境准备(前置,不依赖代码)

- [ ] **P1.0 工具链安装**
  - JDK 17、Maven 或 Gradle、Node.js 20+、Python 3.10+、Docker Desktop
  - 完成标准:终端可执行 `java -version`、`mvn -version`、`node -v`、`python --version`、`docker --version`
  - 学习资源:见 docs/tutorials/spring-boot-tutorial.md 第一、二阶段

## A 组:Spring Boot 后端骨架(学 Spring 的同时做)

- [ ] **P1.1 初始化 Spring Boot 项目**
  - 用 Spring Initializr 生成 Spring Boot 4 + Java 17 项目,依赖:`web`、`data-jpa`、`security`、`data-redis`、`validation`、`mysql-connector`
  - 完成标准:`backend/` 可启动,访问 `/` 返回内容;`pom.xml` 依赖齐
- [ ] **P1.2 统一响应体 + 全局异常处理**
  - 写 `common/ApiResponse`(code/message/data)和 `@RestControllerAdvice` 全局异常处理器
  - 完成标准:抛异常时返回统一 JSON 结构,不裸抛 500
- [ ] **P1.3 配置文件**
  - `application.yml`:数据源、Redis、JWT 密钥、AI 服务地址等走环境变量,提供 `application-dev.yml`
  - 完成标准:配置外置,本地 `docker-compose` 起的 MySQL/Redis 能连上

## B 组:数据层 + 用户认证(先把地基打牢)

- [ ] **P1.4 建表 + JPA 实体**
  - 迁移源项目表结构:users、trips(含 days/spots 明细,存 JSON 或拆表)、chat_sessions、chat_messages
  - 完成标准:Spring Boot 启动自动建表,或用 migration 脚本
- [ ] **P1.5 注册/登录(Spring Security + JWT)**
  - BCrypt 密码哈希;注册、登录接口;JWT 生成与校验过滤器
  - 完成标准:前端能注册登录拿到 token,受保护接口带 token 可访问
- [ ] **P1.6 Redis 接入(第一个真实用途:登录态/黑名单)**
  - 用 Spring Data Redis 封装一个 `RedisService`;登录后把 token 写入 Redis,登出/失效走黑名单
  - 完成标准:Redis 里能看到 token,`redis-cli` 可查;这一步把 Redis 跑通,后续会话存储复用

## C 组:Python AI 服务(学习 LangGraph 的同时做)

- [ ] **P1.7 AI 服务骨架**
  - FastAPI 项目,`POST /generate`(输入 TripRequest,输出 TripPlan)、`GET /health`
  - 复用智旅助手的 LLM 配置(DeepSeek + ChatOpenAI)
  - 完成标准:`curl` 调用 `/generate` 能返回结构化行程 JSON
- [ ] **P1.8 结构化行程生成(先单轮)**
  - 把智旅助手的 `trip_planner_agent.py` 的生成逻辑搬进来,输出对齐**统一行程模型** `TripPlan`(见 ARCHITECTURE 3.2)
  - 完成标准:给定 TripRequest,返回字段完整的 TripPlan,天数与请求一致
- [ ] **P1.9 RAG 检索接入(可选但推荐)**
  - 复用智旅助手的 RAG 检索逻辑(向量库改用 Milvus,替代源项目 ChromaDB / 智旅助手 FAISS),生成前检索攻略作为上下文
  - 完成标准:有/无 RAG 上下文的生成结果质量差异可见

## D 组:前后端联调(闭环)

- [ ] **P1.10 前端迁移 + 表单式对接**
  - 把源项目前端复制到 `frontend/`,改 axios 基地址指向 Spring Boot;表单式规划页调 `/api/trips`
  - 完成标准:填表 → 生成 → Result 页展示 → 保存 → History 页可见,全链路跑通
- [ ] **P1.11 Spring Boot 调用 AI 服务**
  - Spring Boot 写 `ai/AiServiceClient`(WebClient),把表单请求转发 Python `/generate`,拿到 TripPlan 落库
  - 完成标准:前端表单提交后,MySQL 里出现完整行程记录,前端正常渲染

## E 组:基础设施收尾(第一期结束状态)

- [ ] **P1.12 docker-compose 一键启动**
  - frontend / backend / ai-service / redis / mysql 五个服务编排,`docker compose up` 一条命令起
  - 完成标准:新机器 clone 后一条命令能跑起来
- [ ] **P1.13 第一期验收**
  - 走一遍:注册登录 → 表单规划 → 生成 → 保存 → 历史查看
  - 完成标准:与源项目核心功能行为一致,Redis 有数据,日志无报错

## 第一期结束后

进入第二期(对话式):Spring Boot 加 `/api/chat`(SSE 透传)→ Python 用 LangGraph 重写多轮对话图(信息收集 → 追问 → 抽齐 → 生成)→ 前端加聊天面板。具体任务到二期再细化。

## 学习节奏对照(边做边学)

| 阶段 | 配套教程(docs/tutorials/) | 需要掌握的 |
|---|---|---|
| P1.1-P1.3 | spring-boot-tutorial 前 3 阶段 | IoC/DI、项目结构、REST |
| P1.4-P1.6 | redis-tutorial 全部 | 数据结构、RedisTemplate、@Cacheable |
| P1.7-P1.9 | langgraph-tutorial 前 3 阶段 | State/Node/Edge、第一个图 |
| P1.10-P1.12 | 三份教程 + 官网 | 综合运用 |

## 原则

1. **每完成一个任务就跑通一次**,不要攒到最后联调。
2. **遇到不会的先查教程对应章节**,教程没有的再问 Claude。
3. **统一行程模型改字段,必须三处同步**(前端类型 / Java DTO / Python Pydantic)。
4. 第一期**不做**对话式、不做消息队列、不做 Redis 集群,克制加需求。
