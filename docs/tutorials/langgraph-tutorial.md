# LangGraph 从入门到能用的实战教程

> 面向已有 Python 基础、用过 FastAPI + LangChain + DeepSeek 做过旅行规划项目（RAG / ReAct / 单轮结构化行程生成）的学习者。
> 目标：从入门到会用 —— 不要求读源码，但要懂原理、能看懂项目、能动手搭一个**多轮聊天式旅行规划 Agent**，达到去实习的"能上手"程度。
> 本教程所有代码基于 LangGraph **1.x**（写作时最新稳定版为 **1.2.x**，要求 Python 3.10+）。

---

## 目录

- [0. 学习路径总览](#0-学习路径总览)
- [1. LangGraph 是什么？和 LangChain 的关系](#1-langgraph-是什么和-langchain-的关系)
- [2. 核心概念逐个讲透](#2-核心概念逐个讲透)
- [3. 写第一个小图：从线性流程到带分支](#3-写第一个小图从线性流程到带分支)
- [4. 状态管理与多轮对话：checkpointer](#4-状态管理与多轮对话checkpointer)
- [5. 与 LLM 集成：DeepSeek + 工具调用](#5-与-llm-集成deepseek--工具调用)
- [6. 实战：多轮旅行规划 Agent（最小可运行示例）](#6-实战多轮旅行规划-agent最小可运行示例)
- [7. 流式输出 streaming](#7-流式输出-streaming)
- [8. 资源清单](#8-资源清单)
- [9. 给"边学边做"的实习者的几点建议](#9-给边学边做的实习者的几点建议)

---

## 0. 学习路径总览

| 阶段 | 内容 | 预计耗时 | 学到什么程度算过 |
|---|---|---|---|
| 阶段一 | 概念 + 第一个小图 | 2~4 小时 | 能不看文档画出 StateGraph，跑通线性 + 条件分支 |
| 阶段二 | 状态管理与多轮对话（checkpointer） | 3~5 小时 | 能说明 State/Reducer/Checkpointer 的关系；能跑通多轮记忆对话 |
| 阶段三 | LLM 集成（DeepSeek / ToolNode） | 3~4 小时 | 会用 ChatOpenAI 接 DeepSeek，能调工具并理解工具调用闭环 |
| 阶段四 | 实战：多轮旅行规划 Agent | 1~2 天 | 独立完成最小示例，并说出它和你现有项目的对应关系 |
| 阶段五 | 流式输出 + 收尾 | 3~4 小时 | 能解释三种 stream_mode，会用 astream 接 FastAPI SSE |

总时间：约 **1 周**（每天 2~3 小时）可达到"能看懂项目、能搭最小多轮 Agent"的实习水平。想要更扎实，把[资源清单](#8-资源清单)里的 LangGraph Academy 前 3 个模块补完即可。

---

## 1. LangGraph 是什么？和 LangChain 的关系

### 一句话概括

LangGraph 是 LangChain 官方推出的**用图来编排 LLM 应用 / Agent 的框架**。它把一次复杂的任务执行流程建模成一张**有向图**：图中的**节点（Node）**是"做一件事"的函数，**边（Edge）**是"做完这件事下一步去哪"。

### 和 LangChain 的关系

- **LangChain**：偏"积木"层。提供 `ChatOpenAI`（模型封装）、`PromptTemplate`、`@tool`（工具）、`Runnable`（链）等组件。适合**简单、线性的流水线**（RAG：检索 → 拼提示词 → 生成）。
- **LangGraph**：偏"编排"层。在 LangChain 组件之上，提供**状态管理、循环、条件分支、持久化（记忆）、断点续跑、人在环路（human-in-the-loop）、流式输出**等能力。适合**复杂、有状态、需要多轮交互**的 Agent。
- 关系总结：**LangGraph 内部仍然大量使用 LangChain 的组件（模型、工具、消息类型）**，只是把"谁来调度"换成了图。所以你会看到代码里 `from langchain_openai import ChatOpenAI` 和 `from langgraph.graph import StateGraph` 同时出现。

### 什么时候该用 LangGraph 而不是纯 LangChain？

| 场景 | 选 LangChain | 选 LangGraph |
|---|---|---|
| 单轮、线性的 RAG / 文本生成 | ✅ | |
| 需要工具调用并且可能"多轮工具调用才拿到结果"（ReAct 循环） | | ✅ |
| 多轮对话，要记住上下文（跨请求的记忆） | 要自己塞 history | ✅ 内置 |
| 流程有分支 / 循环 / 需要动态决定下一步 | 写起来很别扭 | ✅ 天然支持 |
| 中断后恢复（比如等人工审批 / 等用户补充信息） | | ✅ 内置 |
| 要在浏览器 / App 里做流式输出 | 要自己拼 | ✅ 内置 stream |

**给你的直接判断**：你现有项目里"单轮 LLM 生成结构化行程"用纯 LangChain 没问题；但一旦要升级成**多轮聊天式规划**（先聊目的地、预算、天数，信息齐了再生成行程），中间有"信息是否齐全"的分支判断、有跨轮次的记忆、有"缺什么问什么"的循环 —— 这就是 LangGraph 的主场。

### 当前版本（2026 年现状）

- LangGraph 于 **2025 年 10 月发布 1.0 稳定版（GA）**，此后 API 已冻结。
- 写作时最新稳定版为 **1.2.x**（2026 年 8 月已到 1.2.11）。
- 要求 **Python 3.10+**，不支持 3.9 及更早版本。
- 安装：

```bash
pip install -U langgraph langchain-openai
# 需要 Redis 持久化时再加：
pip install -U langgraph-checkpoint-redis
```

> 提示：1.0 起 `langgraph.prebuilt` 里的 `create_react_agent` 正在逐步迁移到 `langchain` 的 `create_agent`。本教程**刻意不依赖它**，全部手写节点 + 边，因为这才是你理解原理、面试能讲清楚的关键。`ToolNode` 依然可用。

---

## 2. 核心概念逐个讲透

LangGraph 的全部核心概念就六个：**State、Node、Edge、Graph（StateGraph）、条件边（Conditional Edge）、START/END**。逐个讲：

### 2.1 State（状态）

State 是贯穿整个图执行的**共享数据对象**，本质是一个字典（或 Pydantic 模型）。每一个节点都会接收当前 State，可以读它、改它，然后把"要更新的部分"返回，LangGraph 会自动把返回值**合并**进 State 传给下一个节点。

```python
from typing import TypedDict

class MyState(TypedDict):
    text: str            # 普通字段，后写的覆盖先写的
    messages: list       # 消息字段，通常要"累加"而不是覆盖
```

**关键点**：
- 节点**返回什么字段，就更新什么字段**；不返回的字段保持原样。
- 字段的"合并方式"由 **Reducer（归约器）** 决定（见 2.2）。
- State 会在每次执行后保存一份 **Checkpoint（检查点）**，这是"记忆"的底层机制（见第 4 章）。

### 2.2 Reducer（归约器，进阶但必懂）

默认情况下，节点返回值会**覆盖**同名 State 字段。但聊天消息需要的是**追加**，不是覆盖。`add_messages` 就是一个最常用的 Reducer，它把新消息拼到旧消息后面。

```python
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # 追加而非覆盖
```

`Annotated[类型, 归约器]` 的写法就是告诉 LangGraph："这个字段用这个归约器来合并"。你只需要会用它、知道它是干嘛的即可，暂不用自己写归约器。

### 2.3 Node（节点）

节点就是一个普通的 Python 函数：**输入整个 State，返回要更新的字段字典**。

```python
def my_node(state: MyState) -> dict:
    new_text = state["text"] + " 又走了一步"
    return {"text": new_text}   # 只返回要更新的字段
```

节点里想干什么都行：调 LLM、调工具、查数据库、做算术。它不关心"下一步去哪"，那是边的事。

### 2.4 Edge（边）

边定义"从这个节点出来后去哪"。

- `builder.add_edge("A", "B")`：A 执行完**无条件**去 B。
- 还有一种特殊边：**条件边**，见 2.6。

### 2.5 Graph（图）与 StateGraph

`StateGraph` 是 LangGraph 用来搭建图的"画布"，需要传入 State 的类型定义。把节点和边都加好后，调用 `.compile()` **编译**成可执行的图，然后就可以 `.invoke()` / `.stream()` 了。

```python
from langgraph.graph import StateGraph

builder = StateGraph(MyState)   # 传入 State schema
builder.add_node("node_name", my_node)   # 注册节点
builder.add_edge(...)                    # 注册边
graph = builder.compile()                # 编译成可执行图
result = graph.invoke({"text": "hello"}) # 执行
```

### 2.6 条件边（Conditional Edge）

条件边用来做**分支路由**：从一个节点出发，根据 State 里的内容，动态决定下一步去哪个节点。写法是：给 `add_conditional_edges` 传一个"路由函数"，它返回下一步节点名。

```python
def route_after_check(state: MyState) -> str:
    if state["text"].startswith("天气"):
        return "weather_node"   # 去查天气
    return "default_node"       # 默认回复

builder.add_conditional_edges(
    "check_node",               # 从哪个节点出发
    route_after_check,          # 路由函数
    {"weather_node": "weather_node", "default_node": "default_node"}  # 映射表（可选但推荐）
)
```

这个"路由函数 + 映射表"的组合，正是旅行 Agent 里"信息齐不齐"判断的核心。

### 2.7 START 和 END

- **START**（入口）：图从哪开始跑。每个图都要有一条 `START → 第一个节点` 的边。
- **END**（出口）：图到哪结束。`graph.invoke()` 会返回**最后一个节点的输出合并后的最终 State**。

```python
from langgraph.graph import START, END

builder.add_edge(START, "first_node")   # 入口
builder.add_edge("last_node", END)      # 出口
```

### 概念小结（一张图记住）

```
   START
     │
     ▼
 ┌─────────┐  条件边   ┌─────────┐
 │ node_A  │ ────────► │ node_B  │ ──► END
 └─────────┘  分支/循环 │         │
       ▲                └─────────┘
       │    (条件边形成循环)
       └────────────────
   整个流程共享同一个 State；每个节点读它、更新它。
```

---

## 3. 写第一个小图：从线性流程到带分支

### 3.1 准备工作（环境）

```bash
# 建议用虚拟环境（conda 或 venv 均可）
pip install -U langgraph langchain-core langchain-openai python-dotenv
python -c "import langgraph; print(langgraph.__version__)"  # 应显示 1.x
```

先不用接真实模型，用纯函数跑通图，把概念焊死。

### 3.2 线性链式流程

三个节点依次执行：A → B → C。

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class TextState(TypedDict):
    text: str

def node_a(state: TextState) -> dict:
    return {"text": state["text"] + " -> A"}

def node_b(state: TextState) -> dict:
    return {"text": state["text"] + " -> B"}

def node_c(state: TextState) -> dict:
    return {"text": state["text"] + " -> C"}

builder = StateGraph(TextState)
builder.add_node("A", node_a)
builder.add_node("B", node_b)
builder.add_node("C", node_c)

builder.add_edge(START, "A")
builder.add_edge("A", "B")
builder.add_edge("B", "C")
builder.add_edge("C", END)

graph = builder.compile()
result = graph.invoke({"text": "start"})
print(result["text"])
# 输出: start -> A -> B -> C
```

**看懂了什么**：
- `invoke` 传入初始 State `{"text": "start"}`。
- 每个节点都基于上一个节点更新后的 State 工作。
- 最终 `result` 是整个图的最终 State。

### 3.3 带分支的流程

加上一个路由函数：B 之后，如果文本长度超过 20 就走 D，否则走 C。

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class TextState(TypedDict):
    text: str

def node_a(state: TextState) -> dict:
    return {"text": state["text"] + "->A"}

def node_b(state: TextState) -> dict:
    return {"text": state["text"] + "->B"}

def node_c(state: TextState) -> dict:
    return {"text": state["text"] + "->C"}

def node_d(state: TextState) -> dict:
    return {"text": state["text"] + "->D"}

def route_after_b(state: TextState) -> str:
    # 返回"下一步节点名"
    if len(state["text"]) > 20:
        return "D"
    return "C"

builder = StateGraph(TextState)
builder.add_node("A", node_a)
builder.add_node("B", node_b)
builder.add_node("C", node_c)
builder.add_node("D", node_d)

builder.add_edge(START, "A")
builder.add_edge("A", "B")
builder.add_conditional_edges("B", route_after_b, {"C": "C", "D": "D"})
builder.add_edge("C", END)
builder.add_edge("D", END)

graph = builder.compile()

print(graph.invoke({"text": "hi"})["text"])
# hi->A->B->C
print(graph.invoke({"text": "a very very very very long input"})["text"])
# a very very very very long input->A->B->D
```

**看懂了什么**：
- `add_conditional_edges("B", route_after_b, {...})` 表示：B 跑完后，调用 `route_after_b(state)` 拿到节点名，再按映射表跳到对应节点。
- 条件边 = 分支；而如果让路由函数返回"更早的节点"，就形成了**循环**（这是 ReAct / 多轮补全信息的底层机制）。

> ✅ **阶段一练习**：把上面分支改成"如果文本以 '重复' 开头，就跳回 A 重新执行一次（形成循环）"。跑通后，你就算过关。

---

## 4. 状态管理与多轮对话：checkpointer

### 4.1 为什么需要 checkpointer（检查点）

默认情况下，`graph.invoke()` 每次执行都是**独立的**，跑完状态就丢了。多轮对话要"记住上一轮说了什么"，就必须在**每轮执行结束时把 State 存下来**，下一轮执行开始时恢复它。

LangGraph 的做法是：给图配置一个 **checkpointer（检查点存储器）**。每执行完一个节点，就把当时的 State 快照保存一份。下次用同一个 **`thread_id`**（会话标识）调用时，自动从上次的检查点继续。

### 4.2 MessagesState 与消息累积

官方把"带消息累加的 State"预置成了 `MessagesState`，省得每次手写：

```python
from langgraph.graph import MessagesState
# 等价于：
# class MessagesState(TypedDict):
#     messages: Annotated[list[BaseMessage], add_messages]
```

消息靠 `add_messages` 自动累积，这就是"多轮上下文"的根基。

### 4.3 多轮记忆对话：MemorySaver（内存版）

先跑一个最简单的带记忆对话，理解 `thread_id` 的作用。这里用一个假模型函数模拟 LLM 回复（先不接真实 API，专注理解记忆机制）。

```python
from typing import TypedDict
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AIMessage, HumanMessage

# 注意：旧教程常写 from langgraph.checkpoint.memory import MemorySaver，
# 新版推荐 InMemorySaver，二者等价。

def fake_llm_node(state: MessagesState) -> dict:
    # 这里只演示"能看到历史消息"。真实项目中换成调用 DeepSeek（见第 5 章）。
    last_human = state["messages"][-1].content
    return {"messages": [AIMessage(content=f"你刚才说：{last_human}。我记住了上下文。")]}

builder = StateGraph(MessagesState)
builder.add_node("chat", fake_llm_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)

# 会话标识：同一个 thread_id = 同一段连续对话
config = {"configurable": {"thread_id": "user-001"}}

# 第一轮
r1 = graph.invoke({"messages": [HumanMessage(content="我叫小明")]}, config)
print(r1["messages"][-1].content)
# 你刚才说：我叫小明。我记住了上下文。

# 第二轮：没有重新传历史，但模型能看到"我叫小明"
r2 = graph.invoke({"messages": [HumanMessage(content="我叫什么？")]}, config)
print(r2["messages"][-1].content)
# 你刚才说：我叫什么？我记住了上下文。
# 注意：fake 模型不真"回忆"，但 state["messages"] 里此刻已经有两轮共 4 条消息
print(len(r2["messages"]))   # 4（AI/人类各 2 条）

# 换一个 thread_id 就是全新会话，什么都不记得
r3 = graph.invoke({"messages": [HumanMessage(content="我叫什么？")]},
                  {"configurable": {"thread_id": "user-002"}})
print(len(r3["messages"]))   # 2（只有这一轮）
```

**关键点**：
- `checkpointer=memory` 开启持久化。
- 每次调用都要带 `config = {"configurable": {"thread_id": "..."}}`。
- 同一个 `thread_id` 共享记忆；不同 `thread_id` 互相隔离。
- `InMemorySaver` 只存内存，**进程重启即丢失**，适合学习和单机 demo。生产要换 Redis / Postgres / SQLite。

### 4.4 接 Redis 持久化（生产级）

要用 Redis 存状态（跨进程、跨重启、可分布式），官方提供 `langgraph-checkpoint-redis`：

```bash
pip install -U langgraph-checkpoint-redis
```

```python
from langgraph.checkpoint.redis import RedisSaver

redis_url = "redis://localhost:6379"
with RedisSaver.from_conn_string(redis_url) as checkpointer:
    checkpointer.setup()   # 首次必须调用：创建所需索引
    graph = builder.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "user-001"}}
    graph.invoke({"messages": [HumanMessage(content="你好")]}, config)
```

**注意**：
- Redis 需要 **RedisJSON** 和 **RediSearch** 两个模块。**Redis 8.0+ 内置**；更老的版本要用 Redis Stack，否则 `setup()` 会报错。
- 支持 TTL 自动过期（如 30 天不活跃自动清理），适合线上控制存储成本。
- 如果反序列化消息报 `MESSAGE_COERCION_FAILURE`，改用 `JsonPlusSerializer` 序列化器（见[官方 RedisSaver 文档](https://pypi.org/project/langgraph-checkpoint-redis/)）。
- 不想上 Redis 的轻量替代：SQLite（`langgraph.checkpoint.sqlite.SqliteSaver`）。

> ✅ **阶段二练习**：把 4.3 的示例改成真实调用 DeepSeek（参考第 5 章），跑 3 轮对话，验证第 3 轮模型记得第 1 轮说的内容。过关标准：你能向别人讲清楚"Reducer（add_messages）负责同一轮内消息追加，Checkpointer 负责跨轮恢复 State"。

---

## 5. 与 LLM 集成：DeepSeek + 工具调用

### 5.1 用 ChatOpenAI 接 DeepSeek（OpenAI 兼容协议）

DeepSeek 提供 OpenAI 兼容接口，所以直接用 `langchain-openai` 的 `ChatOpenAI`，改 `base_url` 即可，一行都不用动 LangChain 生态。

```python
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-chat",                       # deepseek-chat（V3）或 deepseek-reasoner（R1）
    api_key=os.getenv("DEEPSEEK_API_KEY"),       # 建议放环境变量，别硬编码
    base_url="https://api.deepseek.com",         # DeepSeek 官方 OpenAI 兼容端点（/v1 也可）
    temperature=0.7,
    max_tokens=2048,
)

# 直接调用
resp = llm.invoke("北京秋天三天两夜怎么玩？")
print(resp.content)
```

> 也可以装 `langchain-deepseek` 用 `ChatDeepSeek`，写法几乎一样。用 `ChatOpenAI` 的好处是：以后切换任何 OpenAI 兼容厂商（通义千问、智谱、Kimi、本地 vLLM 等）只需要改 `base_url` + `model`。

### 5.2 让 DeepSeek 输出结构化 JSON

DeepSeek 支持 `response_format={"type": "json_object"}`（强制 JSON 输出）。**注意**：要求你的提示词里出现"json"字样，否则会报错。

```python
resp = llm.invoke(
    "根据需求生成一份行程 JSON：北京，3 天，预算 3000 元。",
    response_format={"type": "json_object"},
)
print(resp.content)
# {"days": [...], "budget": {...}, ...}
```

> 进阶：用 `.with_structured_output(PydanticModel)` 直接拿到类型安全的 Pydantic 对象，比手写 `json.loads` 更稳。课程实战示例会用到 `json.loads`，方便你理解原理。

### 5.3 工具调用：ToolNode 与工具调用闭环

Agent 的核心能力是"自己决定要不要查工具"。LangGraph 提供了一个预置组件 **`ToolNode`**，专门负责"执行模型要调用的工具"。

一个典型工具调用闭环（ReAct 循环）：

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_openai import ChatOpenAI
import os

@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气。"""
    # 这里用 mock 数据，真实项目里可换成高德天气 API
    return f"{city} 今天晴，25 度。"

@tool
def get_hotel(city: str, budget: int) -> str:
    """查询某城市、某预算下的推荐酒店。"""
    return f"{city} 预算 {budget} 元/晚的推荐酒店：如家、汉庭。"

tools = [get_weather, get_hotel]
llm_with_tools = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.7,
).bind_tools(tools)

def llm_node(state: MessagesState) -> dict:
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

builder = StateGraph(MessagesState)
builder.add_node("llm", llm_node)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "llm")

# 核心循环边：模型若请求调工具 → 去 tools；否则 → 结束
builder.add_conditional_edges("llm", tools_condition)
builder.add_edge("tools", "llm")   # 工具执行完，把结果作为消息再交给模型

graph = builder.compile()

result = graph.invoke({"messages": [("human", "北京今天天气如何？")]})
print(result["messages"][-1].content)
```

**看懂了什么**：
- `@tool` 把 Python 函数包装成 LLM 可调用的工具，docstring 是给模型看的说明。
- `bind_tools(tools)` 让模型具备"声明要调哪个工具 + 传什么参数"的能力。
- `tools_condition` 是官方预置的路由函数：模型返回了 tool_calls 就去 `tools` 节点执行，否则结束。
- `tools` 节点执行完把工具结果作为消息追加回去，再跳回 `llm`，形成**循环**，直到模型不再要求调工具。
- 这跟 `tools_condition` 的映射表默认约定：有工具调用 → 名为 `"tools"` 的节点；没有 → `END`。所以节点名必须叫 `"tools"`（或用 `tools_condition(ToolNode(...))` 显式绑定）。

> ✅ **阶段三练习**：把上面的天气工具换成你项目里的"高德地图搜索景点"工具（搜索 "高德地图 API Python" 或复用你项目现成的工具函数），让 Agent 先调工具拿到景点列表再回答。过关标准：你能讲清"模型 → 工具 → 模型"这条循环是谁、在哪一步触发、什么时候停。

---

## 6. 实战：多轮旅行规划 Agent（最小可运行示例）

### 6.1 需求与设计

**目标行为**（对应你项目的升级方向）：

1. 用户开口说旅行需求，但**信息不全**（可能缺目的地 / 预算 / 天数）。
2. Agent 缺什么问什么，多轮对话逐步补全信息。
3. 信息齐全后，Agent 调用 LLM 生成**结构化行程 JSON** 回复用户。

**图的设计**：

```
                  START
                    │
                    ▼
              ┌───────────┐
              │ extract   │  从对话里抽取 destination/budget/days
              └───────────┘
                    │
                    ▼
        ┌─────────────────────┐  条件边：信息齐了吗？
        │  route               │
        └─────────────────────┘
        齐了 │                │ 没齐
             ▼                ▼
   ┌─────────────────┐   ┌──────────┐
   │ generate         │   │ ask       │  缺什么问什么
   │ 生成行程 JSON    │   └──────────┘
   └─────────────────┘
             │                │
             ▼                ▼
           END               END
```

- `extract`：用 LLM 从历史消息中抽取三要素，合并进 `travel_info`。
- `route`：条件边。三要素齐全 → `generate`；缺 → `ask`。
- `ask`：让 LLM 用一句话追问缺的字段。**注意 `ask` 连到 END** —— 问完后本轮结束，等用户下一轮回复，再走 `START → extract` 循环。这正是多轮对话的关键。
- 配 `InMemorySaver` 实现跨轮记忆。

### 6.2 完整代码

```python
import json
import os
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import add_messages

# ---------- 1. 初始化 LLM（DeepSeek） ----------
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.7,
    max_tokens=2048,
)

# ---------- 2. 定义 State ----------
class TravelState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # 对话历史（跨轮累积）
    travel_info: dict          # 已收集的需求 {destination, budget, days}
    itinerary: str             # 最终生成的行程 JSON 字符串

REQUIRED_FIELDS = ["destination", "budget", "days"]
FIELD_NAMES = {"destination": "目的地", "budget": "预算", "days": "天数"}

# ---------- 3. 定义节点 ----------
def extract_node(state: TravelState) -> dict:
    """从对话历史里抽取旅行需求三要素，合并进 travel_info。"""
    prompt = SystemMessage(content=(
        "你是一个信息抽取器。根据对话历史抽取用户的旅行需求。"
        "只输出 JSON，格式为 {\"destination\": 目的地字符串或null, "
        "\"budget\": 数字或null, \"days\": 数字或null}。"
        "字段缺失填 null，不要输出任何其他内容。"
    ))
    recent = state["messages"][-6:]   # 只看最近几轮，省 token
    resp = llm.invoke([prompt, *recent], response_format={"type": "json_object"})
    try:
        extracted = json.loads(resp.content)
    except json.JSONDecodeError:
        extracted = {}

    # 合并：保留旧值，新抽取的非空值覆盖旧值
    old = state.get("travel_info", {})
    merged = {
        f: (extracted.get(f) if extracted.get(f) not in (None, "", 0) else old.get(f))
        for f in REQUIRED_FIELDS
    }
    # 注意：days/budget 若用户明确说"0"，不算有效值；此处简化为上面逻辑
    return {"travel_info": merged}


def missing_fields(state: TravelState) -> list[str]:
    info = state.get("travel_info", {})
    return [f for f in REQUIRED_FIELDS if not info.get(f)]


def ask_node(state: TravelState) -> dict:
    """缺信息时，用 LLM 友好地追问缺的字段。"""
    missing = missing_fields(state)
    need = "、".join(FIELD_NAMES[f] for f in missing)
    prompt = SystemMessage(content=(
        f"用户还没有提供：{need}。请用一句自然、友好的中文追问缺少的信息，"
        "不要重复用户已提供的内容，不要输出其他内容。"
    ))
    reply = llm.invoke([prompt, *state["messages"][-3:]])
    return {"messages": [AIMessage(content=reply.content)]}


def generate_node(state: TravelState) -> dict:
    """信息齐全，生成结构化行程 JSON。"""
    info = state["travel_info"]
    prompt = SystemMessage(content=(
        "你是一位资深旅行规划师。根据用户的目的地、预算和天数，"
        "生成一份结构化的行程，只输出 JSON："
        "{\"days\":[{\"day\":1,\"theme\":\"主题\",\"plan\":[\"上午去哪\",\"下午去哪\",\"晚上去哪\"],"
        "\"food\":[\"推荐餐厅\"]}],\"budget\":{\"total\":总预算,\"breakdown\":[\"项\",\"金额\"]},"
        "\"tips\":[\"小贴士\"]}。"
        "每天 plan 至少 3 项。只输出 JSON。"
    ))
    user = HumanMessage(content=(
        f"目的地：{info['destination']}；预算：{info['budget']} 元；天数：{info['days']} 天。"
    ))
    resp = llm.invoke([prompt, user], response_format={"type": "json_object"})
    return {"itinerary": resp.content, "messages": [AIMessage(content=resp.content)]}


# ---------- 4. 定义路由（条件边） ----------
def route(state: TravelState) -> Literal["ask_node", "generate_node"]:
    return "ask_node" if missing_fields(state) else "generate_node"


# ---------- 5. 组装图 ----------
builder = StateGraph(TravelState)
builder.add_node("extract_node", extract_node)
builder.add_node("ask_node", ask_node)
builder.add_node("generate_node", generate_node)

builder.add_edge(START, "extract_node")
builder.add_conditional_edges(
    "extract_node",
    route,
    {"ask_node": "ask_node", "generate_node": "generate_node"},
)
builder.add_edge("ask_node", END)
builder.add_edge("generate_node", END)

memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)
```

### 6.3 运行：多轮对话演示

```python
config = {"configurable": {"thread_id": "travel-demo-001"}}

# 第一轮：信息不全，只给了目的地
graph.invoke({"messages": [HumanMessage(content="我想去北京玩")]}, config)
# 回复大概会问：你预算大概多少？打算玩几天？

# 第二轮：补齐天数，还差预算
graph.invoke({"messages": [HumanMessage(content="玩三天吧")]}, config)
# 回复：好的，那您预算大概多少呢？

# 第三轮：补齐预算，信息齐了 → 生成行程
final = graph.invoke(
    {"messages": [HumanMessage(content="预算三千左右")]},
    config,
)
itinerary = final["itinerary"]
print(itinerary)   # 结构化 JSON 行程
print(final["travel_info"])  # {'destination': '北京', 'budget': 3000, 'days': 3}
```

**运行逻辑回顾**：每轮都从 `START → extract` 开始 → `extract` 把新信息并入 `travel_info` → `route` 判断：没齐去 `ask` 追问然后 END 等用户；齐了去 `generate` 输出 JSON。因为有 checkpointer，第二轮开始时 `travel_info` 里还留着"北京"。

### 6.4 和你现有项目的对应关系

| 你现有项目（FastAPI + LangChain + DeepSeek） | 这个 LangGraph 示例中的对应物 |
|---|---|
| FastAPI 路由 / 每次请求单独处理 | `graph.invoke(..., config)` + `thread_id` |
| 手动拼接 `messages` 历史 | `messages` 字段 + `add_messages` 自动累积 |
| 自己写"缺什么就再问一次"的 if/else | `route` 条件边 |
| 单轮 `ChatPromptTemplate` 生成行程 JSON | `generate_node` + `response_format` |
| 无记忆（或 Session 存历史） | `InMemorySaver` / `RedisSaver` |
| `@tool` 调高德地图 | `ToolNode` + `tools_condition`（第 5 章） |

**升级到生产的样子**：
- 把 `InMemorySaver` 换成 `RedisSaver`（多实例共享、会话可持久）。
- `extract` / `ask` 之间可以再加一个 `route` 分支：用户说"改一下预算"，就用第 5 章的 `ToolNode` 调高德地图搜景点/酒店。
- 把 `invoke` 换成 `astream`（第 7 章）对接 FastAPI 的 SSE，实现打字机效果。

> ✅ **阶段四练习**：跑通 6.2 的完整代码。然后改造：把"天数"也拆成可选 + 追问；或加一个新字段 `interests`（偏好，如"美食/人文/亲子"），在 `generate_node` 里用上。过关标准：能独立说出"extract 是 LLM 抽取、route 是逻辑判断、ask/generate 是 LLM 生成"这条链路。

---

## 7. 流式输出 streaming

### 7.1 三种最常用的 stream_mode

`graph.stream()` 与 `graph.astream()` 返回一个迭代器，按"每个节点执行后"逐段产出。用 `stream_mode` 控制产出什么：

| 模式 | 产出内容 | 适用场景 |
|---|---|---|
| `"values"` | 每个节点后**完整的 State** | 调试、监控全状态 |
| `"updates"` | 每个节点后**该节点的输出**（字典，键=节点名） | 追踪每个节点干了什么 |
| `"messages"` | LLM 逐 token 的 `(token, 元数据)` | 聊天打字机效果 |

```python
from langchain_core.messages import HumanMessage

config = {"configurable": {"thread_id": "stream-demo"}}

# updates：看每个节点返回了什么
for event in graph.stream(
    {"messages": [HumanMessage(content="去杭州玩两天，预算两千")]},
    config,
    stream_mode="updates",
):
    print(event)
    # {'extract_node': {'travel_info': {...}}}
    # {'generate_node': {'itinerary': '{"days": [...', 'messages': [AIMessage(content=...)]}}

# messages：逐 token 输出（对接前端 SSE）
for event in graph.stream(
    {"messages": [HumanMessage(content="去杭州玩两天，预算两千")]},
    config,
    stream_mode="messages",
):
    token = event[0]            # token
    meta = event[1]             # 元数据
    print(token.content, end="", flush=True)
```

### 7.2 异步版 + FastAPI SSE 对接思路

FastAPI 里用 `astream`，配合 SSE（`StreamingResponse`）即可实现打字机：

```python
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

app = FastAPI()
# graph 与 config 需在外面准备好（含 checkpointer）

@app.post("/chat")
async def chat(message: str, thread_id: str = "default"):
    async def gen():
        async for event in graph.astream(
            {"messages": [HumanMessage(content=message)]},
            {"configurable": {"thread_id": thread_id}},
            stream_mode="messages",
        ):
            token = event[0]
            if token.content:
                yield f"data: {token.content}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")
```

> ✅ **阶段五练习**：把 6.2 的图分别用 `updates` 和 `messages` 两种模式各跑一次，观察输出差异。过关标准：能说出"聊天打字机效果该用哪个模式、为什么"。

---

## 8. 资源清单

### 8.1 官方文档（必看，以官方为准）

- **LangGraph 官方文档（Python）**：<https://docs.langchain.com/oss/python/langgraph/>
  - 概念讲解：<https://docs.langchain.com/oss/python/langgraph/concepts>
  - 流式输出：<https://docs.langchain.com/oss/python/langgraph/streaming>
- **LangGraph 主仓库（含 examples/ 目录）**：<https://github.com/langchain-ai/langgraph>
- **LangGraph 1.0 发布公告**：<https://www.langchain.com/blog/langchain-langgraph-1dot0>
- **langgraph-checkpoint-redis（PyPI）**：<https://pypi.org/project/langgraph-checkpoint-redis/>
- **PyPI 版本页（查最新稳定版）**：<https://pypi.org/project/langgraph/>

### 8.2 LangGraph Academy（官方免费课程，强烈推荐）

- 首页：<https://academy.langchain.com>
- GitHub 仓库：<https://github.com/langchain-ai/langchain-academy>
  - 建议学 **Module 0~3**（环境、LangGraph 基础、状态模式与持久化、流式与人在环路），与本文档阶段一~三对应。
  - 2025 年新增快速入门课 **LangGraph Essentials**（约 1 小时），适合复习。

### 8.3 免费中文教程 / 社区

- **LangGraph 中文文档站（社区翻译）**：<http://langgraph.com.cn>（含流式输出、ToolNode 等中文 how-to）
- **LangChain Academy 中文版（langchain-academy-zh）**：<https://github.com/yanlinpu/langchain-academy>（精简、降低国内环境门槛）
- **LangGraph-Mastery-Playbook**（六阶段实战手册，支持 DeepSeek）：<https://github.com/leslieo2/LangGraph-Mastery-Playbook>
- **腾讯云/百度云开发者社区**：搜 "LangGraph 对话历史记录"、"DeepSeek LangGraph Agent"，有大量中文实战文章
  - 例如《大模型开发实战：使用 LangGraph 为对话添加历史记录》：<https://cloud.tencent.cn/developer/article/2523070>

### 8.4 官方示例仓库（可直接改着用）

- **react-agent**（官方 ReAct 模板，含 graph.py 结构）：<https://github.com/langchain-ai/react-agent>
- **langgraph-example**（LangGraph Cloud 部署最小示例）：<https://github.com/langchain-ai/langgraph-example>
- **Agent Inbox 示例**（人在环路 / 中断审批）：<https://github.com/langchain-ai/agent-inbox-langgraph-example>
- 旅行相关开源项目（可对照你的项目）：
  - Yangjon1/trip_agent（LangGraph + 高德 MCP + FastAPI）：<https://github.com/Yangjon1/trip_agent>
  - SuperLuJC/PlannerAgent（LangGraph 多轮旅行助手，支持 DeepSeek）：<https://github.com/SuperLuJC/PlannerAgent>

### 8.5 书（可选，进阶）

- 《AI Agent 开发：零基础构建复合智能体》（清华大学出版社，2025），含 LangGraph 编排与多智能体实战。

---

## 9. 给"边学边做"的实习者的几点建议

1. **先跑通再深入**：把本文档 6.2 的完整代码跑起来，你就已经超过了"只会调 API"的入门水平。原理在跑的过程中自然就懂了。
2. **面试能讲清的三个点**：① State/Reducer/Checkpointer 三者的关系；② 条件边怎么实现"缺什么问什么"的循环；③ `stream_mode` 的 `values/updates/messages` 区别。这三个点是 LangGraph 岗位的高频考点。
3. **不要背 API，背模式**：LangGraph 的套路就是"定义 State → 写节点函数 → 加边 → compile → invoke/stream"。所有复杂应用都是这套模板的变体。
4. **对着自己的项目改**：每学一个概念，就想想它对应你现有旅行规划项目里的哪一块（见 6.4 的对照表），这样学得最快。
5. **版本以官方为准**：网上大量教程还停留在 0.x/0.2 写法。遇到"导入报错"，先检查版本，再去[官方文档](https://docs.langchain.com/oss/python/langgraph/)确认当前写法。

祝你一周上手，实习顺利。
