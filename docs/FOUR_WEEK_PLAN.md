# 智旅云图 复现版 · 四周冲刺计划(28 天)

> 目标:**4 周内 1:1 复现核心功能 + 新增对话式规划**,vibe coding 方式(Claude 写代码,你做验收和理解)。
> 前提:完全 0 基础,边做边学。每天建议 2~4 小时,每周留一天缓冲。
> 铁律:**每次给 Claude 的任务不超过 2 个模块/文件**,保证代码质量和你的理解成本。

---

## 技术决策备忘(随项目演进随时补充)

- **向量数据库用 Milvus**(不用源项目的 ChromaDB、也不用智旅助手的 FAISS)。原因:Milvus 是独立的向量数据库服务,支持生产级扩展;RAG 检索逻辑与后端解耦,替换连接即可,切换成本低。
  - 落地点:D24 接入 RAG,D27 docker-compose 加 milvus 服务,本地开发 D24 前用单条 docker 命令起 Milvus standalone。
- **Spring Boot 4.1.x**(非 3.x):3.x 已于 2026-06 停止社区维护,Spring Initializr 只提供 4.x;本教程与代码均已按 4.x 更新。
- **表单/对话互斥**:一次规划只能选一种模式,产物统一为 `TripPlan` 进入同一套展示/保存流程。

---

## 第一部分:vibe coding 怎么让 Claude 干活

### 核心原则

1. **一次只做一件事**。每次会话只让 Claude 做 1~2 个文件/模块,不要丢一个大需求让它自由发挥。
2. **上下文靠 claude.md**。项目根目录的 `claude.md` 已写清技术栈、架构规则、目录结构。发给 Claude 的提示词里只要一句"先读根目录 claude.md",它就会自动按规范写。
3. **任务完成 = 你验收**。让 Claude 自己跑测试/启动服务,并列出改动清单和验证方法。你负责"看它改了啥、跑通没"。
4. **看不懂就问**。0 基础不丢人,让 Claude"逐行解释这段代码,我是零基础"。
5. **每一步能运行才算过**。当天任务没跑通,不进入下一天,先修。

### 发提示词的五个要素(每次必带)

| 要素 | 说明 | 示例 |
|---|---|---|
| 1. 背景 | 一句话说清在做什么项目 | "我在做智旅云图复现项目,先读根目录 claude.md" |
| 2. 范围 | 明确只做哪些文件(≤2 个) | "只新建 JwtUtil.java,不改其他文件" |
| 3. 参考 | 源项目对应代码的位置 | "参考 C:\...\源项目\backend\app\api\routes\trip.py 的逻辑" |
| 4. 约束 | 必须遵守的规则 | "遵守架构文档统一行程模型;分层 Controller→Service→Repository" |
| 5. 交付 | 要它交什么 | "列出改动清单 + 告诉我怎么启动验证" |

### 通用提示词模板(直接复制改)

```
我在做「智旅云图复现」项目。请先读项目根目录的 claude.md 和 docs/ARCHITECTURE.md,按其中的规范来做。

本次只做【模块名】,涉及文件(新建/修改,不超过2个):
- backend/src/main/java/com/zhilv/.../XXX.java

要求:
1. 【功能点1】
2. 【功能点2】
3. 【约束:分层/命名/不动范围外代码】
4. 【如何验证:启动命令/测试命令】

参考源:【源项目对应文件路径】

完成后:列出改动文件清单,说明改了哪些逻辑,并告诉我启动后怎么验证(访问什么地址、看什么输出)。如果代码有我看不懂的地方,用零基础能懂的话解释。
```

### 完整提示词示例(认证任务,可直接复制)

```
我在做「智旅云图复现」项目。请先读项目根目录 claude.md 和 docs/ARCHITECTURE.md。

本次只做【注册/登录 + JWT 认证】,涉及文件(不超过2个):
- backend/src/main/java/com/zhilv/controller/AuthController.java (新建)
- backend/src/main/java/com/zhilv/service/UserService.java (新建)

要求:
1. 注册接口:接收 username/password,密码用 BCrypt 加密存到 users 表,重复用户名返回统一错误。
2. 登录接口:校验密码,成功签发 JWT 返回 token。
3. 用项目已有的 ApiResponse 统一返回格式,异常走全局处理器。
4. 只做这两层,不要改 entity/repository 以外的东西;如果缺 User 实体或 UserRepository,告诉我缺什么、补哪些文件,等我确认再补。
5. JWT 密钥、过期时间放 application.yml 走环境变量。

参考源:源项目的认证逻辑在 C:\Users\20243\Desktop\Agent Param\auth 和 C:\Users\20243\Desktop\智旅云图 源项目\zhilv-yuntu\backend\app 下,可参考其 BCrypt 用法和 token 结构,但用 Spring Security + JWT 标准做法实现。

完成后:列出改动文件清单,说明启动命令和验证方式(用 curl 或浏览器访问哪个地址、期望什么返回)。我完全零基础,代码里涉及 Spring Security 的过滤器部分请额外用通俗的话解释一遍。
```

---

## 第二部分:28 天逐日计划(详细版)

图例:🎓=当天学的教程章节,🛠=给 Claude 的开发任务,✅=当天验收标准。
教程在 `docs/tutorials/`(spring-boot-tutorial.md / redis-tutorial.md / langgraph-tutorial.md)。
后端代码统一位于 `backend/src/main/java/com/zhilv/`,下文用 `com.zhilv.XXX` 简写包名。

### Week 1:环境与后端地基(第 1~7 天)

**D1 · 环境安装 + 学前知识**
- 🎓 spring 教程第 0 章(学前必备:后端/HTTP/数据库/JSON 是什么)+ 第 1 章(怎么用这份教程)
- 🛠 无开发任务,纯环境:JDK 17+、VS Code(装 Extension Pack for Java)、Maven、Docker Desktop、Node.js 20+、Python 3.10+
- ✅ `java -version`、`node -v`、`python --version`、`mvn -version`、`docker --version` 都有输出

**D2 · Java 基础 + 后端骨架**
- 🎓 spring 教程第 2 章(Spring Boot 是什么)+ 第 3 章(Java 基础速成)
- 🛠 任务:用 Spring Initializr 生成项目,跑通 Hello World
  - 文件:`backend/pom.xml`、`ZhilvApplication.java`、`com.zhilv.controller.HelloController`
  - 版本:Spring Boot 4.1.x + Java 17 语言级别
- ✅ `./mvnw spring-boot:run` 后访问 `http://localhost:8080` 有内容(已完成)

**D3 · Spring 核心原理(不写代码,纯理解)**
- 🎓 spring 教程第 4 章(Spring 核心原理:IoC / DI / Bean)重点,配合 Claude 解释
- 🛠 无开发任务。让 Claude"用生活类比讲一遍 IoC 和 DI,我零基础"
- ✅ 能用自己的话说出"为什么 Spring 自动给我对象,不用 new"(已完成)

**D4 · 统一响应 + 全局异常**
- 🎓 spring 教程第 5 章(第一个项目:pom.xml / application.yml / 三层架构)
- 🛠 任务A:`com.zhilv.common.ApiResponse`(统一响应体 code/message/data + success/error 静态方法)
- 🛠 任务B:`com.zhilv.common.GlobalExceptionHandler`(@RestControllerAdvice 全局异常,不裸抛 500)
- ✅ 访问 `/demo/error` 收到 `{code:500,message:"服务器开小差了,请稍后再试",data:null}` 而不是浏览器默认错误页(已完成)

**D5 · 建表 + JPA 实体(本次)**
- 🎓 spring 教程第 7 章前 2 节(Entity / Repository 深入 + 事务)
- 🛠 任务A:`com.zhilv.entity.User` + `com.zhilv.repository.UserRepository`(JPA 建 users 表)
  - 字段:id / username(唯一)/ password(BCrypt 哈希)/ created_at
- 🛠 任务B:`com.zhilv.entity.Trip` + `com.zhilv.repository.TripRepository`(JPA 建 trips 表)
  - 字段:id / user_id / title / destination / start_date / end_date / day_count / travelers / budget / preferences(JSON 串)/ pace / special_notes / summary / tips(JSON 串)/ plan_json(完整行程 JSON)/ source(FORM|CHAT)/ created_at / updated_at
  - 设计思路对齐源项目 `trip_records`:完整行程存大 JSON(`plan_json`),拆出顶层字段方便列表展示和查询
- 依赖:`spring-boot-starter-data-jpa` + `mysql-connector-j`;数据源配置走环境变量(默认 root/root 对应本地容器)
- ✅ 起 MySQL 容器,Spring Boot 启动后 MySQL 里自动建出 `users`、`trips` 两张表(需先装 Docker Desktop)

**D6 · 数据层完善(ChatSession/ChatMessage)**
- 🎓 spring 教程第 7 章前 2 节(复习)
- 🛠 任务A:`com.zhilv.entity.ChatSession` + `ChatSessionRepository`
  - 字段:id / user_id / title / created_at / updated_at
- 🛠 任务B:`com.zhilv.entity.ChatMessage` + `ChatMessageRepository`
  - 字段:id / session_id / role(USER|ASSISTANT)/ content / created_at
- ✅ `chat_sessions`、`chat_messages` 建出;四张表(users/trips/chat_sessions/chat_messages)都能查

**D7 · 缓冲日(Week1 复习验收)**
- 🎓 复习本周没看懂的章节,看懂为止
- 🛠 最多 1 个修 bug 任务
- ✅ 后端能启动、四张表就绪、统一响应生效

### Week 2:认证 + Redis + 表单业务(第 8~14 天)

**D8 · 注册/登录接口**
- 🎓 spring 教程第 8 章(Spring Security + JWT)前半
- 🛠 任务A:`com.zhilv.controller.AuthController`(POST `/api/auth/register`、POST `/api/auth/login`)
- 🛠 任务B:`com.zhilv.service.UserService`(注册 BCrypt 加密、重复用户名返回统一错误;登录校验密码,签发 JWT 返回 token)
- ✅ curl 能注册、登录,返回 token;重复注册返回统一错误 JSON

**D9 · JWT 过滤器 + 安全配置**
- 🎓 spring 教程第 8 章后半(过滤器链路、SecurityConfig)
- 🛠 任务A:`com.zhilv.config.JwtUtil`(签发/解析 token)
- 🛠 任务B:`com.zhilv.config.SecurityConfig` + `com.zhilv.config.JwtAuthenticationFilter`(白名单放行注册/登录,其余接口校验 token)
- ✅ 不带 token 访问受保护接口返回 401,带 token 放行

**D10 · Redis 接入(token 黑名单)**
- 🎓 redis 教程第 0 章(学前必备)+ 阶段 1~3
- 🛠 任务A:`com.zhilv.config.RedisConfig` + `com.zhilv.service.RedisService`(封装 set/get/delete)
- 🛠 任务B:登录写 token、登出进黑名单、过滤器校验黑名单
- ✅ `docker exec -it <redis容器> redis-cli` 能看到 token 记录;登出后旧 token 失效

**D11 · 统一行程模型(TripPlan)**
- 🎓 复习 spring 教程第 6 章(校验 @Valid)
- 🛠 任务A:`com.zhilv.dto.TripPlan`(严格按 docs/ARCHITECTURE.md 3.2 的 JSON 结构:顶层 + days[].spots[]/meals[]/transport)
- 🛠 任务B:`frontend/src/types/trip.ts`(前端类型,与 TripPlan 对齐)
- ✅ Java DTO / TS 类型 / 架构文档三处字段完全一致(这是跨服务契约,改一处必须同步另两处)

**D12 · 行程控制器 + 服务(表单提交)**
- 🎓 复习 spring 教程第 6 章(REST 完整写法)
- 🛠 任务A:`com.zhilv.controller.TripController`
  - POST `/api/trips`:接收 TripRequest(目的地/预算/偏好等),校验后交给服务
  - GET `/api/trips`:按当前用户返回历史列表
- 🛠 任务B:`com.zhilv.service.TripService`(接收 TripRequest、字段校验、先落库草稿,source=FORM)
- ✅ 表单提交后 trips 表出现一条草稿记录

**D13 · 行程落库 + 历史接口**
- 🎓 复习 spring 教程第 6 章(分页查询)
- 🛠 任务A:TripService 完善(草稿→正式落库;GET `/api/trips` 按用户分页返回;DELETE `/api/trips/{id}` 删除)
- 🛠 任务B:导出接口(GET `/api/trips/{id}/export`,返回行程 JSON 全量)
- ✅ 历史列表接口能按用户返回行程;能删;能导出

**D14 · 缓冲日(Week2 复习验收)**
- 🎓 复习 JWT 和 Redis 两章,不懂的让 Claude 讲
- 🛠 最多 1 个修 bug 任务
- ✅ 完整走一遍:注册→登录→带 token→提交行程→查历史

### Week 3:AI 服务 + 表单链路闭环(第 15~21 天)

**D15 · AI 服务骨架**
- 🎓 langgraph 教程第 0~1 阶段(LangGraph 是什么、概念)
- 🛠 任务A:`ai-service/app/main.py` + `app/config.py` + GET `/health` + POST `/generate`(先返回假数据)
- ✅ `curl http://localhost:8100/health` 返回 ok;`/generate` 能调通返回占位 JSON

**D16 · DeepSeek 接入 + 单轮生成**
- 🎓 langgraph 教程第 2 阶段(第一个图)
- 🛠 任务A:LLM 配置(复用智旅助手 config.py,DeepSeek + ChatOpenAI)+ 单轮生成逻辑(搬 `trip_planner_agent.py`)
- ✅ 给定 TripRequest,返回能调通 LLM 的行程文本;DeepSeek API Key 提前就绪

**D17 · 生成对齐 TripPlan + Pydantic 模型**
- 🎓 langgraph 教程第 3 阶段(LangChain 集成)
- 🛠 任务A:`ai-service/app/models/*.py`(Pydantic 模型对齐 TripPlan)+ 生成逻辑改造为返回结构化 JSON
- ✅ 给定 TripRequest,返回字段完整、天数与请求一致的 TripPlan JSON(与 D11 的 Java DTO / TS 类型一致)

**D18 · Spring Boot 调 AI(客户端)**
- 🎓 复习 spring 教程第 6 章(WebClient 或 RestClient 用法,让 Claude 演示)
- 🛠 任务A:`com.zhilv.ai.AiServiceClient`(RestClient 调 `POST /generate`,反序列化 TripPlan)
- ✅ Spring Boot 能调到 Python 服务并拿到 TripPlan(可先写个临时验证接口)

**D19 · 表单链路闭环**
- 🛠 任务A:TripService 改造:提交表单 → 调 AiServiceClient 生成 → 拿 TripPlan → 落库(plan_json 等字段填全)→ 返回给前端
- ✅ 后端 POST `/api/trips` 一次调用返回完整行程;MySQL 出现完整行程记录

**D20 · 前端迁移 + 表单对接**
- 🎓 无(直接用源项目前端代码)
- 🛠 任务A:把源项目 frontend 复制进 `frontend/`,axios 基地址改指向 Spring Boot
- 🛠 任务B:`frontend/src/views/Home.vue` 表单提交对接 + `frontend/src/services/api.ts` 封装(携带 JWT)
- ✅ 浏览器填表能调通后端,返回行程数据

**D21 · Result 页渲染 + 保存 + 历史(Week3 验收)**
- 🛠 任务A:`frontend/src/views/Result.vue` 渲染 TripPlan(复用源项目展示样式,含每日安排/景点/餐饮)
- 🛠 任务B:保存按钮(落库调后端)+ `frontend/src/views/History.vue` 历史列表联动
- ✅ 表单式全链路跑通:填表→生成→展示→保存→历史可见

### Week 4:对话式 + 部署收尾(第 22~28 天)

**D22 · 会话数据层 + 接口**
- 🎓 langgraph 教程第 4 阶段(checkpointer / 多轮记忆)
- 🛠 任务A:`com.zhilv.controller.ChatController` + `com.zhilv.service.ChatService`
  - POST `/api/chat/sessions`:创建会话
  - GET `/api/chat/sessions`:列会话
  - GET `/api/chat/sessions/{id}/messages`:拉历史消息
- ✅ 能创建会话、存消息、按 sessionId 拉取历史(会话状态实际由 Python 的 LangGraph checkpointer + Redis 管,Spring 只存映射和消息落库)

**D23 · LangGraph 多轮对话图(核心,拆细)**
- 🎓 langgraph 教程第 5 阶段(工具调用 / 实战)重点
- 🛠 任务A:`ai-service/app/graph/travel_agent.py` 第一步:信息收集状态机
  - State 字段:目的地/预算/天数/偏好/节奏,缺哪个就在回复里追问哪个,逐步收敛
- ✅ 聊天里说"帮我规划杭州3天"能追问缺的信息(预算、偏好等)

**D24 · 多轮图补全:生成收敛 + RAG(Milvus)**
- 🎓 langgraph 教程第 6 阶段(完整实战示例)
- 🛠 任务A:信息抽齐后自动调用生成函数,产出 TripPlan(复用 `/generate` 逻辑)
- 🛠 任务B:RAG 接入:把智旅助手 `rag/*` + `agents/tools/rag_tool.py` 逻辑迁移到 **Milvus** 后端,生成前检索攻略作为上下文
  - 前置:D24 前先用 docker 起 Milvus standalone(一条命令),索引智旅助手现有攻略数据
- ✅ 完整对话:追问→补齐→生成出可保存的 TripPlan;开启 RAG 后生成质量明显提升

**D25 · SSE 流式输出**
- 🎓 langgraph 教程第 7 阶段(streaming)
- 🛠 任务A:`ai-service/app/main.py` `/chat` 改 SSE 端点
- 🛠 任务B:`com.zhilv.controller.ChatController` 透传 SSE + `AiServiceClient` 流式版
- ✅ curl 能看到事件流,生成过程逐步返回

**D26 · 前端聊天面板 + 模式互斥**
- 🛠 任务A:`frontend/src/components/chat-panel/ChatPanel.vue`(消息列表 + 输入框 + 流式渲染)+ `services/chat.ts`
- 🛠 任务B:`Home.vue` 表单/对话二选一互斥,对话完成后跳 Result.vue(与表单共用展示/保存/历史)
- ✅ 页面能对话、流式回复;两种方式都进入同一 Result/History 流程;互斥正确(进一种模式另一种不可用)

**D27 · 一键部署**
- 🛠 任务A:`docker-compose.yaml` 编排 **frontend/backend/ai-service/redis/mysql/milvus** 六个服务
- 🛠 任务B:各服务 Dockerfile + `.env.example` + 数据初始化脚本(建库、Milvus 建集合、攻略灌数据)
- ✅ 新机器 `docker compose up` 一条命令全部起跑,全链路可用

**D28 · 全量验收 + 收尾**
- 🛠 任务:完整走查 + 修 bug(每次一个)
- ✅ 验收清单:注册登录→表单规划→对话规划→互斥正确→保存→历史→导出→RAG 生效→部署一条命令起

---

## 第三部分:遇到问题的处理

| 情况 | 做法 |
|---|---|
| 看不懂 Claude 写的代码 | 追加提示:"逐行解释这段代码,我完全零基础,重点讲 X 部分" |
| 当天任务没跑通 | 不进入下一天。贴报错给 Claude:"报错如下,帮我定位修复,先讲原因再改" |
| 报错太长 | 直接把完整报错复制给 Claude,它会自己找原因 |
| 想扩展需求 | 单独开一个新任务,不要在当前任务里追加(保持单模块) |
| 教程和项目对不上 | 以项目实际为准,让 Claude 先解释再动手 |
| Milvus 起不来 / 连接报错 | 先确认 docker 容器在跑、端口(默认 19530)通;报错贴给 Claude |

## 第四部分:节奏建议

- 每天固定顺序:**先学当天教程章节(约 1 小时)→ 再发 Claude 任务 → 验收**。
- 0 基础学 Spring 最快的方式是"跟着 Claude 写的代码问为什么",教程当字典查。
- D7、D14 是缓冲日,专治"学得累";遇到 D24 RAG / D27 部署这种大活,当天做不完就顺延到缓冲日。
- 涉及 Milvus 的两天(D24、D27)需要你提前装好 Docker Desktop——D5 起 MySQL 也依赖它。
- 遇到 DeepSeek API Key 没有 → 在 D16 前准备好(智旅助手 .env 里有现成的)。
- 每次发任务先读一遍"第一部分"的五个要素,保证 Claude 拿到的上下文完整。
