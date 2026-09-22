# Redis 从入门到能用：完全零基础新手版

> 面向对象：**完全零基础**——不知道什么是后端、什么是数据库、什么是内存、什么是缓存、什么是客户端/服务器，连 Docker 和命令行都没怎么用过，但愿意跟着教程一步步动手敲命令的同学。
> 使用场景：在「智旅云图」项目里用 Redis 做**聊天会话状态存储、攻略缓存、token 黑名单**。
> 学习方式：边学边做，每章有练习和"算过"标准。目标不是让你精通，而是**能看懂项目 + 能上手用 + 能去实习**。不读源码，只懂原理。
> 版本信息：本文基于 **Redis 8.x（当前最新稳定版 8.10，2026-07-29 GA）**。Redis 8 之后基础用法与 7.x 一致，本文内容同样适用于 7.x。
> 预计总时长：**1~2 周业余时间**（每天 2~3 小时）。别怕，第 0 章把所有前置概念都补上了。

---

## 目录

- [第 0 章 学前必备知识（完全新手篇）](#第-0-章-学前必备知识完全新手篇)
- [第 1 章 总览：分阶段学习路径](#第-1-章-总览分阶段学习路径)
- [第 2 章 阶段一：Redis 是什么？为什么快？](#第-2-章-阶段一redis-是什么为什么快)
- [第 3 章 阶段二：安装与启动 + redis-cli 上手](#第-3-章-阶段二安装与启动--redis-cli-上手)
- [第 4 章 阶段三：五种核心数据结构](#第-4-章-阶段三五种核心数据结构)
- [第 5 章 阶段四：TTL 过期时间与缓存三大问题](#第-5-章-阶段四ttl-过期时间与缓存三大问题)
- [第 6 章 阶段五：持久化 RDB / AOF（懂概念即可）](#第-6-章-阶段五持久化-rdb--aof懂概念即可)
- [第 7 章 阶段六：在 Spring Boot 中集成 Redis](#第-7-章-阶段六在-spring-boot-中集成-redis)
- [第 8 章 阶段七：结合本项目场景实战](#第-8-章-阶段七结合本项目场景实战)
- [第 9 章 资源清单](#第-9-章-资源清单)
- [附：常见新手问题速查](#附常见新手问题速查)

---

# 第 0 章 学前必备知识（完全新手篇）

这一章专门写给**完全零基础**的你。如果你之前完全没接触过后端开发，先花半天把它读完、做一遍，再进入阶段一。读完之后，你会具备理解 Redis 的最小背景知识。

## 0.1 内存 vs 硬盘：为什么"内存快"

**内存（RAM）** 和 **硬盘（Disk）** 都是电脑里能存数据的地方，但差别巨大。

打个比方：

- **硬盘**像一个**大仓库**。什么都能存，容量大、便宜，断电了东西也还在。但你要取东西，得跑到仓库去，翻箱倒柜，很慢。
- **内存**像你**手边的办公桌**。容量小、贵，一断电桌面就被"清空"了。但你想拿什么，伸手就能拿到，快得多。

所以：

- 你的照片、电影、文档，都存在**硬盘**上（关了电脑还在）。
- 你正在用的程序、正在算的数据，放在**内存**里（程序关了或断电就没了）。

速度差距有多大？内存的读写是**纳秒级**（十亿分之一秒），硬盘是**毫秒级**（千分之一秒）。看起来都是"一瞬间"，但毫秒是纳秒的一百万倍。**差好几个数量级**。

> 关键结论：**数据放在哪里，决定了读取速度。** 这是理解 Redis 为什么快的基石。

## 0.2 什么是数据库

**数据库（Database）** 就是一个专门用来**长期保存数据**的软件，你可以把它理解成一个**超级大的、会查会改的 Excel**。

我们平时自己存数据，用 Excel 表格。但网站的数据量很大（几百万用户、几万条攻略），而且要同时被很多人读写，Excel 扛不住。所以有了数据库软件，专门干这件事。

常见的数据库：

- **MySQL**：把数据存在**硬盘**上，安全可靠。本书后面提到的"数据库""DB""查库"基本都指它。
- **Redis**：本书主角，把数据存在**内存**里，飞快。但它"记性"没 MySQL 好，重启容易丢（后面阶段五会讲怎么让它尽量不丢）。

> 一句话区分：**MySQL 是"存重要业务数据的保险柜"，Redis 是"放高频读取数据的顺手货架"。**

## 0.3 什么是键值对（Key-Value）

**键值对**是最简单的一种数据结构，英文叫 **Key-Value**。用一个"钥匙（Key）"对应一个"值（Value）"。

想象一个**自助储物柜**：

- 每个柜子有一个编号（比如 `柜子 17`），这就是 **Key**。
- 柜子里放着你的包，这就是 **Value**。
- 你想拿东西，报出柜号，储物柜就帮你把东西拿出来。

或者想成**查字典**：你查一个字（Key），得到它的解释（Value）。

Redis 的核心操作就两条：

- `SET 钥匙 值`：把东西放进某个柜子。
- `GET 钥匙`：按柜号把东西取出来。

> 后面阶段三会讲到，Redis 里的"值"不只是简单的字串，还能是列表、集合、对象等更丰富的结构。但底层思想都是"一个钥匙 → 一个东西"。

## 0.4 什么是缓存，为什么需要缓存

**缓存（Cache）** 就是把"经常要读的东西"放在一个**更快的地方**，下次直接用，不用每次去慢的地方取。

生活例子：你经常要喝水。如果每次喝水都跑到楼下去买，很累。聪明做法是**在桌上放一杯水**。桌面上这杯水，就是"缓存"；楼下超市，就是"数据库"。水喝完（缓存过期）再去买。

网站也是这个道理。比如「智旅云图」的**景点攻略详情页**，一天被几百万人看。如果每次有人看，程序都去 MySQL（硬盘）里查一遍，MySQL 会非常累、响应变慢，甚至崩溃。

解决办法：把热门攻略**先放进 Redis（内存）里**。用户来看时，先查 Redis：

- Redis 里有（命中）：直接返回，飞快。
- Redis 里没有（未命中）：再去 MySQL 查，查到后顺手**在 Redis 里存一份**，下次就能命中。

这套"先查缓存，没查到再查数据库"的流程，是后面阶段四的重点，也是你实习时天天见的模式。

> 注意：缓存里存的是**数据库的副本**。副本可能和真身不一致（比如数据库改了，缓存还没更新），这就是后面要解决的"一致性"问题。新手阶段先用 TTL 过期时间让它自动刷新即可。

## 0.5 缓存三大问题的"直觉场景"

进阶教程里的"缓存穿透 / 击穿 / 雪崩"，听起来吓人，其实对应三个很朴素的生活场景。先有个直觉，术语留到阶段四详解：

- **穿透（Cache Penetration）**：一个人在超市问"有没有一种根本不存在的商品"，比如"火星矿泉水"。店员每次都去仓库翻，永远找不到，还白跑一趟。如果一堆人同时问不存在的东西，仓库（数据库）就被拖垮了。**问的是不存在的数据。**
- **击穿（Cache Breakdown）**：某款爆款商品正好在**最热闹的那一秒**下架了（缓存过期），所有顾客瞬间全冲去仓库问"还有没有？"，仓库被挤爆。**问的是存在的热点数据，但缓存恰好在高并发时失效。**
- **雪崩（Cache Avalanche）**：超市搞促销，一大批热门商品**同时卖完下架**（一大批 key 同时过期），顾客全部冲向仓库，仓库直接崩了。**大量 key 同时失效。**

先记着这三个画面，阶段四会教你对应的"怎么防"。

## 0.6 服务器 / 客户端 / 端口 / 6379

**服务器（Server）**：一台专门"提供服务"的电脑。它常年开机、等着别人来请求它。比如：

- 存放攻略数据的 MySQL 服务器；
- 提供 Redis 服务的 Redis 服务器（程序）；
- 你项目里的 Spring Boot 后端，跑起来后也是一台"本地服务器"。

**客户端（Client）**：主动"去请求服务"的一方。比如你的浏览器、`redis-cli` 工具、Spring Boot 程序，都算是客户端。一个"客户端问，服务器答"。

**端口（Port）**：一台电脑上可能同时跑很多服务（网页服务、Redis、MySQL……）。为了区分，每个服务占一个**门牌号**，这个号就叫端口。别人要访问某个服务，就要敲对门牌号。

- 网页服务默认门牌号是 `80`（或 `8080`）。
- **Redis 的默认门牌号是 `6379`**。看到 6379，就等于看到 Redis。

**localhost**：就是"本机"的意思。你代码里写 `localhost:6379`，意思是"连接本机的 6379 号门，也就是本机的 Redis"。

## 0.7 什么是 Docker，为什么用 Docker 跑 Redis

**Docker** 是一个"集装箱"工具。它能把一个软件**连同它需要的运行环境一起打包**，放到一个叫**容器（Container）**的隔离盒子里，一条命令就能启动。

打个比方：

- **不用 Docker**：要装 Redis，你得手动下载安装包、配置依赖、设成系统服务……步骤多，还容易污染电脑（装了一堆东西删不干净）。
- **用 Docker**：像在手机上装 App——你只需要下载一个"Redis 应用"（叫**镜像（Image）**），点一下（一条命令）就装好并运行了。不用了，删除即可，不留垃圾。

**为什么本项目推荐用 Docker 跑 Redis**：

1. **干净**：容器隔离，不会把电脑弄得一团糟。
2. **一致**：Docker 里跑的 Redis 和你公司 Linux 服务器上跑的一模一样，避免"我电脑上好好的，服务器上跑不起来"。
3. **省心**：一条命令搞定安装启动，卸载也干净。

### Windows 上安装 Docker Desktop 的步骤

1. 用浏览器打开 Docker 官网下载页：<https://www.docker.com/products/docker-desktop/>
2. 点 **Download for Windows** 下载安装包（约几百 MB）。
3. 双击安装包。在安装向导里，勾选 **Use WSL 2 instead of Hyper-V**（推荐默认勾选）。
4. 如果安装时提示"未启用 WSL2"，请先以管理员身份打开 PowerShell，执行 `wsl --install`，然后按提示重启电脑，再重新安装 Docker Desktop。
5. 装完后，桌面上出现 **Docker Desktop** 图标，双击启动。等它的图标（一条鲸鱼）稳定不再转圈，就说明 Docker 引擎起来了。
6. 验证安装是否成功：打开终端（见 0.8），输入：

```bash
docker --version
```

能看到版本号，说明装好了。再跑一条最经典的验证命令：

```bash
docker run hello-world
```

如果终端打印出一段欢迎文字，说明 Docker 完全正常。

> 提示：Docker Desktop 启动后，图标是"静止的鲸鱼"才表示可用；如果图标一直在动或报错，点开它看提示，多半是 WSL2 没启或电脑没开"虚拟化"（Intel VT-x / AMD-V，一般新电脑默认已开启）。

## 0.8 什么是终端 / 命令行，Windows 常用命令

**终端（Terminal）/ 命令行** 是一个让你**用键盘打字来指挥电脑**的窗口，而不是用鼠标点图标。

很多教程用终端操作，是因为：

- 有些工具（比如 `redis-cli`）只有命令行版；
- 打字命令可以复制粘贴、可以写进脚本，比点鼠标快得多、也更容易说清楚。

### Windows 上怎么打开终端

三种方式任选其一：

- 按 `Win + R`，输入 `cmd`，回车。
- 在开始菜单搜 **PowerShell**。
- 用 VS Code 写代码时，菜单栏选 **终端 → 新建终端**（很多教程用这个）。

### Windows 最常用命令（零基础必会）

| 命令 | 作用 | 例子 |
|---|---|---|
| `dir` | 列出当前文件夹里的内容 | `dir` |
| `cd 文件夹名` | 进入某个文件夹 | `cd C:\Users\20243\Desktop` |
| `cd ..` | 返回上一级文件夹 | `cd ..` |
| `mkdir 名字` | 新建文件夹 | `mkdir my-redis` |
| `cls` | 清空屏幕 | `cls` |
| `docker --version` | 查看 Docker 版本，验证安装 | `docker --version` |
| `ping 127.0.0.1` | 测试本机网络通不通 | `ping 127.0.0.1` |

> 提示：命令行里的"斜杠"是反斜杠 `\`，路径里文件夹之间用 `\` 隔开，例如 `C:\Users\20243`。在 Linux/Mac 上才用 `/`。另外，终端里回车键就是"执行这句话"。

## 0.9 "Spring Boot 集成 Redis"是怎么一回事

**Spring Boot** 是一个用 **Java** 语言写"网站后端程序"的框架（框架 = 别人写好的半成品积木，你拿来拼出自己的程序）。它负责接收前端请求、处理业务、和数据库打交道。

**集成 Redis** 的意思是：**让你的 Spring Boot 程序能连接并使用 Redis**。

直觉上这件事分三步：

1. 在 Spring Boot 项目里加一个"Redis 连接库"（叫依赖，见阶段六）。
2. 在配置文件里告诉它 Redis 在哪：`localhost:6379`（本机 + 端口）。
3. 在代码里用一行行 Java 代码读写 Redis（比如 `redisTemplate.opsForValue().set(...)`）。

做完这三步，你的 Java 程序就能"像用 redis-cli 一样"操作 Redis 了。区别是：`redis-cli` 是你在终端里**手动**敲命令，而集成后是**程序自动**执行这些操作。

> 类比：redis-cli 像你手动开锁取货；Spring Boot 集成像给程序装了一个"自动存取货"的机械臂，程序里调用一下，它就替你开锁取货。

## 0.10 Redis 在「智旅云图」项目里具体干什么

看项目前先知道 Redis 在这里的**三个用途**（阶段七会展开）：

1. **存聊天会话状态**：用户在对话式规划里和 AI 多轮聊天，聊到一半的上下文（历史消息、状态）存进 Redis。下次用户再说一句话，能接得上。
2. **缓存攻略**：热门景点攻略详情被反复访问，放进 Redis 缓存，减轻 MySQL 压力。
3. **token 黑名单**：用户退出登录时，把他的登录凭证（token）记进 Redis 黑名单，让它立刻失效。

## 0.11 第 0 章练习与"算过"标准

**小练习**：

1. 用自己的话写出：内存和硬盘有什么区别？为什么 Redis 放内存就快？
2. 用"储物柜"或"字典"的例子，给一个不懂编程的人解释什么是键值对。
3. 打开终端，用 `dir`、`cd`、`mkdir` 三个命令各操作一次。
4. 安装 Docker Desktop 并跑通 `docker run hello-world`。

**算过标准**：能不用看笔记，对朋友讲清楚"内存 vs 硬盘""键值对""缓存是干嘛的"这三个概念；Docker 能成功跑起一个容器。

---

# 第 1 章 总览：分阶段学习路径

| 阶段 | 内容 | 预计耗时（零基础） | 学到什么程度"算过" |
|---|---|---|---|
| 阶段一 | Redis 是什么、为什么快 | 1 天 | 能用自己的话讲出"内存 + 单线程 + IO 多路复用"三个原因 |
| 阶段二 | 安装启动 + redis-cli | 2 天 | 能用 Docker 跑起 Redis，会用 redis-cli 敲命令，能 `PING` 通 |
| 阶段三 | 五种核心数据结构 | 4~5 天 | 每种结构至少能写出一个真实场景例子，能用 redis-cli 完成增删改查 |
| 阶段四 | TTL + 缓存三大问题 | 2~3 天 | 能说清穿透/击穿/雪崩是什么、各自怎么防 |
| 阶段五 | 持久化 RDB / AOF | 1 天 | 能说清 RDB 和 AOF 的区别、各自适用场景 |
| 阶段六 | Spring Boot 集成 | 4~5 天 | 能自己搭一个 Redis 缓存 demo，会用 RedisTemplate 和 @Cacheable |
| 阶段七 | 结合本项目实战 | 3~4 天 | 能画出聊天会话状态、景点攻略缓存、token 黑名单的存取流程 |

**总时长约 1~2 周业余时间**（每天 2~3 小时，或工作日每晚 1.5~2 小时 + 周末集中）。每个阶段后面都有"独立小练习"，做完练习、能答出"算过标准"即可进入下一阶段，不必贪快。

---

# 第 2 章 阶段一：Redis 是什么？为什么快？

## 2.1 Redis 是什么

Redis（**RE**mote **DI**ctionary **S**erver，中文直译"远程字典服务器"）是一个**基于内存**的开源**键值数据库**。它把数据存在**内存**里（第 0 章说过，内存快），所以读写非常快；同时它支持把数据**保存到硬盘**（持久化），重启后不丢。

一句话定位：Redis 是一个**速度极快的内存数据结构存储系统**，常用作：

- **缓存**：把频繁读的数据放进去，减少数据库压力（最常见用途）
- **会话存储**：登录状态、聊天会话上下文
- **消息队列**：基于 List / Stream 做简单的发布订阅和队列
- **计数器 / 排行榜**：利用原子自增和有序集合

> 中文资料里常把它叫"缓存数据库"，但注意它不只是缓存——它本身也是一个数据库，只是常被拿来当缓存用。

## 2.2 为什么快：三个核心原因

对新手来说，不需要深入源码，但要能讲清楚"为什么快"这三点：

**原因一：数据在内存中**
Redis 的数据存在 RAM（内存）里，而 MySQL 等传统数据库的数据主体在硬盘上。内存的读写速度比硬盘快几个数量级（纳秒级 vs 毫秒级，见 0.1）。这是它快的最根本原因。

**原因二：单线程模型，避免了锁和上下文切换**
Redis 的**核心命令执行是单线程**的（一个线程依次处理所有客户端请求）。"线程"可以理解成干活的人；单线程 = 只有一个人干活，但这个人足够快。

单线程的好处是：没有多线程并发时的**锁竞争**和**上下文切换**开销（多个人抢同一把钥匙、来回换人的成本），也天然不会出现"多个线程同时改一个数据"的打架问题，所以单个命令的执行是**原子**的（一个命令要么完整做完、要么完全不做，中间不会被插队）。这也是 `INCR` 这种"读-改-写"操作能保证不出一丝差错的原因。

> 补充一点（2025 年后的小变化）：Redis 8.0 引入了可选的 I/O 多线程（`io-threads`），网络读写可以由多线程分担，但**核心命令执行仍是单线程**。对初学者，请记住"命令执行单线程"即可，面试也主要考这个。

**原因三：IO 多路复用**
Redis 用事件循环 + **IO 多路复用**机制（底层基于 epoll / kqueue，这是操作系统提供的"同时盯很多连接"的能力）同时监听成千上万个客户端连接。它不需要为每个连接开一个线程，而是"一个线程同时看很多个连接，谁有数据来了就处理谁"，极大地降低了并发连接的开销。

> 简单类比：单线程服务员一次只服务一桌，但能同时盯着整个大厅，哪桌客人举手（有请求）就过去服务。比起"每桌一个服务员"，省了大量人力和排队协调成本。

## 2.3 阶段一小练习

- 用自己的话（中文）写出：Redis 是什么、为什么快。
- 把"单线程"和"原子性"的关系写清楚：为什么单线程执行能保证一个命令的原子性。
- 想一想：MySQL 把数据存在硬盘，Redis 把数据存在内存。那么一个查询接口，先查 Redis 和直接查 MySQL，哪个更快？为什么？（答案：先查 Redis 快，因为内存比硬盘快。）

**算过标准**：不看资料能口述出"内存、单线程、IO 多路复用"这三点。

---

# 第 3 章 阶段二：安装与启动 + redis-cli 上手

## 3.1 重要背景：Windows 上没有"官方原生版"

Redis 官方**不维护 Windows 原生版本**。微软曾移植过一个 Windows 版（停留在 3.2 时代，2016 年后不再更新，有安全漏洞，**不要用**）。

所以在 Windows 上跑 Redis，主流有 3 种方案，从"最推荐给本项目"排序：

| 方案 | 复杂度 | 说明 | 适用 |
|---|---|---|---|
| **Docker Desktop** | 中 | 拉官方镜像 `redis:alpine`，一条命令跑起来 | 本项目首选，环境干净、和 Linux 生产一致 |
| **WSL2** | 中 | 在 WSL2 里装 Linux 版 Redis，官方推荐路线 | 已用 WSL 做开发的同学 |
| **Memurai** | 低 | Redis 官方认可的 Windows 原生替代品，装个 MSI 就行 | 不想装 Docker/WSL，就想本地快点跑 |

> 结论：**本项目统一用 Docker 跑 Redis**。下面详细讲 Docker 方案，附带 Memurai 备用方案。如果你在第 0 章已经装好 Docker Desktop，直接进入 3.2。

## 3.2 方案 A：Docker 跑 Redis（本项目推荐）

前提：已安装 Docker Desktop 并启动（见 0.7）。

拉镜像并启动一个名为 `my-redis` 的容器，把宿主机的 `6379` 端口映射到容器：

```bash
docker run --name my-redis -p 6379:6379 -d redis:alpine
```

这条命令拆开看：

- `--name my-redis`：给这个容器起个名字，叫 `my-redis`。
- `-p 6379:6379`：把电脑（宿主机）的 6379 号门和容器里的 6379 号门打通，这样外面访问本机 6379 就进到容器里的 Redis。
- `-d`：后台运行（别占着终端）。
- `redis:alpine`：用哪个镜像。`alpine` 是一个极简版 Linux，镜像很小。

验证容器在跑：

```bash
docker ps                     # 看到 my-redis 在 UP 状态即可
docker logs my-redis          # 看到 "Ready to accept connections" 说明启动成功
```

常用运维命令：

```bash
docker stop my-redis          # 停止
docker start my-redis         # 再次启动（数据还在，前提见阶段五持久化）
docker rm my-redis            # 删除容器（注意：不带 -v 不删数据卷）
```

> 关于数据持久化：`docker run` 不挂数据卷时，容器删除后数据会丢。阶段五会讲 Redis 自己的 RDB/AOF 持久化，练习阶段可以先不挂卷，但要意识到这一点。更规范的做法是挂载一个数据卷：`-v redis-data:/data`。

## 3.3 方案 B：Memurai（Windows 原生，备用）

Memurai 是 Redis 官方认可的 Windows 原生实现（与 Redis 7.2.6 API 兼容），官方在 redis.io 上有专门教程。从 memurai.com 下载 Developer Edition（免费，仅限开发用，每运行 10 天需重启服务）。

```bash
net start memurai             # 启动 Windows 服务
memurai-cli ping              # 测试，返回 PONG 即成功
```

## 3.4 用 redis-cli 做最基本的操作

**redis-cli** 是 Redis 自带的"命令行客户端"工具，可以理解成**连接 Redis 用的对讲机**——你在终端里敲命令，Redis 那边执行并回话。

进入 redis-cli（如果用 Docker，需要先进容器或使用 `docker exec`）：

```bash
redis-cli                     # 本机直连，默认 localhost:6379
docker exec -it my-redis redis-cli   # 在容器内执行
```

> 提示：如果中文显示乱码，用 `redis-cli --raw` 启动即可正常显示中文。

依次敲下面命令感受一下（`PING`、字符串、键存在、过期）：

```bash
PING                 # 返回 PONG，确认连接正常
SET name zhilv       # 设置一个字符串键
GET name             # 读取，返回 "zhilv"
EXISTS name          # 键是否存在，返回 1
DEL name             # 删除键
TTL name             # 查看剩余过期时间（秒），-1 表示永不过期
KEYS *               # 列出所有键（仅限测试环境用，生产禁止！）
FLUSHALL             # 清空所有数据（危险命令，练习用，生产禁止！）
```

`help` 命令可以随时看某个命令的用法：

```bash
help set
help @string          # 查看 string 类型的所有命令
```

> **安全提醒**：`KEYS *` 在生产环境会阻塞 Redis，绝对不能用于生产；这里只在本地练习时玩一玩。

## 3.5 阶段二小练习

1. 用 Docker 把 Redis 跑起来，`PING` 返回 `PONG`。
2. 依次执行 `SET` / `GET` / `DEL` / `TTL` / `EXISTS`，确认每一条命令的返回。
3. 用 `SET key value EX 60` 设置一个 60 秒后过期的键，观察 `TTL` 倒数。

**算过标准**：能不看笔记，在 5 分钟内用 Docker 启动 Redis 并用 redis-cli 完成"写入、读取、删除、设过期"四个操作。

---

# 第 4 章 阶段三：五种核心数据结构

Redis 有 5 种最核心的数据结构：**string（字符串）、hash（哈希）、list（列表）、set（集合）、zset（有序集合）**。前面第 0 章说过键值对，这一章的每一种结构，都是"一个 key 对应一种更丰富的 value 形态"。

> Redis 8 之后还内置了 JSON、TimeSeries、BloomFilter 等更多结构，但**初学先掌握这五种就够用**。集群、哨兵先不学。

学习每种结构时，记住三件事：**长什么样 → 支持什么命令 → 用在哪（真实场景）**。

## 4.1 String 字符串 —— 最基础、最常用

**长什么样**：一个 key 对应一个字符串（可以是文本、数字、二进制序列化数据）。

**核心命令**：

```bash
SET key value            # 设置
GET key                  # 读取
SET key value EX 60      # 设置并指定 60 秒过期（等价于 SETEX key 60 value）
MSET a 1 b 2             # 批量设置
MGET a b                 # 批量读取
INCR counter             # 自增 1（原子操作！）
DECR counter             # 自减 1
INCRBY counter 10        # 自增 10
APPEND key str           # 追加
STRLEN key               # 字符串长度
```

**真实场景**：

- **会话状态 / 简单缓存**：`SET session:user123 tokenvalue EX 3600`——把登录态或聊天会话的 JSON 快照存起来，带过期时间。
- **计数器**：`INCR page:view:20260830`——点赞数、浏览量、访问统计。因为单线程 + 原子操作，多个请求并发 `INCR` 也不会出错，这比在 MySQL 里先查后改更省事。
- **分布式 ID / 验证码**：`SET phone:138xxxx1234 889932 EX 300`——短信验证码，5 分钟过期。

## 4.2 Hash 哈希 —— 存"对象"最合适

**长什么样**：一个 key 下面有多个 field-value 对，像一个 Java 对象（第 0 章的"储物柜"升级版：一个柜子里面还分了好几个小格子，每个格子有标签）。

**核心命令**：

```bash
HSET user:1 name "张三" age 25
HGET user:1 name          # 取单个字段
HGETALL user:1            # 取所有字段
HMGET user:1 name age     # 取多个字段
HLEN user:1               # 字段数量
HINCRBY user:1 age 1      # 某字段自增
HDEL user:1 age           # 删除字段
```

**真实场景**：

- **存对象**：用户信息 `user:1001` 下的 `name`、`avatar`、`level` 字段。和 string 存整段 JSON 相比，hash 的好处是**可以只改某个字段**，不用整段读改写。
- **聊天会话状态（本项目场景）**：一个会话 `session:{chatId}` 下挂 `history`（对话历史 JSON）、`user_id`、`created_at`、`mode`（模式）等字段，取用方便。**详见阶段七。**

> 对比记忆：string 存"一整坨"，hash 存"一个对象的多个属性"。

## 4.3 List 列表 —— 有序的队列

**长什么样**：一个 key 对应一个有序的字符串列表，可以从头或尾插入/弹出。"弹"可以理解成"取出并拿掉"。

**核心命令**：

```bash
LPUSH queue task1        # 从左边（头部）压入
RPUSH queue task1        # 从右边（尾部）压入
LPOP queue               # 从左边弹出
RPOP queue               # 从右边弹出
LRANGE queue 0 -1        # 取整个列表
LLEN queue               # 列表长度
BLPOP queue 5            # 阻塞式弹出，等 5 秒，无数据则超时（做队列常用）
```

**真实场景**：

- **简单的消息队列 / 任务队列**：`RPUSH` 放任务，`BLPOP` 阻塞取任务——生产者和消费者模式。
- **最新动态 / 时间线**：`LPUSH` 往头部推，`LRANGE 0 9` 取最近 10 条。
- **注意**：Redis 的 List 能做轻量队列，但功能远不如专业 MQ（RocketMQ / RabbitMQ / Kafka）。本项目的消息队列后续如果做，先可以用 List/Stream 顶一下，**不要指望它做复杂路由、消息回溯、死信队列**。

## 4.4 Set 集合 —— 自动去重、交并差

**长什么样**：一个 key 对应一个**无序、自动去重**的字符串集合。去重 = 同一个元素加两次，也只算一个。

**核心命令**：

```bash
SADD tags "美食" "夜景" "人文"     # 添加
SMEMBERS tags                    # 取所有元素
SISMEMBER tags "美食"             # 判断是否在集合中，返回 1/0
SREM tags "美食"                  # 删除元素
SCARD tags                       # 元素个数
SINTER set1 set2                 # 交集
SUNION set1 set2                 # 并集
SDIFF set1 set2                  # 差集
```

**真实场景**：

- **标签 / 兴趣**：景点标签、用户关注列表，天然去重。
- **共同好友 / 共同关注**：`SINTER` 一次算出两个集合的交集。
- **签到 / 已读去重**：`SADD` 记录已处理的事件 ID，防止重复处理。

## 4.5 ZSet 有序集合 —— 排行榜神器

**长什么样**：和 Set 一样是去重集合，但**每个元素带一个分数（score）**，Redis 按分数自动排序。

**核心命令**：

```bash
ZADD leaderboard 100 "用户A" 98 "用户B" 95 "用户C"
ZINCRBY leaderboard 2 "用户C"       # 给用户C 加 2 分
ZRANGE leaderboard 0 9 WITHSCORES   # 分数从低到高取前 10
ZREVRANGE leaderboard 0 9 WITHSCORES # 分数从高到低取前 10（排行榜常用）
ZSCORE leaderboard "用户A"          # 查某用户分数
ZRANK leaderboard "用户B"           # 查某用户排名（0 起）
ZREM leaderboard "用户A"            # 删除
```

**真实场景**：

- **排行榜**：热销榜、积分榜、阅读量榜。`ZINCRBY` 加分，`ZREVRANGE` 取榜单。
- **热门景点攻略（本项目场景）**：把景点按"热度分"存进 zset，取 `ZREVRANGE 0 9` 就是热点榜。
- **延时任务**：用时间戳当 score，`ZRANGEBYSCORE` 取出到期任务（进阶，先了解）。

## 4.6 五结构速查表

| 结构 | 一句话描述 | 最典型场景 | 本项目会用在哪 |
|---|---|---|---|
| String | 单个 key → 一个值 | 缓存、计数器、验证码 | 缓存攻略 JSON、浏览量 |
| Hash | 一个 key → 多个字段 | 存对象 | 聊天会话状态（多字段） |
| List | 有序列表 | 队列、时间线 | 轻量消息队列（后续） |
| Set | 去重集合 | 标签、共同关注 | 用户收藏的景点集合 |
| ZSet | 带分数排序集合 | 排行榜、热点榜 | 热门景点攻略榜 |

## 4.7 阶段三小练习

1. 用 redis-cli 把五种结构各存一组数据，并完成读、改、删。
2. 用 ZSet 实现一个小排行榜：给自己班 5 个同学加积分，用 `ZREVRANGE` 排出名次。
3. 用 Hash 模拟存"一个用户"，包含姓名、年龄、简介三个字段，并只修改年龄字段。

**算过标准**：能不看表说出每种结构的"一句话特点 + 一个真实场景"，并能用 redis-cli 熟练完成增删改查。

---

# 第 5 章 阶段四：TTL 过期时间与缓存三大问题

## 5.1 过期时间 TTL（Time To Live）

**TTL（Time To Live，存活时间）** 是 Redis 做缓存的关键特性：**给 key 设置一个存活时间，到期自动删除**。就像第 0 章"桌上那杯水"，喝完（过期）就没了，下次再倒。

```bash
SET cache:guide:1 "攻略内容" EX 3600    # 1 小时后过期
TTL cache:guide:1                       # 查看剩余秒数，-1 永不过期，-2 不存在/已过期
PERSIST cache:guide:1                   # 去掉过期时间（让它永不过期）
EXPIRE cache:guide:1 60                 # 给已存在的 key 追加过期时间
```

为什么必须有 TTL？

- **防止脏数据长期存在**：攻略内容改了，旧缓存自动过期后能读到新的。
- **防止内存被撑爆**：不带 TTL 的缓存只增不减，最终把内存占满。

## 5.2 缓存的基本读写模型

先理解"用缓存保护数据库"的经典流程（英文叫 read-through，直译"读穿"）：

```
请求来了
  → 先查 Redis（缓存）
     → 命中：直接返回（极快）
     → 未命中：查 MySQL → 把结果写回 Redis（带 TTL）→ 返回
```

用 redis-cli 手工模拟一遍：

```bash
# 第一次请求（缓存未命中，走数据库，然后写回缓存）
SET guide:1 "景点攻略正文" EX 600

# 第二次请求（缓存命中）
GET guide:1
```

## 5.3 缓存三大经典问题：穿透 / 击穿 / 雪崩

这是实习面试高频题，也是理解缓存容错的关键。三者区别记住一句话：**穿透查的是"不存在"的数据，击穿是"一个热点 key 过期"被打穿，雪崩是"大量 key 同时过期"把 DB 打崩。**（第 0 章 0.5 节已经给了生活画面，现在对号入座。）

### 问题一：缓存穿透（Cache Penetration）

**是什么**：请求查询一个**数据库中根本不存在**的数据（比如恶意构造 `id=-1` 或随机不存在的 ID）。缓存永远不可能命中，每次请求都直接打到数据库，数据库压力骤增。

**怎么防**：

1. **缓存空值**：查不到数据时，也往 Redis 写一个空对象/特殊标记，TTL 设短一点（2~5 分钟）。这样同一个不存在的 key 第二次请求就命中缓存，不会再到 DB。
2. **布隆过滤器**（了解即可）：请求先过一个"可能存在"的过滤器，判定"一定不存在"的直接拦截。对入门阶段，先知道"有这东西"，本项目的量级用"缓存空值"就够。

### 问题二：缓存击穿（Cache Breakdown）

**是什么**：一个**特别热门的 key**（比如秒杀商品、爆款文章）刚好在**高并发瞬间过期**，于是那一瞬间大量请求同时落到数据库，把 DB 打穿。注意：这个数据**是存在的**，只是缓存恰好失效。

**怎么防**：

1. **互斥锁（Mutex）**：回源查库前先抢锁，只有一个线程去查库并重建缓存，其他线程等待或返回旧值。"锁"可以理解成"只有一把钥匙，谁拿到谁去查库"。
2. **逻辑过期**（了解）：key 不设物理过期，value 里自己存一个过期时间戳，过期后后台异步刷新，读请求先返回旧值。适合容忍短暂旧数据的场景。
3. **`@Cacheable(sync = true)`**：Spring 里开启同步，本质上也是加锁防击穿，阶段六会提到。

### 问题三：缓存雪崩（Cache Avalanche）

**是什么**：**大量 key 在同一时刻集体过期**（比如同一批数据都设了 1 小时 TTL），或 Redis 服务宕机，导致大批请求同时落到数据库，数据库直接崩掉。

**怎么防**：

1. **TTL 加随机偏移**：设置过期时间时，在基础值上加一个随机数（如 `3600 + random(0~600)` 秒），让 key 分散过期，不要整点集体失效。**这是最常用、最简单的方案。**
2. **Redis 高可用**（本阶段不做，知道存在即可）：主从 + 哨兵 / Cluster，避免 Redis 单点宕机。
3. **多级缓存 / 熔断降级**（了解）：本地缓存 Caffeine + Redis + DB 多层拦截；DB 扛不住时降级返回兜底数据。

## 5.4 阶段四小练习

1. 用 redis-cli 演示：设 10 个 key，TTL 各不相同（模拟随机偏移），用 `TTL` 观察。
2. 用手绘或文字画出"缓存穿透"和"缓存雪崩"的请求流程图，标出 DB 压力点。
3. 把三种问题的"触发条件 / 影响范围 / 解决方案"各写一行，做成对比表。

**算过标准**：能对面试官讲清楚三者的区别，并至少说出每个问题一种解决方案。

---

# 第 6 章 阶段五：持久化 RDB / AOF（懂概念即可）

Redis 是内存数据库（数据放内存），如果不做持久化，重启后内存里的数据全丢。**持久化（Persistence）** 就是"把内存里的数据想办法保存到硬盘上"，这样重启后能恢复。Redis 提供两种持久化机制，**可以只理解概念，不要求会调优**。

## 6.1 RDB（快照，Snapshot）

**是什么**：在指定时间间隔内，把内存中的全部数据**拍一张快照存到磁盘**（一个 `.rdb` 文件）。快照 = 那一刻的完整截图。

**特点**：

- 文件紧凑、恢复速度快（直接把快照加载进内存）。
- 它是**周期性**的，不是实时的——两个快照之间的数据如果宕机就会丢。
- 适合对数据一致性要求不高、但追求恢复速度的场景（比如缓存数据）。

## 6.2 AOF（Append Only File，追加日志）

**是什么**：把**每一条写命令**以日志形式追加到文件里。Redis 重启时，**重放这些命令**来恢复数据。可以理解成"记账本"：每次操作都记一笔，重启后照着账本重做一遍。

**特点**：

- 数据更安全，丢失窗口小（取决于 `appendfsync` 刷盘策略，可选每秒/每命令/交给系统）。"刷盘"= 把内存里的日志真正写进硬盘。
- 文件比 RDB 大，恢复速度相对慢。

## 6.3 两者怎么选 / 能不能一起用

- **可以同时开启**：实际生产常用"AOF + RDB"结合——RDB 负责快速恢复，AOF 负责减少丢失。Redis 重启时会优先用 AOF 恢复（数据更完整）。
- **对新手记住三点**：RDB 是"定时快照"、AOF 是"实时日志"；RDB 恢复快但可能丢数据、AOF 丢得少但文件大恢复慢；Redis 默认开启了 RDB，可以两者一起开。

> 本项目里 Redis 主要存聊天会话状态和缓存，**会话状态建议开持久化**（AOF），这样服务重启后聊天上下文不丢；纯缓存数据丢了也无所谓，让缓存自己重建。

## 6.4 阶段五小练习

1. 写一句自己的话，分别解释 RDB 和 AOF 是什么、各有什么优点和缺点。
2. 在 Docker 里给 Redis 挂上数据卷重启一次，确认数据还在（体会持久化的作用）。

**算过标准**：能说清"RDB 是快照、AOF 是日志"以及各自适用场景，不要求会配置调优。

---

# 第 7 章 阶段六：在 Spring Boot 中集成 Redis

这是本项目后端（Spring Boot）部分的核心。目标：**在 Spring Boot 里既能用 RedisTemplate 精细操作，也能用 @Cacheable 声明式缓存。**（忘了 Spring Boot 集成是什么的，回看第 0 章 0.9 节。）

## 7.1 加依赖

**依赖（Dependency）** 可以理解成"别人写好的功能包"。在 `pom.xml` 中加入（Spring Boot 会自动使用 Lettuce 作为 Redis 客户端，支持连接池和异步）：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
<!-- 用 @Cacheable 注解时需要缓存抽象 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>
```

## 7.2 配置连接（application.yml）

注意：Spring Boot 3.x 中配置前缀是 `spring.data.redis`（Boot 2.x 是 `spring.redis`）。

```yaml
spring:
  data:
    redis:
      host: localhost
      port: 6379
      password:            # 没设密码就不写
      database: 0          # 默认 0；测试时可开多个库做隔离
      timeout: 2000
      lettuce:
        pool:
          max-active: 8    # 连接池（可选）
          max-idle: 8
```

> 验证是否连上：项目启动后调用一个 Redis 操作，或临时写一个 `CommandLineRunner` 打印 `redisTemplate.getConnectionFactory()`。

## 7.3 配置序列化（非常重要，跳过会踩大坑）

**序列化（Serialization）**：把内存里的对象变成一串能存进 Redis 的字节；**反序列化**：再变回对象。好比把一堆东西打包成快递（序列化），收到后拆包还原（反序列化）。

**问题**：Spring 默认的 `RedisTemplate` 用 JDK 序列化，存到 Redis 里的是一坨不可读的二进制，占用大、还可能反序列化报错。**入门阶段推荐**：

- **Key 用 String 序列化**（可读、直观）
- **Value 用 JSON 序列化**（可读、跨语言通用）

写一个配置类：

```java
package com.example.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

@Configuration
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);

        // key 用 String 序列化
        StringRedisSerializer stringSerializer = new StringRedisSerializer();
        template.setKeySerializer(stringSerializer);
        template.setHashKeySerializer(stringSerializer);

        // value 用 JSON 序列化
        GenericJackson2JsonRedisSerializer jsonSerializer = new GenericJackson2JsonRedisSerializer();
        template.setValueSerializer(jsonSerializer);
        template.setHashValueSerializer(jsonSerializer);

        template.afterPropertiesSet();
        return template;
    }
}
```

> 入门提示：操作纯字符串时直接用 Spring 自带的 `StringRedisTemplate`，不用自己配置序列化，最省心。上面这个配置是为了让你能存"对象"。

## 7.4 用 RedisTemplate / StringRedisTemplate 操作数据

`StringRedisTemplate` 适合存字符串；`RedisTemplate<String, Object>` 适合存对象（配了 JSON 序列化后）。

```java
@Service
public class GuideCacheService {

    // StringRedisTemplate：只存字符串，最简单
    private final StringRedisTemplate stringRedisTemplate;

    // RedisTemplate：配了 JSON 序列化后可以存对象
    private final RedisTemplate<String, Object> redisTemplate;

    public GuideCacheService(StringRedisTemplate stringRedisTemplate,
                             RedisTemplate<String, Object> redisTemplate) {
        this.stringRedisTemplate = stringRedisTemplate;
        this.redisTemplate = redisTemplate;
    }

    /** 存字符串，带 10 分钟过期 */
    public void saveGuide(String guideId, String json) {
        stringRedisTemplate.opsForValue()
                .set("guide:" + guideId, json, Duration.ofMinutes(10));
    }

    /** 读字符串 */
    public String getGuide(String guideId) {
        return stringRedisTemplate.opsForValue().get("guide:" + guideId);
    }

    /** 存对象（自动 JSON 序列化） */
    public void saveGuideObject(String guideId, Guide guide) {
        redisTemplate.opsForValue()
                .set("guide:" + guideId, guide, Duration.ofMinutes(10));
    }

    /** 手动查缓存，未命中则查库并回填（这就是 5.2 的 read-through 模型） */
    public Guide getGuideWithFallback(String guideId) {
        String key = "guide:" + guideId;
        Guide cached = (Guide) redisTemplate.opsForValue().get(key);
        if (cached != null) {
            return cached;
        }
        // 未命中 → 查数据库（这里略）→ 回填
        Guide guide = guideRepository.findById(guideId).orElse(null);
        if (guide != null) {
            redisTemplate.opsForValue().set(key, guide, Duration.ofMinutes(10));
        }
        return guide;
    }

    /** 删除缓存 */
    public void deleteGuide(String guideId) {
        stringRedisTemplate.delete("guide:" + guideId);
    }
}
```

每种数据结构的操作方法（对应阶段三的 redis-cli 命令）：

| Redis 结构 | Java 操作入口 | 示例 |
|---|---|---|
| String | `opsForValue()` | `opsForValue().set(k, v, Duration)` |
| Hash | `opsForHash()` | `opsForHash().put(key, field, value)` |
| List | `opsForList()` | `opsForList().leftPush(key, value)` / `rightPop(key)` |
| Set | `opsForSet()` | `opsForSet().add(key, value)` |
| ZSet | `opsForZSet()` | `opsForZSet().add(key, value, score)` / `reverseRange(key, 0, 9)` |

## 7.5 用 @Cacheable 等注解做声明式缓存

**先开启缓存**：在启动类上加上 `@EnableCaching`。

```java
@SpringBootApplication
@EnableCaching
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

**配置缓存管理器**（设置默认 TTL 和 JSON 序列化）：

```java
@Configuration
public class CacheConfig {

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(30))                    // 默认 30 分钟过期
                .serializeKeysWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new GenericJackson2JsonRedisSerializer()));

        return RedisCacheManager.builder(factory)
                .cacheDefaults(config)
                .build();
    }
}
```

**三个核心注解**：

```java
@Service
public class GuideService {

    /**
     * 先查缓存：命中直接返回，不执行方法体；未命中才执行方法并把返回值写入缓存。
     * value/cacheNames：缓存分区名；key：用 SpEL 指定缓存键。
     * sync = true：缓存未命中时并发请求只让一个去查库，防缓存击穿。
     */
    @Cacheable(value = "guide", key = "#guideId", sync = true)
    public Guide getGuideById(String guideId) {
        System.out.println(">>> 真正执行了方法（查库）");
        return guideRepository.findById(guideId).orElse(null);
    }

    /** 方法每次执行，执行后把结果写入缓存（用于更新） */
    @CachePut(value = "guide", key = "#guide.id")
    public Guide updateGuide(Guide guide) {
        return guideRepository.save(guide);
    }

    /** 删除缓存条目 */
    @CacheEvict(value = "guide", key = "#guideId")
    public void deleteGuide(String guideId) {
        guideRepository.deleteById(guideId);
    }
}
```

**注解要点（实习够用）**：

- `@Cacheable`：查，命中直接返回，未命中执行方法并缓存。加 `sync = true` 防击穿。
- `@CachePut`：写，每次执行方法，然后更新缓存。
- `@CacheEvict`：删，删除缓存条目。
- `key` 用 SpEL：`#id` 取参数、`#user.getId()` 取对象属性、`#result` 取方法返回值。（**SpEL** 是 Spring 的表达式语法，可以在注解里写"用哪个字段当缓存 key"。）
- `unless`：条件满足时不缓存（如 `unless = "#result == null"` 不缓存空结果）。
- 缓存名（`value`）是逻辑分区，Redis 里的实际 key 形如 `guide::123`。

## 7.6 阶段六小练习

1. 新建一个 Spring Boot 项目（或在本项目 backend 里），连上 Docker 里的 Redis。
2. 配好 RedisTemplate 的 JSON 序列化，写一个接口：查某个对象时先查缓存、未命中查库回填。
3. 用 `@Cacheable` 改造同一个接口，验证第二次请求不再执行方法体（打印日志确认）。

**算过标准**：能用 `@Cacheable` 让一个接口"第二次调用不打印查库日志"，并能解释 `RedisTemplate` 和 `@Cacheable` 各适合什么场景。

---

# 第 8 章 阶段七：结合本项目场景实战

本项目会用到 Redis 的三个核心场景：**聊天多轮会话状态**、**缓存热点景点攻略**、**token 黑名单**。

## 8.1 场景一：聊天多轮会话状态存储

**背景**：本项目 AI 服务用 LangGraph（一个用 Python 写的"多轮对话框架"，可以把它想象成"帮 AI 记住聊到哪了"的组件）做多轮对话，需要保存每个会话的上下文；Spring Boot 后端（Java）也需要能查询/管理会话状态。**两者职责怎么划分？**

### 职责划分（关键结论）

| 数据 | 谁写 | 谁读 | 用途 |
|---|---|---|---|
| **LangGraph 检查点（checkpoint）** | LangGraph 的 `RedisSaver` 自动写 | LangGraph 自动读 | 保存多轮对话的完整 graph 状态（消息历史、分支状态） |
| **会话元信息** | Spring Boot 后端写 | Spring Boot 后端读 | 会话 ID、用户 ID、创建时间、模型模式、标题等 |
| **会话历史副本**（可选） | Spring Boot 后端读 checkpoint 后汇总 | 前端/列表页 | 会话列表展示、摘要 |

**一句话原则**：**"状态机内部的状态"交给 LangGraph 的 checkpointer 管（用 RedisSaver），"业务上需要给用户看/给后端用的元信息"由 Spring Boot 用 Redis 自己存。** 不要两套都写，避免状态不一致。

### LangGraph 侧：用 RedisSaver 做 checkpointer

LangGraph 官方提供 Redis 检查点保存器（Python 包 `langgraph-checkpoint-redis`）。核心用法是给图绑定 `checkpointer`，调用时指定 `thread_id`，每次对话自动恢复/保存该线程的状态：

```python
from langgraph.checkpoint.redis import RedisSaver
from langgraph.prebuilt import create_react_agent

REDIS_URI = "redis://localhost:6379"

with RedisSaver.from_conn_string(REDIS_URI) as checkpointer:
    checkpointer.setup()  # 初始化 Redis 索引（只需一次）
    graph = create_react_agent(model, tools=tools, checkpointer=checkpointer)

    # thread_id 即"会话标识"，多轮对话的上下文自动存在 Redis 里
    config = {"configurable": {"thread_id": "chat_1001"}}
    graph.invoke({"messages": [("human", "帮我推荐西湖附近的景点")]}, config)
    # 下一次只需传新的消息，Redis 会自动恢复完整历史
    graph.invoke({"messages": [("human", "换个不那么累的")]}, config)
```

需要了解的点（看懂项目即可，不要求全掌握）：

- **checkpoint（短期记忆）**：`RedisSaver` 保存每个线程的最新状态，支持 TTL 自动过期（会话多久没聊就清理）。
- **store（长期记忆）**：`RedisStore` 跨线程保存用户长期偏好等，进阶再学。
- Redis 8.0+ 已内置 RedisJSON / RediSearch 模块，LangGraph Redis 集成可直接用；若用老版本 7.x 需要 Redis Stack。

### Spring Boot 侧：用 Hash 存会话元信息

后端需要维护"会话"这个业务对象（给前端列表、删除会话、展示摘要），这些信息用 Redis **Hash** 存最合适：

```bash
HSET chat:chat_1001 user_id "u_88" title "西湖一日游" mode "travel"
HSET chat:chat_1001 summary "已推荐3个景点"
EXPIRE chat:chat_1001 604800        # 7 天未活跃自动清理
```

Java 侧：

```java
@Service
public class ChatSessionService {

    private final StringRedisTemplate redisTemplate;

    public ChatSessionService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public void createSession(String chatId, String userId, String mode) {
        String key = "chat:" + chatId;
        Map<String, String> fields = new HashMap<>();
        fields.put("user_id", userId);
        fields.put("mode", mode);
        fields.put("created_at", String.valueOf(System.currentTimeMillis()));
        redisTemplate.opsForHash().putAll(key, fields);
        redisTemplate.expire(key, Duration.ofDays(7)); // 会话 7 天过期
    }

    public Map<Object, Object> getSession(String chatId) {
        return redisTemplate.opsForHash().entries("chat:" + chatId);
    }

    public void deleteSession(String chatId) {
        redisTemplate.delete("chat:" + chatId);
    }
}
```

> **为什么不把聊天历史整个塞进 Redis 的 string？** 聊天历史（尤其长对话）体积大、结构复杂，重放给模型时需要完整结构，这部分正是 LangGraph checkpoint 的职责。后端 Redis 只存"轻量的元信息"即可，保持职责单一。

## 8.2 场景二：缓存热点景点攻略

**背景**：景点攻略详情页被频繁访问，直接查 MySQL 压力大。用 Redis 做"缓存 + 热点榜"。

### 攻略详情缓存

用 `@Cacheable` 即可（防击穿开 `sync = true`，TTL 加随机偏移防雪崩）：

```java
@Cacheable(value = "guide", key = "#guideId", sync = true)
public Guide getGuideById(String guideId) {
    return guideRepository.findById(guideId).orElse(null);
}
```

进阶一点：TTL 随机偏移（防止整点集体过期）——不用注解，改用 RedisTemplate 手动控制：

```java
public void saveGuideWithRandomTtl(String guideId, Guide guide) {
    long baseTtl = Duration.ofHours(1).toSeconds();
    long jitter = ThreadLocalRandom.current().nextLong(0, 600); // 0~10 分钟随机
    redisTemplate.opsForValue().set("guide:" + guideId, guide,
            Duration.ofSeconds(baseTtl + jitter));
}
```

### 热点景点排行榜

用 ZSet，把每个景点的"访问量/热度分"作为 score：

```bash
ZINCRBY hot:guide 1 "guide_1001"     # 每次访问给该攻略 +1 分
ZREVRANGE hot:guide 0 9 WITHSCORES   # 取热度前 10
```

Java 侧：

```java
@Service
public class HotGuideService {

    private final StringRedisTemplate redisTemplate;

    public void recordVisit(String guideId) {
        redisTemplate.opsForZSet().incrementScore("hot:guide", guideId, 1);
    }

    public List<String> top10() {
        Set<String> top = redisTemplate.opsForZSet()
                .reverseRange("hot:guide", 0, 9);
        return new ArrayList<>(top);
    }
}
```

## 8.3 场景三：token 黑名单（退出登录立即失效）

**背景**：本项目用 JWT 做登录凭证（**JWT** 是一个字符串 token，服务端不保存它，靠"验签"判断合法）。JWT 的优点是无状态，但缺点是"签出去了就不好撤回"。如果用户点"退出登录"，理论上那个 token 在过期前还能用——这不行。

**解决**：退出时把该 token 记进 Redis 的一个"黑名单"里，设过期时间 = 该 token 剩余有效期。之后每次收到请求，先查 Redis 看看这个 token 在不在黑名单里，在就拒绝。

```bash
# 用户退出登录时，把 token 加入黑名单，过期时间 = token 剩余有效期
SET blacklist:token:eyJhbGciOiJIUzI1NiJ9.xxx 1 EX 3600

# 每次请求校验 token 前，先查黑名单
GET blacklist:token:eyJhbGciOiJIUzI1NiJ9.xxx   # 返回 1 说明已注销
```

Java 侧示意（一般配合 Spring Security 的过滤器）：

```java
@Service
public class TokenBlacklistService {

    private final StringRedisTemplate redisTemplate;

    public void revoke(String token, long ttlSeconds) {
        redisTemplate.opsForValue()
                .set("blacklist:token:" + token, "1", Duration.ofSeconds(ttlSeconds));
    }

    public boolean isRevoked(String token) {
        return Boolean.TRUE.equals(redisTemplate.hasKey("blacklist:token:" + token));
    }
}
```

> 说明：这是"可选优化"。本项目第一阶段可以只做无状态 JWT，先不做黑名单；等做到"退出登录/踢人下线"功能时再补。重点是理解"用一个快速数据库记住'哪些凭证作废了'"这个思路。

## 8.4 阶段七小练习（项目实战）

1. 跑通 LangGraph + `RedisSaver`：两个 `invoke` 之间能记住上一轮对话。
2. 在 Spring Boot 里写 `ChatSessionService`：创建/读取/删除一个聊天会话，用 redis-cli 确认数据落在 Hash 里且带过期时间。
3. 给攻略详情加缓存 + 热度榜：访问一次 +1 分，能查出 Top 10。
4. （选做）实现 token 黑名单：调用 `revoke` 后，`isRevoked` 返回 true。

**算过标准**：能画一张图说明"LangGraph checkpoint 存什么、Spring Boot 的 Redis 存什么、两者怎么配合"，且前三个小练习都跑通。

---

# 第 9 章 资源清单

> 搜索时间为 2026-08，版本信息为当前最新。

### 官方文档

- **Redis 官方文档（英文）**：<https://redis.io/docs/> — 权威、全面，建议当作"字典"查，不用通读。
- **Redis 官方快速入门**：<https://redis.io/docs/latest/develop/get-started/> — 适合新手的第一篇。
- **Redis 命令参考（英文，可交互试）**：<https://redis.io/docs/latest/commands/> — 忘了命令就查。
- **Redis 中文文档（redis.cn，社区维护）**：<http://www.redis.cn/documentation.html>；命令中文参考：<http://www.redis.cn/commands.html>
- **Redis 在线练习**：<https://try.redis.io/> — 浏览器里直接敲命令，零安装。

### 版本信息

- **当前最新稳定版：Redis 8.10（2026-07-29 GA，最新补丁 8.10.1）**；Redis 8.0 于 2025-05-02 GA，8.0 起更名为 Redis Open Source，并内置了 JSON / TimeSeries / 搜索等模块。
- 版本发布说明：<https://redis.io/blog/redis-8-ga.md>

### 免费中文教程 / 视频

- **尚硅谷 Redis 7 零基础到进阶（B 站，免费）**：<https://www.bilibili.com/video/BV13R4y1v7sP> — 从零基础到进阶，带面试题，适合入门。
- **尚硅谷 Redis 6 入门到精通（B 站，免费）**：<https://www.bilibili.com/video/BV1Rv41177Af>
- **黑马程序员 Redis 入门到实战（B 站，免费，含项目）**：<https://www.bilibili.com/video/BV1cr4y1671t> — 配合"黑马点评"项目讲缓存穿透/击穿/雪崩、分布式锁，进阶看。

### 示例项目（GitHub）

- **AngelLFMorante/CacheRedis**：<https://github.com/AngelLFMorante/CacheRedis> — 最小可跑的 Spring Boot 3 + Redis 缓存示例，覆盖 `@Cacheable` / `@CachePut` / `@CacheEvict`，适合入门照抄。
- **黑马点评（Dark-Horse-Reviews）**：<https://github.com/05Huang/Dark-Horse-Reviews> — 高并发 Redis 实战项目，覆盖缓存三大问题、分布式锁、GEO、Stream 队列，实习加分项，后续进阶用。

### 与 LangGraph 结合（本项目专属）

- **Redis 官方博客：Build smarter AI agents with LangGraph and Redis**：<https://redis.io/blog/langgraph-redis-build-smarter-ai-agents-with-memory-persistence/>
- **langgraph-checkpoint-redis（PyPI）**：<https://pypi.org/project/langgraph-checkpoint-redis/>

---

## 附：常见新手问题速查

1. **redis-cli 连不上**：先 `docker ps` 看容器是否在跑；再确认端口映射 `-p 6379:6379`；本机直连用 `redis-cli`，容器内用 `docker exec -it my-redis redis-cli`。
2. **中文乱码**：用 `redis-cli --raw` 启动。
3. **Spring Boot 3.x 配 Redis 没生效**：注意配置前缀是 `spring.data.redis`，不是 `spring.redis`。
4. **存的对象取出来变 Map 或反序列化报错**：基本是序列化配置问题，按 7.3 配置 JSON 序列化，实体类实现 `Serializable`。
5. **`@Cacheable` 不生效**：检查启动类有没有 `@EnableCaching`；检查方法是不是被同类内部调用（Spring AOP 对同类内部调用 `this.method()` 不生效，需要走代理）。
6. **Docker 跑不起来**：确认 Docker Desktop 图标是静止状态；检查 WSL2 是否启用（管理员 PowerShell 跑 `wsl --install`）；确认电脑虚拟化已开启（BIOS 的 Intel VT-x / AMD-V）。
7. **哪些内容先不学**：集群（Cluster）、哨兵（Sentinel）、Redisson 分布式锁、Lua 脚本、Redis 模块（JSON/搜索等）——这些是进阶内容，实习前能看懂概念即可，不必深入。

> 最后提醒：本教程的目标是"看懂 + 能用"，不是"精通"。先把命令敲熟、把 Spring Boot 集成跑通、把本项目三个场景做出来，就达到了"能去实习"的下限。进阶内容（分布式锁、集群、高可用）等实习后再补。
