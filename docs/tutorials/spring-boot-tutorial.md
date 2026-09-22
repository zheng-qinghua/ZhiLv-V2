# Spring Boot 从入门到能用(零基础版)

> 面向读者:**完全零基础的新手**——没写过任何后端代码,不知道什么是 HTTP、接口、数据库,甚至不太熟悉命令行。
> 目标:看懂项目、能独立写 CRUD(增删改查)、能去实习。不读源码,只懂原理。
> 学习方式:边学边做,配合 Claude 辅助写代码。
> 建议总时长:**6~8 周**(业余时间,每天 2~3 小时)。零基础最怕的不是学不会,而是想一口吃成胖子,所以我把每一步都拆得很小。

---

## 目录

- [第 0 章 学前必备知识(完全新手篇)](#第-0-章-学前必备知识完全新手篇)
- [第 1 章 这份教程怎么用](#第-1-章-这份教程怎么用)
- [第 2 章 Spring Boot 是什么 / 当前版本](#第-2-章-spring-boot-是什么--当前版本)
- [第 3 章 Java 基础速成(4~6 天)](#第-3-章-java-基础速成46-天)
- [第 4 章 Spring 核心原理:必须搞懂的三个词](#第-4-章-spring-核心原理必须搞懂的三个词)
- [第 5 章 第一个 Spring Boot 项目](#第-5-章-第一个-spring-boot-项目)
- [第 6 章 开发 REST API](#第-6-章-开发-rest-api)
- [第 7 章 数据层:Spring Data JPA + MySQL(讲透)](#第-7-章-数据层spring-data-jpa--mysql讲透)
- [第 8 章 认证:Spring Security + JWT](#第-8-章-认证spring-security--jwt)
- [第 9 章 开发调试:热部署、日志、DevTools](#第-9-章-开发调试热部署日志devtools)
- [第 10 章 分阶段学习路径总表](#第-10-章-分阶段学习路径总表)
- [第 11 章 资源清单](#第-11-章-资源清单)
- [附:与"智旅云图"项目的关系](#附与智旅云图项目的关系)

---

## 第 0 章 学前必备知识(完全新手篇)

> 这一章不讲 Spring,只讲"做后端这件事本身"。先建立一张完整的地图,后面所有章节都是往地图上填细节。**看不懂就先看下去,不用背,回头需要时再翻回来。**

### 0.1 客户端、服务器、后端、接口(API)

用一个**餐厅**来类比整个网络世界:

- **客户端(Client)**:来吃饭的"顾客"。最常见的是你电脑上的浏览器、手机里的 App。它们负责向别人要东西、展示结果。
- **服务器(Server)**:专门"做饭上菜"的"后厨"——一台 24 小时开机、专门跑程序、替别人干活的电脑。当你在网页上看到的数据,其实都存在服务器上。
- **后端(Backend)**:跑在服务器上的一段程序。它负责干活:查数据、算价格、判断"你是不是登录用户"。我们这门课要学的 Spring Boot,写出来的就是一个后端。
- **接口(API,Application Programming Interface)**:后厨开出来的"点菜窗口"。前端(客户端)不能随便闯进后厨翻冰箱,只能隔着这个窗口喊"我要一份宫保鸡丁"。这个"窗口"就对应服务器上一个特定的网址,比如 `http://localhost:8080/api/trips`。访问它,就相当于对后厨下了一个"给我行程列表"的订单。
- **请求(Request) 与 响应(Response)**:你在窗口喊的话叫"请求",后厨端出来的菜叫"响应"。每次请求,服务器都会返回一个响应。

一句话:**前端是客人,后端是后厨,接口是点菜窗口,数据库是冰箱仓库。**

### 0.2 浏览器访问网页,背后发生了什么

你在地址栏输入 `https://www.baidu.com` 回车,短短一秒内,背后发生了这些事:

1. 你的浏览器(客户端)向百度的一台服务器发出一个"请求":我要你的首页。
2. 百度的服务器收到请求,可能要问它的数据库"今天的热点是什么",拿到数据后组装成一张网页。
3. 服务器把组装好的网页作为"响应"发回你的浏览器。
4. 你的浏览器把收到的内容渲染成你看到的漂亮页面。

学完 Spring Boot 后,你自己写的那台"服务器"干的就是第 2、3 步的活:**收到请求 → 处理数据 → 返回结果**。

### 0.3 HTTP、请求与响应、状态码

- **HTTP(HyperText Transfer Protocol,超文本传输协议)**:客户端和服务器之间**交流用的"共同语言"**。就像中国人和外国人都用英语对话一样,浏览器和后端约定好用 HTTP 这个"标准话术"沟通。你不需要学它的全部,只需要知道它长什么样。

一个 HTTP 请求大致长这样(不用背,看个眼熟):

```
GET /api/trips/3 HTTP/1.1
Host: localhost:8080
Authorization: Bearer eyJhbGciOi...
```

- 第一行是"我要干什么 + 找谁":`GET` 是动作,`/api/trips/3` 是地址。
- 后面几行是"附加说明",比如带身份凭证、带浏览器信息。

**请求的动作(HTTP 方法,Method)**,常用的就 4 个,记忆口诀是"查、增、改、删":

| 方法 | 意思 | 生活类比 |
|------|------|---------|
| `GET` | 获取数据 | 看一眼菜单,不改任何东西 |
| `POST` | 新增数据 | 下单一道新菜 |
| `PUT` | 修改数据 | 把菜退回厨房重做 |
| `DELETE` | 删除数据 | 把这道菜从菜单划掉 |

**响应里最重要的东西之一,是"状态码(Status Code)"**——一个三位数字,告诉客户端"你这次的请求结果怎么样"。相当于快递物流的"已揽收 / 运输中 / 已签收 / 拒收"。

| 状态码 | 含义 | 生活类比 |
|--------|------|---------|
| `200` | 成功,一切正常 | 菜已上齐 |
| `400` | 你(客户端)的请求有错,比如参数填错了 | 你点菜时把"微辣"写成了乱码 |
| `401` | 没登录 / 没带有效凭证 | 你没付钱,服务员不让上菜 |
| `404` | 你要的资源不存在 | 这家店没有这道菜 |
| `500` | 服务器自己出错了 | 后厨着火了 |

你在浏览器里按 `F12` → 打开"网络(Network)"标签,刷新任意网页,就能看到一堆请求和它们的状态码,这是认识 HTTP 最好的方式。

### 0.4 数据库:为什么需要它、表/行/列、SQL

- **数据库(Database)**:专门用来**持久化**保存数据的"仓库"。所谓"持久化",就是数据关机后还在。你程序里用变量存的数据,一旦程序重启就全没了(存在内存里);而数据库把数据存到硬盘上,重启后依然在。

为什么后端一定要配数据库?想象一个旅行 App:用户 A 保存了一个行程,如果只存在他自己那台手机的内存里,用户 B 就永远看不到。只有把行程存到大家都能访问的**服务器数据库**里,任何用户登录后都能查得到。

- **表(Table)**:数据库里数据是按"表"组织的。一张表就是一类东西的清单。比如"行程表 trip"。你可以把它想成一张 Excel 表格。
- **行(Row)**:表里的一行 = 一条完整记录。比如"去北京的 3 天行程"这一条。
- **列(Column)**:表里的一列 = 一个字段(属性)。比如"城市 city"这一列、"天数 days"这一列。

一张 `trip` 表长这样(你会经常用 SQL 看到它):

| id | city | days | budget_level |
|----|------|------|--------------|
| 1 | 北京 | 3 | normal |
| 2 | 成都 | 5 | cheap |

- **SQL(Structured Query Language,结构化查询语言)**:和数据库**对话的语言**。最常用的一个语句是查询:`SELECT * FROM trip;`,意思是"把 trip 表里所有数据给我"。第 7 章你会正式用它来验证数据是否真的存进了数据库。

**现在你只需要记住三句话**:数据要持久化 → 用数据库;数据按表/行/列组织;和数据库说话用 SQL。概念到此为止,动手的部分在第 7 章。

### 0.5 JSON:前后端之间传数据用的格式

- **JSON(JavaScript Object Notation,读作"杰森")**:一种**纯文本的数据格式**,是前后端之间传数据的"标准信封"。因为它是纯文本,任何语言都能读写,所以成了互联网默认的数据交换格式。

它长这样。用你熟悉的**旅行行程**举例——这就是你学的后端要返回给前端的东西:

```json
{
  "city": "北京",
  "days": 3,
  "budgetLevel": "normal",
  "totalBudget": 5000,
  "attractions": ["故宫", "长城", "颐和园"]
}
```

规则很简单,10 秒看懂:
- 外层是一对花括号 `{}`,里面是"键值对",用逗号分隔。
- 键(左边)必须是带双引号的字符串,值(右边)可以是数字(`3`)、字符串(`"北京"`)、数组(`["故宫",...]`)、甚至嵌套的另一个 `{...}`。

当你点开浏览器 Network 里某个接口的"预览(Preview)",看到的那个分层折叠的东西,就是 JSON。**第 6 章你写的接口,返回的就是 JSON。**

### 0.6 编程语言、编译、运行、JDK、IDE、终端

- **编程语言**:人和电脑之间的"翻译媒介"。电脑只懂机器码(0 和 1),人没法直接写。于是发明了高级编程语言(比如 Java),人用接近英语的语法写代码,再由工具翻译给电脑执行。我们要学的 **Java** 是世界上最主流的后端语言之一,很多大公司的服务器程序都是它写的。
- **编译(Compile)**:把人类写的 Java 代码"翻译"成电脑能执行的机器码这一步。Java 的编译器叫 `javac`。
- **运行(Run)**:电脑把编译好的程序真正执行起来,开始干活。写 Java 的流程永远是:**写代码 → 编译 → 运行**。代码写错了,编译阶段就会报错(这是好事,越早发现越好)。
- **JDK(Java Development Kit,Java 开发工具包)**:Java 官方提供的"全套工具箱",里面包含了编译器(`javac`)、运行环境、常用工具库。你写 Java、编译 Java、运行 Java 都离不开它。**装好它,是第一步。**
- **IDE(Integrated Development Environment,集成开发环境)**:给程序员用的"超级记事本",把写代码、编译、运行、看报错都集成到一个窗口里。我们推荐用 **IntelliJ IDEA 社区版(Community Edition)**,免费、功能足够、教程最多。

**安装 IntelliJ IDEA 社区版(照着做):**

1. 打开官网下载页:浏览器搜索"IntelliJ IDEA Community download"或直接访问 [https://www.jetbrains.com/idea/download/](https://www.jetbrains.com/idea/download/)。
2. 页面上有 Windows / macOS / Linux 三个选择。我们用的是 Windows,点 Windows 对应的 **Community Edition(社区版,免费)** 那个大按钮下载 `.exe` 安装包。
3. 双击安装包,一路点"Next(下一步)",遇到"Installation Options(安装选项)"时,勾选上 **"Add 'Open Folder as Project'"(添加右键菜单)** 和 **"Create Desktop Shortcut"(创建桌面快捷方式)**,然后继续"Next → Install → Finish"。
4. 第一次打开,选择"Don't Import Settings(不导入设置)",再选一个你喜欢的主题(黑色或白色都行),点"Start Using IntelliJ IDEA"。
5. 这样就装好了。**注意:社区版是免费的,直接用,不需要激活码,不要去网上找什么"破解版"。**

- **终端 / 命令行(Command Line / Terminal)**:一个**靠打字命令来操作电脑的黑窗口**,不需要鼠标点。它在开发里非常重要,因为很多工具(Java、Maven、Git)都靠命令来用。Windows 上打开方式:按 `Win + R`,输入 `cmd`,回车。

**Windows 下最常用的 5 个命令**(先记住这 5 个,边学边用):

| 命令 | 作用 | 例子 |
|------|------|------|
| `cd 文件夹名` | 进入某个文件夹(cd 是 change directory) | `cd C:\Users\20243\Desktop` |
| `dir` | 列出当前文件夹里有什么 | `dir` |
| `mkdir 名字` | 新建一个文件夹(make directory) | `mkdir my-project` |
| `java -version` | 查看 Java 版本,验证 JDK 装没装好 | `java -version` |
| `mvn -v` | 查看 Maven 版本,验证 Maven 装没装好 | `mvn -v` |

> 小技巧:在文件资源管理器的地址栏输入 `cmd` 并回车,可以**直接在这个文件夹里打开终端**,省去一路 `cd` 的麻烦。

### 0.7 依赖、包管理、Maven、pom.xml

- **依赖(Dependency)**:你程序里要用到的"别人写好的现成功能库"。比如你想让程序能解析 JSON、能连数据库,不需要自己从零写——用现成的库就行。**依赖 = 你点外卖时后厨要用到的现成调料包。**
- **包管理(Package Management)**:自动去网上下载这些依赖、并管理它们版本的工具。否则你要手动去网上一家家下载、复制、放对位置,非常痛苦。
- **Maven(读"妹文")**:Java 世界里最主流的**依赖管理 + 构建工具**。它去中央仓库(一个巨大的公共代码仓库)按清单下载依赖,还能帮你编译、打包。你后面几乎天天和它打交道。
- **pom.xml**:Maven 的"采购清单"文件。里面写着"我这个项目需要哪些依赖、叫什么名字、什么版本"。Maven 一读它,就自动去下载。`pom` 是 `Project Object Model`(项目对象模型)的缩写,不用背,记住"它是 Maven 的清单文件"就行。

在项目里,你只需要记住一个动作:**往 `pom.xml` 里加一行依赖,保存,然后让 Maven 把新的依赖拉下来。** 第 5 章会实际操作。

### 0.8 端口、localhost

- **端口(Port)**:一台电脑上,可以同时运行很多个"服务"(比如一个聊天服务器、一个网页服务器)。端口就是给每个服务发的**"门牌号"**。访问者除了要知道这台电脑的地址(IP),还要知道门牌号(端口),才能准确敲开某一扇门。端口号是一个 0~65535 的数字,常见的如 8080、3306。
- **localhost**:一个特殊的"地址",意思是"**本机**"(我自己的这台电脑)。它等价于 `127.0.0.1`。当你在浏览器输入 `http://localhost:8080`,就是在说"访问我本机电脑上,门牌号 8080 的服务"。

为什么这个很重要?因为你学的 Spring Boot 项目,启动后默认就在本机的 8080 端口上开了一个服务,浏览器访问 `http://localhost:8080` 就能看到它。第 5 章你会亲自体验。

### 0.9 第 0 章自测(能用自己的话答上来即可)

1. 客户端、服务器、后端、接口,各自是什么?用餐厅类比怎么解释?
2. `GET` 和 `POST` 的区别是什么?状态码 200 / 404 / 500 各表示什么?
3. 为什么需要数据库?表、行、列各是什么?
4. 你负责的这个后端接口,返回给前端的是什么格式的数据?(答案:JSON)
5. 用浏览器访问 `http://localhost:8080`,这句话里的 `localhost` 和 `8080` 分别是什么?

答不上来也没关系,翻回对应小节再看一遍。**这一章值得花 2~3 天,不着急。**

---

## 第 1 章 这份教程怎么用

你是来"用"Spring Boot 的,不是来"研究"它的。零基础最大的误区是"我要先把 Java 学完再开始",**千万别这么做**——你的目标不是成为 Java 语言学家,而是能写出、能看懂一个后端项目。这条路线是:

1. **第 0 章:先把地图画出来**(客户端/服务器/HTTP/数据库/JSON 这些概念),扫清未知感。
2. **第 3 章:补 Java 基础语法**(只学"看懂代码"必需的部分,不深究)。
3. **第 4 章:懂三个核心概念**:IoC、DI、Bean。这三个词不懂,后面所有代码都是死记硬背。
4. **第 5~9 章:上手做**:建项目 → 写接口 → 接数据库 → 加登录 → 打磨。每一步配一个小练习。
5. **最后对照"智旅云图"项目**,把学到的能力对应到项目的真实功能上(见文末附录)。

**建议总时长:6~8 周(业余时间,每天 2~3 小时)。** 前 3 周会有点吃力,因为全是新概念;熬过第 4 章,你会突然发现所有代码都在一个套路里打转,后面越学越快。第 10 章有每阶段的时长和过关标准。

**配合 Claude 的正确姿势**:让 Claude 写代码没问题,但你必须能看懂它写的每一行,并能回答"为什么"。看不懂就让它解释:"逐行解释这段代码,我是完全零基础的新手,不懂的术语请用生活类比。" 本章每一节末尾的"过关自测"问题,如果你答不上来,就说明该阶段没过,回头再看。

**你还需要准备的"测试工具"**:后端写好了,怎么验证接口能不能用?你可以在浏览器地址栏直接输入网址访问 `GET` 接口,但要测 `POST`、要模拟登录、要看 JSON 返回格式,最好装一个**接口测试工具**。推荐 **Postman**(免费)或 **Apifox**(中文,对新手更友好)。下载后先不用学会全部功能,第 6 章会手把手带着用。

---

## 第 2 章 Spring Boot 是什么 / 当前版本

### 2.1 一句话定义

**Spring Boot 是 Java 后端世界的一个"快速起步框架",它帮你把开发一个 Web 服务(就是第 0 章说的"后厨")所需要的各种零件(接收请求、连数据库、做安全校验、打日志等)自动组装好,让你用尽量少的配置,就搭出一个能跑起来的后端服务。**

用"后厨"类比:你自己从零开一家餐厅,要分别去学怎么装灶台、怎么接水管、怎么买冰箱;而 Spring Boot 等于给你一个**装修好的中央厨房**,灶台、水管、冰箱都装好了,你只管写菜单(业务代码)。

没有 Spring Boot 的"传统 Java Web 开发" vs 用 Spring Boot:

| 环节 | 传统方式(自己拼装) | Spring Boot(中央厨房) |
|------|-------------------|----------------------|
| 启动服务 | 要手动下载安装一个服务器软件,再配置半天 | 内置服务器,`main` 方法一跑就起来 |
| 配置 | 几十行 XML 配置 | 大部分用默认值,极少数配置写一个 `application.yml` |
| 引入功能 | 手动找库、配版本、处理兼容 | 引入一个"起步依赖(Starter)",全自动配好 |
| 连数据库 | 手动配数据源、写连接工厂 | 加一个依赖 + 几行配置,开箱即用 |

### 2.2 Spring Boot 和 Spring 的区别

- **Spring** 是一大堆模块(Spring Core、Spring MVC、Spring Security、Spring Data…)。它们很强大,但组合起来配置很啰嗦,像买了很多零件还得自己组装。
- **Spring Boot** 在 Spring 之上加了"自动配置"和"起步依赖(Starter)",把 80% 的常用配置变成默认值。你引入一个 `spring-boot-starter-web`,Web 环境就自动配好了,内置一个 Tomcat(服务器软件),`main` 一跑就起来。

简单记:**Spring Boot = Spring + 自动配置 + 起步依赖 + 内嵌服务器**。

### 2.3 当前版本(2026 年 8 月)

- **当前最新稳定版:Spring Boot 4.1.x**(2026-06 发布,基于 Spring Framework 7,要求 JDK 17+,推荐 21)。
- **本项目使用:Spring Boot 4.1.x,本教程按 4.x 讲,跟着教程即对应你手上的项目。**

为什么用 4.1.x?

- 3.5.x 的开源社区支持已于 2026 年 6 月结束,新项目不应再选 3.x;
- 4.x 和 3.x 的**核心概念(IoC/DI/Bean/自动配置/三层架构)完全一样**,国内 3.x 教程内容照样能看懂;
- 本项目的 pom.xml 用的就是 4.1.1,边学边看代码,一一对应。

> 4.x 与 3.x 的小区别:Web 起步依赖的坐标从 `spring-boot-starter-web` 改名为 `spring-boot-starter-webmvc`,其余常用 starter 名称基本不变。

### 2.4 需要的软件(先装好,缺一不可)

| 软件 | 作用 | 说明 |
|------|------|------|
| **JDK 17 或 21** | Java 的运行时 + 编译器 | 装 LTS 版(长期支持版),推荐 **JDK 21**。去 [https://www.oracle.com/java/technologies/downloads/](https://www.oracle.com/java/technologies/downloads/) 或搜"JDK 21 download"下载安装 |
| **Maven 3.9+** | 依赖管理和构建工具(见 0.7) | 去 [https://maven.apache.org/download.cgi](https://maven.apache.org/download.cgi) 下载。装好后配置系统环境变量,让终端能识别 `mvn` 命令 |
| **IntelliJ IDEA(社区版即可)** | 写代码的 IDE(见 0.6) | 社区版免费够用,已在上文讲了安装步骤 |
| **MySQL 8.x** | 数据库(见 0.4) | 第 7 章才需要,可以到时候再装。去 [https://dev.mysql.com/downloads/](https://dev.mysql.com/downloads/) 下载 MySQL Installer for Windows |
| **Postman 或 Apifox** | 接口测试工具 | 第 6 章需要,免费 |

装好环境后,验证:打开终端(见 0.6),输入 `java -version` 和 `mvn -v`,能输出版本号就说明装好了。

> 新手提示:如果你在装 JDK 和 Maven 时卡在"环境变量配置",不要慌。这不是理解问题,是操作熟练度问题——**多试两次,或者让 Claude 一步步带你**,IDEA 其实也能自己检测到已安装的 JDK。装环境一般花半天到一天,卡住了就停下来去搜教程,别死磕。

---

## 第 3 章 Java 基础速成(4~6 天)

这一章的目标是"**看懂 Java 代码**",不是"成为 Java 语法专家"。零基础学 Java,重点是先认识它长什么样,能读懂 Spring Boot 项目里的代码。每个概念我都会用生活化的方式讲。

### 3.1 JDK / JVM / JRE 是什么

- **JDK(Java Development Kit)**:Java 开发工具包,包含编译器(`javac`)和运行环境。你写代码、编译、运行都靠它。(第 0 章讲过,复习一下。)
- **JRE(Java Runtime Environment)**:运行 Java 程序需要的环境,JDK 里内置了它。
- **JVM(Java Virtual Machine,Java 虚拟机)**:Java 程序真正的"运行场所"。Java 代码**先编译**成一种中间格式(字节码,`.class` 文件),然后由 JVM 把字节码翻译成当前电脑能执行的机器码。**JVM 是整个 Java 能"一处编译、到处运行"的关键**——同一份 `.class` 文件,在 Windows、Mac、Linux 上分别装对应版本的 JVM 就能跑。

> 记个区别:有些语言(比如 JavaScript、Python)是"边读边执行"的(解释执行),写错的地方要运行到那行才报错;Java 是"先整体翻译一遍(编译)再运行",所以很多错误在编译阶段就被发现了。你要做的只是知道:Java 多了"编译"这一步。

### 3.2 Maven 常用命令

Maven(见 0.7)你后面天天用,先记住这几个命令就够了:

```bash
mvn clean            # 清理编译产物(删掉 target 目录,重新来)
mvn compile          # 编译
mvn test             # 跑测试
mvn spring-boot:run  # 启动项目(等价于在 IDEA 里点运行按钮)
mvn package          # 打包成可执行 jar 包
```

### 3.3 类 / 对象 / 接口(Java 面向对象速览)

Java 是一种"面向对象"的语言,意思是你写代码时,把东西都组织成"类"。

```java
// 一个类:就是一张"模板"。它描述了"用户"这类东西有哪些属性
public class User {
    private Long id;        // 私有成员变量(字段):id
    private String name;    // 私有成员变量(字段):名字

    // 构造方法:创建这个类的对象时调用,负责把初始值填进去
    public User(Long id, String name) {
        this.id = id;
        this.name = name;
    }

    // getter/setter:Java 里访问私有字段靠方法,不能直接点出来
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
}
```

- **类(class)**:一张"模具/模板"。类比"用户"这个概念本身。
- **对象(Object)**:按模板造出来的一个具体实例。比如 `new User(1, "小明")` 就造了一个具体的用户。
- **成员变量(字段)**:这个类拥有的属性,比如用户的 `id`、`name`。
- **方法(Method)**:这个类能做的动作,比如"获取名字 `getName()`"。类比其他语言里的"函数"。
- **接口(interface)**:一份"我能做什么"的契约,只声明方法名,不写具体实现。类比"服务承诺":餐厅承诺提供"上菜"服务,但具体怎么炒是后厨的事。你后面会用到的 `JpaRepository` 就是接口。
- **依赖(Dependency)**:一个类要干活,需要用到另一个类,那后者就是前者的"依赖"。比如"行程服务"类需要"行程仓库"类,那么"行程服务"就依赖"行程仓库"。(这是第 4 章 IoC/DI 的地基,先有个印象。)

**Lombok(很重要)**:手写 getter/setter 太啰嗦了,业界用一个叫 **Lombok** 的工具,靠注解自动生成。你会在几乎所有项目里看到这种写法:

```java
import lombok.Data;

@Data  // 这一行注解 = 自动生成 getter/setter/toString 等一堆方法
public class User {
    private Long id;
    private String name;
}
```

看到 `@Data` 你就知道:这个类就是个"数据容器",字段自动有 getter/setter,不需要你手写。

### 3.4 注解(Annotation)是什么 —— 一定要理解,这是 Spring 的地基

**注解就是"贴在代码上的标签"。** 它本身不干活,但框架(Spring)会读这些标签,然后根据标签来决定怎么处理你。类比快递箱上的"易碎""加急"贴纸——贴纸本身没有魔力,但快递员看到就会按标签特殊处理。

```java
@RestController       // 贴纸:告诉 Spring "这个类是处理 Web 请求的控制器"
public class HelloController {

    @GetMapping("/hello")   // 贴纸:告诉 Spring "这个方法负责处理 GET /hello 这个地址的请求"
    public String hello() {
        return "Hello";
    }
}
```

注解可以理解为**写给框架看的元信息**。Spring 启动时扫描这些标签,然后自动创建对象、注册接口地址、装配依赖。你学 Spring 的过程,很大一部分就是"学会贴各种标签"。

### 3.5 Lambda 和泛型(看懂流式代码和尖括号)

你会经常看到带 `->` 的代码,这叫 **Lambda**,是一种"把一小段逻辑作为参数传进去"的简写方式。看到 `->` 就知道是它:

```java
// 意思:从 trips 列表里,挑出天数(days)大于 3 的行程
List<Trip> longTrips = trips.stream()
        .filter(t -> t.getDays() > 3)   // 这个 t -> ... 就是 Lambda
        .collect(Collectors.toList());
```

`List<Trip>` 这种带尖括号的写法叫**泛型**,意思是"这个列表里只装某种类型的东西"。`List<String>` = 只装字符串的列表,`List<Trip>` = 只装 Trip 对象的列表。Java 是"静态类型"语言,所有变量都必须声明类型,不像有些语言那样随意——这是它的特点,写起来麻烦一点,但不容易出错。

### 3.6 过关自测(能答上来再进下一章)

1. JVM、JDK、JRE 各自是什么?Java 为什么要"编译"?
2. `pom.xml` 是干什么的?Maven 是做什么的?
3. `@RestController`、`@GetMapping` 这些注解是谁在"读"?为什么要用注解?
4. 看到 `List<Trip>` 能说出它是什么吗?`@Data` 有什么作用?

---

## 第 4 章 Spring 核心原理:必须搞懂的三个词

这一章是整个教程最关键的部分。不求看源码,但要把**设计思想**想通。想通了,你写代码就是在"填空";没想通,你就是在"抄魔法"。这一章值得放慢速度,3~5 天都不算多。

### 4.1 IoC(控制反转,Inversion of Control)

**问题场景**:你的"行程服务"类要查数据库,需要用到"行程仓库"类。传统做法是谁来创建这个仓库?

```java
// 传统写法(控制权在"我"手里):自己在类内部 new 一个依赖
public class TripService {
    private TripRepository repo = new TripRepository(); // 我亲自创建依赖
}
```

**问题**:依赖被写死在代码里。想换一个实现(比如测试时换成假数据),就得改代码;而且每个类都自己 `new` 依赖,类之间像麻绳一样纠缠在一起,很难维护。

**IoC 的做法(控制权反转给容器)**:

```java
// Spring 写法:我不 new,我只声明"我需要一个 TripRepository"
public class TripService {
    private final TripRepository repo;

    public TripService(TripRepository repo) { // 构造方法,Spring 会把现成的对象塞进来
        this.repo = repo;
    }
}
```

**IoC = "创建对象、管理对象生命周期"的控制权,从程序员手里反转给了 Spring 容器。** 用餐厅类比:服务员(你的类)不需要自己买菜、洗菜,只需要对后厨(Spring 容器)说"我要一份鸡",后厨就会把现成的菜递过来。

### 4.2 DI(依赖注入,Dependency Injection)

**DI 是 IoC 的具体实现手段**:当某个类需要依赖时,容器把依赖"注入"进去,而不是让类自己去创建。上面构造方法里那个被"塞进来"的 `repo`,就是被注入进来的依赖。

三种注入方式(知道前两种就行):

```java
// 1. 构造器注入(官方推荐,现在最主流)
@RestController
public class TripController {
    private final TripService tripService;

    public TripController(TripService tripService) {  // Spring 自动把 TripService 实例传进来
        this.tripService = tripService;
    }
}

// 2. 字段注入(旧代码常见,看到要认识)
@RestController
public class TripController {
    @Autowired                 // 这个注解的意思是:让 Spring 把这个字段直接塞进来
    private TripService tripService;
}

// 3. Setter 注入(不常见,了解即可)
```

**为什么用构造器注入**:依赖在对象创建时就固定了,不可能为空,容易测试,IDE 也更容易帮你发现循环依赖(两个类互相需要对方,会死循环)。

### 4.3 Bean 容器(ApplicationContext)

**Bean = 被 Spring 容器创建和管理的一个对象。**

用餐厅类比:**Bean 就是后厨已经做好、随时能端出来的菜;容器(ApplicationContext)就是那个装满成品菜的保温柜。** 你的类想吃哪道菜,不用自己做,喊一声,容器就递给它。

- 你写一个类,加上 `@Component`(或它的变体 `@Service`、`@Repository`、`@Controller`),Spring 启动时扫描到它,就会创建一个实例放到**容器**里。
- 容器像一个"对象仓库",谁需要某个 Bean,声明一下,容器就注入给谁。
- 默认是**单例**的:整个应用里同一个类只有一个实例,大家都用它(这样省内存,也符合"共享服务"的直觉)。

```java
@Component              // 声明:这个类交给 Spring 管理,成为 Bean
public class MyHelper { ... }
```

**几个标注 Bean 的注解,等价关系要记住**(它们作用几乎一样,只是语义不同):

| 注解 | 用途 | 备注 |
|------|------|------|
| `@Component` | 通用组件 | 最底层 |
| `@Service` | 业务层(核心逻辑) | 是 `@Component` 的变体,语义更明确 |
| `@Repository` | 数据访问层 | 同上,Spring 还会帮它把数据库异常翻译得更友好 |
| `@Controller` / `@RestController` | Web 层(处理请求) | 同上 |
| `@Configuration` + `@Bean` | 手动注册 Bean | 当你想把一个"不是自己写的类"(比如第三方库的类)交给容器管理时用 |

**Spring 的"组件扫描"**:`@SpringBootApplication` 所在类的包及其子包会被自动扫描。所以你的类必须放在主类的包(或其子包)下,否则注解不生效——**这是新手最常见的坑之一**。如果明明加了注解却报"找不到 Bean",先检查类的位置对不对。

### 4.4 自动配置 + @SpringBootApplication 到底做了什么

`@SpringBootApplication` 是一个"组合注解",由三个注解合成:

```java
@SpringBootApplication
// 相当于:
// @SpringBootConfiguration  —— 声明这是一个配置类(是 @Configuration 的变体)
// @EnableAutoConfiguration  —— 开启"自动配置"
// @ComponentScan            —— 开启组件扫描
public class TripServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(TripServiceApplication.class, args);
    }
}
```

- **`@ComponentScan`**:扫描主类所在包及其子包,把带 `@Component` 等注解的类注册成 Bean(见 4.3)。
- **`@EnableAutoConfiguration`**:Spring Boot 的**精髓**。它根据你 `pom.xml` 里引入了哪些依赖,自动帮你配置好对应的东西。比如:
  - 你引入了 `spring-boot-starter-web` → 自动配置内嵌服务器 Tomcat、Spring MVC(处理请求的组件)、JSON 序列化工具。
  - 你引入了 `spring-boot-starter-data-jpa` 且配置了数据库 → 自动配置数据库访问、事务管理器。
  - 你引入了 `spring-boot-starter-security` → 自动配置基础安全。
- **`SpringApplication.run(...)`**:启动整个应用。它做的事:创建容器 → 执行自动配置 → 启动内嵌服务器 → 把所有 Bean 实例化并装好 → 然后你的程序就对外服务了。

> 一句话总结启动流程:**main 方法触发 → 容器创建 → 自动配置生效 → 所有 Bean 被实例化并注入 → 内嵌服务器开始监听端口。**

**原理需要学到什么程度?** 能说清上面这句话即可,不需要去看 Spring 内部源码。等你哪天遇到"为什么我加了个依赖就自动配好了"这类问题,再回头加深理解。

### 4.5 常见概念澄清(面试/阅读必备)

- **IoC 和 DI 的关系**:IoC 是**思想**(控制权反转),DI 是**实现手段**(依赖注入)。两人常混着说,但心里要有数。
- **Spring 与 Spring Boot 的关系**:见 2.2。
- **Spring MVC 是什么**:Spring 里负责处理 Web 请求的那套东西(路由、控制器、参数绑定)。Spring Boot 内嵌了它,你不用单独配。
- **AOP(面向切面编程)**:简单理解为"在不改业务代码的前提下,给方法外面包一层额外逻辑"(比如打日志、开事务、做权限检查)。你后面用 `@Transactional`、`@PreAuthorize` 时,其实就是在用 AOP。**不用深学,知道概念即可。**

### 4.6 过关自测

1. 用一句话解释 IoC,再说 DI 是怎么实现 IoC 的。
2. Bean 是什么?`@Service` 和 `@Component` 是什么关系?
3. `@SpringBootApplication` 由哪三个注解组成,各自干什么?
4. 为什么 Spring Boot"引入一个依赖就自动配好了"?这叫什么机制?

---

## 第 5 章 第一个 Spring Boot 项目

### 5.1 用 start.spring.io 创建项目

打开官方脚手架网站 [https://start.spring.io](https://start.spring.io)。这是 Spring 官方提供的"项目生成器":你在网页上勾选想要的东西,它帮你把整个项目骨架下载下来。

按下面配置:

- **Project**:Maven(用 0.7 学的 Maven)
- **Language**:Java
- **Spring Boot**:3.5.x(选最新小版本)
- **Group**:`com.zhilyuntu`(类比一个包名,用来标识你的项目所属组织,通常写公司/个人域名反写)
- **Artifact**:`trip-service`(项目名)
- **Packaging**:Jar(打成 jar 包,一种可执行的压缩文件)
- **Java**:21(或 17)
- **Dependencies(点击 ADD 添加)**:`Spring Web`、`Spring Data JPA`、`MySQL Driver`、`Validation`、`Lombok`、`Spring Security`(后面阶段再加也行)

点 **Generate** 下载一个 zip 压缩包,解压后用 IDEA 打开(File → Open → 选择解压出来的文件夹)。IDEA 会自动下载依赖——**第一次会比较久**,因为要把 Maven 清单里的依赖全部拉下来,耐心等。

> 也可以让 Claude 帮你创建:告诉它"用 Spring Initializr 配置,依赖有 web、data-jpa、mysql、validation、lombok",它会给你 `pom.xml` 和目录骨架。

### 5.2 项目结构解析(必须看懂)

```
trip-service/
├── pom.xml                       # 依赖清单(核心,见 0.7)
├── src/
│   ├── main/
│   │   ├── java/com/zhilyuntu/tripservice/
│   │   │   ├── TripServiceApplication.java   # 启动类(@SpringBootApplication)
│   │   │   ├── controller/                    # Web 层(接收请求)
│   │   │   ├── service/                       # 业务层(核心逻辑)
│   │   │   ├── repository/                    # 数据访问层(接口)
│   │   │   ├── entity/                        # 数据库实体(对应表)
│   │   │   └── common/                        # 通用类(统一响应、异常等)
│   │   └── resources/
│   │       ├── application.yml                # 配置文件(核心)
│   │       ├── application-dev.yml            # 多环境配置(开发环境)
│   │       └── static/  templates/            # 静态资源/模板(前后端分离一般用不上)
│   └── test/java/                             # 测试代码
```

先记住一句话:**`pom.xml` 管"有什么零件",`application.yml` 管"怎么设置",`java` 目录管"写什么代码"。**

### 5.3 pom.xml 怎么读

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.5.16</version>   <!-- 版本号主要就改这里 -->
    </parent>

    <groupId>com.zhilyuntu</groupId>
    <artifactId>trip-service</artifactId>
    <version>0.0.1-SNAPSHOT</version>

    <dependencies>
        <!-- Web 起步依赖:内置服务器 + Spring MVC + JSON 处理 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>

        <!-- JPA 起步依赖:对象关系映射 + 事务 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>

        <!-- 参数校验 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>

        <!-- MySQL 驱动:让 Java 能连接 MySQL 数据库 -->
        <dependency>
            <groupId>com.mysql</groupId>
            <artifactId>mysql-connector-j</artifactId>
            <scope>runtime</scope>
        </dependency>

        <!-- Lombok:自动生成 getter/setter 等 -->
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>

        <!-- Spring Security(认证阶段再加) -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-security</artifactId>
        </dependency>
    </dependencies>
</project>
```

**重点**:`spring-boot-starter-parent` 统一管理了所有 Spring 依赖的版本。所以你写依赖时**不用写版本号**(除了你自己加的第三方库)。这就是"依赖版本管理"。

**Starter(起步依赖)是什么**:一个"打包好的一堆依赖"。`spring-boot-starter-web` 内部包含处理请求的、做 JSON 的、内置服务器等十几个库,你引入它就全有了,还保证版本兼容。类比:你想做西餐,不需要分别买面粉、黄油、烤箱——买一个"西餐入门套餐"就全齐了。

### 5.4 application.yml 配置

```yaml
server:
  port: 8080

spring:
  application:
    name: trip-service

  datasource:
    url: jdbc:mysql://localhost:3306/zhilyuntu?useSSL=false&serverTimezone=Asia/Shanghai&characterEncoding=utf8mb4
    username: root
    password: 你的密码
    driver-class-name: com.mysql.cj.jdbc.Driver

  jpa:
    hibernate:
      ddl-auto: update   # create/create-drop/update/none,开发期用 update
    show-sql: true       # 打印 SQL,方便调试
    open-in-view: false  # 建议关掉(面试考点,现在不用深究)

logging:
  level:
    com.zhilyuntu: debug   # 包级日志级别
```

逐项解释(这些都是第 0 章概念的落地):

- **`server.port`**:服务监听哪个**端口**(见 0.8)。默认 8080,如果被别的程序占了,改成 8081 就行。
- **`spring.datasource.url`**:数据库连接串。格式是固定的 `jdbc:mysql://主机:端口/库名?参数`。其中 `localhost:3306` 意思就是"本机上、3306 端口(MySQL 默认端口)的数据库",`zhilyuntu` 是数据库名。
- **`spring.datasource.username/password`**:连接数据库的账号密码,一般用 MySQL 安装时设置的 root 密码。
- **`ddl-auto: update`**:启动时按实体类自动创建/修改表(第 7 章讲)。开发期用 `update` 很爽,生产环境要关掉。
- **`logging.level`**:日志级别(第 9 章细讲),现在知道它是控制"打印多详细的运行信息"就行。

### 5.5 三层架构(核心中的核心)

Spring Boot 项目几乎是铁板一块的三层架构,你读任何项目都是这个套路:

```
浏览器/前端
   │  HTTP 请求(JSON)
   ▼
[Controller 控制层]   接收请求、校验参数、调 Service、返回响应(接待员)
   │
   ▼
[Service 业务层]     核心业务逻辑、事务边界、调用 Repository(大厨)
   │
   ▼
[Repository 数据层]  直接操作数据库(仓库管理员)
   │
   ▼
[MySQL]             数据库(仓库)
```

用餐厅类比:Controller 是**前厅接待员**(收订单、上菜),Service 是**后厨大厨**(真正做菜),Repository 是**仓库管理员**(负责去冰柜取食材)。

加上两个贯穿的辅助层:

- **Entity(实体)**:和数据库表一一对应的类(第 7 章细讲)。
- **DTO(Data Transfer Object,数据传输对象)**:接口之间传数据用的结构。它的作用是**不把内部实体直接暴露给前端**——比如用户实体里有密码字段,返回给前端前要先转成不含密码的 DTO。**新手常犯的错就是把 Entity 直接返回给前端,把密码也泄露出去了。**

### 5.6 运行第一个项目

在 IDEA 里找到 `TripServiceApplication` 类,点类名左边或上面的**绿色三角**运行。看到类似日志:

```
Tomcat started on port 8080 (http)
Started TripServiceApplication in 2.5 seconds
```

然后浏览器访问 `http://localhost:8080`,会看到 404(因为你还没写任何接口)——**这恰恰说明服务起来了!** 404 是"地址不存在",证明你的服务器已经在 8080 端口上等着接客了(第 0 章的 404 概念派上用场了)。

**小练习 0(半天)**:按 5.1 创建项目,成功启动,浏览器能访问到 404,然后把 `server.port` 改成 8081,重启,浏览器访问 `http://localhost:8081` 也能看到 404。这就是"环境通不通"的验证。

### 5.7 过关自测

1. 项目里 `controller`、`service`、`repository` 各负责什么?用餐厅类比怎么讲?
2. `pom.xml` 里的 `<parent>` 起什么作用?为什么依赖不用写版本号?
3. `application.yml` 里 `datasource.url` 里的 `jdbc:mysql://` 是什么意思?
4. `ddl-auto: update` 是干什么的?
5. 为什么访问 `http://localhost:8080` 看到 404,反而说明服务启动成功了?

---

## 第 6 章 开发 REST API

> 先补一个概念:**REST API** 就是一套"按大家约定俗成的规矩"设计的接口(API 见 0.1)。规矩核心就是:**用 HTTP 方法(GET/POST/PUT/DELETE,见 0.3)表示动作,用 URL 表示资源,用 JSON(见 0.5)传数据。** 比如"查所有行程" = `GET /api/trips`,"新增一个行程" = `POST /api/trips`。

### 6.1 @RestController 与路由注解

```java
@RestController                       // 贴纸:这个类专门处理 HTTP 请求,返回值自动转成 JSON
@RequestMapping("/api/trips")         // 贴纸:这个类所有接口的公共路径前缀(公共门牌号)
public class TripController {

    private final TripService tripService;

    public TripController(TripService tripService) {   // 构造器注入(见 4.2)
        this.tripService = tripService;
    }

    @GetMapping                     // 贴纸:处理 GET  /api/trips
    public List<TripSummary> list() {
        return tripService.listTrips();
    }

    @GetMapping("/{id}")            // 贴纸:处理 GET  /api/trips/3  (3 是路径里的 id)
    public TripDetail get(@PathVariable Long id) {
        return tripService.getTrip(id);
    }

    @PostMapping                    // 贴纸:处理 POST /api/trips
    public TripDetail create(@RequestBody CreateTripRequest req) {
        return tripService.createTrip(req);
    }

    @DeleteMapping("/{id}")         // 贴纸:处理 DELETE /api/trips/3
    public void delete(@PathVariable Long id) {
        tripService.deleteTrip(id);
    }
}
```

**关键注解对照表**(每个注解的作用是啥,一定分清):

| Spring 注解 | 作用 |
|-------------|------|
| `@RestController` | 类上:这个类处理 HTTP 请求,返回值直接转成 JSON 响应 |
| `@RequestMapping("/api/trips")` | 类/方法上的路径前缀,拼出完整地址 |
| `@GetMapping` / `@PostMapping` / `@PutMapping` / `@DeleteMapping` / `@PatchMapping` | 方法上:限定这个接口的 HTTP 方法和路径 |
| `@PathVariable` | 取 URL 路径里的变量,比如 `/api/trips/3` 里的 `3` |
| `@RequestParam` | 取查询参数,比如 `/api/trips?city=beijing` 里的 `beijing` |
| `@RequestBody` | 取请求体(前端发来的 JSON)并自动转成对象 |

### 6.2 请求参数绑定(三种,必须分清)

写接口时,前端传数据有三种"姿势",对应三种注解:

```java
// 姿势 1:查询参数(query param),地址长这样 /api/trips?city=beijing&page=1
@GetMapping("/api/trips")
public Result list(@RequestParam(required = false) String city,      // 可缺省
                   @RequestParam(defaultValue = "1") int page) {    // 缺省为 1
    return Result.ok();
}

// 姿势 2:路径参数(path variable),地址长这样 /api/trips/3
@GetMapping("/api/trips/{id}")
public Result get(@PathVariable Long id) {
    return Result.ok();
}

// 姿势 3:请求体(request body),前端发来 JSON 放在请求体里
@PostMapping("/api/trips")                    // body: { "city": "beijing", "days": 3 }
public Result create(@RequestBody @Valid CreateTripRequest req) {
    return Result.ok();
}
```

### 6.3 DTO 校验(用 Validation)

前端传来的数据不能直接信,必须校验。比如"城市不能为空""天数必须在 1~30 之间"。校验规则用注解贴在 DTO 的字段上:

```java
// 请求 DTO:前端传进来的参数结构 + 校验规则
public class CreateTripRequest {
    @NotBlank(message = "城市不能为空")
    private String city;

    @NotNull(message = "天数不能为空")
    @Min(value = 1, message = "至少 1 天")
    @Max(value = 30, message = "最多 30 天")
    private Integer days;

    @Pattern(regexp = "^(cheap|normal|luxury)$", message = "预算档次不合法")
    private String budgetLevel;
    // getter/setter 或用 @Data
}
```

在 Controller 参数上加 `@Valid`,校验不通过时 Spring 会自动抛异常,配合下面的全局异常处理器统一返回错误信息。

### 6.4 统一响应体(Result / ApiResponse)

让所有接口返回同一个格式,前端才好统一处理。这是企业项目的标配。格式约定为:`{ code, message, data }` 三件套:

```java
public class Result<T> {
    private int code;        // 业务码,0 表示成功
    private String message;  // 提示信息
    private T data;          // 真正的数据(泛型 T,可以是任何类型)

    public static <T> Result<T> ok() { return ok(null); }
    public static <T> Result<T> ok(T data) {
        Result<T> r = new Result<>();
        r.code = 0; r.message = "success"; r.data = data;
        return r;
    }
    public static <T> Result<T> error(String message) {
        Result<T> r = new Result<>();
        r.code = 1; r.message = message;
        return r;
    }
    // getter/setter ...
}
```

用法:

```java
@GetMapping("/{id}")
public Result<TripDetail> get(@PathVariable Long id) {
    return Result.ok(tripService.getTrip(id));
}
```

这样前端拿到的 JSON 永远是 `{"code":0,"message":"success","data":{...}}`,写前端的同事会很感激你。

### 6.5 全局异常处理(@RestControllerAdvice)

**作用:统一拦截所有异常,不让错误堆栈(一堆技术报错信息)直接暴露给前端,而是转成上面那种友好的 JSON。** 这是"统一响应"的闭环——所有接口无论成功失败,返回格式都一样。

```java
@RestControllerAdvice            // 贴纸:全局异常处理器,所有 Controller 抛的异常都经过这里
public class GlobalExceptionHandler {

    // 业务异常:我们自己抛的,message 直接给用户看
    @ExceptionHandler(BizException.class)
    public Result<Void> handleBiz(BizException e) {
        return Result.error(e.getMessage());
    }

    // 参数校验失败
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleValid(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldError().getDefaultMessage();
        return Result.error(msg);
    }

    // 兜底异常:任何没处理到的异常都走这里,记录日志并返回通用错误
    @ExceptionHandler(Exception.class)
    public Result<Void> handleAll(Exception e) {
        // 生产环境这里要记日志(e),不要把堆栈返回给前端
        return Result.error("服务器开小差了,请稍后再试");
    }
}
```

自定义业务异常(自己定义的"业务出错",比如"行程不存在"):

```java
public class BizException extends RuntimeException {
    public BizException(String message) { super(message); }
}
```

抛法:`throw new BizException("行程不存在");` 然后被全局处理器接住,返回 `{"code":1,"message":"行程不存在"}`。

### 6.6 小练习 1(2~3 天):用内存做一份 Trip CRUD

> **CRUD** = Create(增)、Read(查)、Update(改)、Delete(删),是后端最核心的四种操作。

**先不接数据库**,用 `Map<Long, Trip>`(一张内存里的"键值对表",见 3.5 的泛型)或 `List` 存数据,做一个完整的 `Trip` 接口:

- `GET /api/trips` 列出所有行程
- `GET /api/trips/{id}` 查单个行程
- `POST /api/trips` 新增行程(字段:`city`、`days`、`budgetLevel`,带校验)
- `DELETE /api/trips/{id}` 删除行程

**要求**:
1. 全部走统一响应体 `Result`。
2. 查不存在的 id 要抛 `BizException`,由全局处理器返回友好错误。
3. 参数校验用 `@Valid`,非法输入返回错误 JSON。
4. 用 Postman(或 Apifox)全部测通。**不会用 Postman 的话,让 Claude 教你怎么发请求、怎么看返回。**

**过关标准**:4 个接口 + 校验 + 异常处理都能正常工作,你能说清楚每一层(Controller/Service)各自做了什么。

---

## 第 7 章 数据层:Spring Data JPA + MySQL(讲透)

> 本章把第 6 章"内存里"的数据换成"存进 MySQL 数据库"(概念见 0.4),让数据关机不丢、多用户共享。
> 选型说明:教程正文讲 **Spring Data JPA**——它让你"用对象去操作表",心智模型最贴近直觉,新手最好上手。中国很多公司用 **MyBatis/MyBatis-Plus**,本章末尾附了一节对比,实习前补一下即可。

### 7.1 环境准备

1. 安装 MySQL 8.x(第 2 章提到过)。打开 MySQL 命令行工具,建一个库(复制粘贴即可):

   ```sql
   CREATE DATABASE zhilyuntu DEFAULT CHARACTER SET utf8mb4;
   ```

2. 在 `application.yml` 配好数据源(见 5.4),把密码改成你自己的。
3. 确保 `pom.xml` 里有 `spring-boot-starter-data-jpa` 和 `mysql-connector-j`。

### 7.2 Entity(实体):对象 ↔ 表的映射

**Entity(实体)** 是一个 Java 类,它和数据库里的一张表一一对应:类名 ↔ 表名,字段 ↔ 列。这就是 **ORM(Object-Relational Mapping,对象关系映射)**——把"数据库的表"和"程序里的对象"互相翻译的机制。

```java
import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data                        // Lombok:getter/setter/toString
@Entity                      // 贴纸:声明这是一个 JPA 实体,对应一张表
@Table(name = "trip")        // 指定表名(不写默认用类名)
public class Trip {

    @Id                                     // 贴纸:这个字段是主键(唯一标识,像身份证号)
    @GeneratedValue(strategy = GenerationType.IDENTITY) // 主键自增(数据库自动加 1)
    private Long id;

    @Column(nullable = false, length = 64)  // 贴纸:字段约束——非空、长度 64
    private String city;

    private Integer days;

    @Column(name = "budget_level")          // 驼峰(budgetLevel)映射成下划线列(budget_level)
    private String budgetLevel;

    private Integer totalBudget;            // 总预算(元)

    @Column(columnDefinition = "TEXT")      // 存长文本(行程内容)
    private String content;

    private LocalDateTime createdAt;        // 创建时间

    private LocalDateTime updatedAt;
}
```

**映射规则**:
- 类 ↔ 表,字段 ↔ 列。
- 驼峰 `budgetLevel` 自动映射成下划线列 `budget_level`(Spring Boot 默认开启该命名策略)。
- `@Column` 用来细化约束(非空、长度、列名等)。
- `@Id` + `@GeneratedValue` 是主键自增的标准写法。

### 7.3 Repository(数据访问接口):写接口名就完事了

这是 JPA 最爽的地方:**你只需要定义一个接口,继承 `JpaRepository`,常用的 SQL 全自动生成。** 你不用写任何实现代码。

```java
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface TripRepository extends JpaRepository<Trip, Long> {

    // 方法名就是查询条件:Spring 按约定自动生成 SQL
    List<Trip> findByCity(String city);

    // 组合条件:城市 = ? 且 天数 > ?
    List<Trip> findByCityAndDaysGreaterThan(String city, int days);

    // 分页 + 排序:返回 Page 对象
    Page<Trip> findByCity(String city, Pageable pageable);

    // 复杂查询:写 JPQL(用实体名/属性名,不是表名/列名)
    @Query("SELECT t FROM Trip t WHERE t.budgetLevel = :level AND t.totalBudget > :min")
    List<Trip> findBudgetTrips(@Param("level") String level, @Param("min") int min);
}
```

**`JpaRepository<Trip, Long>` 自带的方法**(直接拿来用,不用写实现):第一个泛型参数是实体类,第二个是主键类型。

```java
tripRepository.save(trip);                 // 新增或更新(有 id 就更新,没 id 就新增)
tripRepository.findById(id);               // 查单个,返回 Optional(可能为空,要处理)
tripRepository.findAll();                  // 查全部
tripRepository.findAll(PageRequest.of(0, 10)); // 分页查(第 1 页 10 条)
tripRepository.count();                    // 计数
tripRepository.deleteById(id);             // 按 id 删
tripRepository.existsById(id);             // 判断是否存在
```

这里体现了 Spring 的**"约定优于配置"**思想:你按约定写方法名(`findByCity`、`findByCityAndDaysGreaterThan`),框架自动翻译成 SQL。你想学会这套"方法名生成 SQL"的语法,只需要记住几个关键词:`findBy` + 字段名 + `And`/`Or`/`GreaterThan`/`LessThan` 等。详细规则查官方文档(第 11 章)。

### 7.4 Service 层 + @Transactional(事务)

业务层编排 Repository,并用 `@Transactional` 声明**事务**边界。

> **事务(Transaction)**:一组要么全部成功、要么全部失败的操作。类比转账:A 账户扣钱、B 账户加钱,必须一起成功;如果 B 加钱失败,A 扣钱也要回滚(撤销),否则钱就凭空消失了。

```java
@Service
public class TripService {

    private final TripRepository tripRepository;

    public TripService(TripRepository tripRepository) {   // 构造器注入
        this.tripRepository = tripRepository;
    }

    public Page<Trip> listTrips(String city, int page, int size) {
        return tripRepository.findByCity(city, PageRequest.of(page - 1, size, Sort.by("createdAt").descending()));
    }

    public Trip getTrip(Long id) {
        return tripRepository.findById(id)
                .orElseThrow(() -> new BizException("行程不存在"));
    }

    @Transactional                     // 开启事务:里面任何一步失败,全部回滚
    public Trip createTrip(CreateTripRequest req) {
        Trip trip = new Trip();
        trip.setCity(req.getCity());
        // ... 设置其他字段 ...
        return tripRepository.save(trip);
    }

    @Transactional
    public void deleteTrip(Long id) {
        if (!tripRepository.existsById(id)) {
            throw new BizException("行程不存在");
        }
        tripRepository.deleteById(id);
    }
}
```

**@Transactional 原理(够用的程度)**:
- 它基于 AOP(见 4.5)实现。方法进入前开启事务,方法正常返回后提交(生效),抛异常则回滚(撤销)。
- **适用位置**:写操作(增删改)、多步骤需要"要么全成功要么全失败"的操作。
- **常见坑**:事务靠"代理"实现,所以**同一个类内部方法互相调用**时,`@Transactional` 可能不生效(调的是 `this` 而不是代理)。写代码时把事务方法放到对外暴露的方法上即可。
- 读操作一般不加;要加也是 `@Transactional(readOnly = true)` 做性能提示。

### 7.5 分页和排序(接口返回 Page)

数据多了不能一次全返回,要分页。JPA 的 `Page` 对象自带总条数、总页数等:

```java
@GetMapping
public Result<Page<TripSummary>> list(@RequestParam(defaultValue = "1") int page,
                                      @RequestParam(defaultValue = "10") int size) {
    Page<Trip> p = tripService.listTrips(null, page, size);
    return Result.ok(p);
}
```

`Page<Trip>` 自带 `totalElements`(总条数)、`totalPages`(总页数)、`content`(当前页数据),序列化成 JSON 后,前端拿 `data.content`、`data.totalElements` 即可。

### 7.6 小练习 2(3~5 天):把练习 1 换成 MySQL

把练习 1 的内存版 Trip CRUD 换成 MySQL 持久化:

1. 建 `Trip` 实体、`TripRepository`,写 `TripService`。
2. 实现:新增(带校验)、列表(支持按城市过滤 + 分页)、详情、删除。
3. 给写操作加 `@Transactional`。
4. 用 MySQL 验证数据真的落库了:打开 MySQL 命令行,输入 `SELECT * FROM trip;`(第 0 章的 SQL 派上用场了),应该能看到你插入的行。
5. 再自己加一个字段(比如 `weather`),重启服务,验证 `ddl-auto: update` 自动给表加了一列。

**过关标准**:重启服务后数据还在;分页正确;非法 id 返回友好错误;你能解释"为什么方法名 `findByCityAndDaysGreaterThan` 能自动生成 SQL"。

### 7.7 附:MyBatis / MyBatis-Plus 快速对比(实习常遇)

JPA 是"以对象为中心"(先有 Entity,自动建表);MyBatis 是"以 SQL 为中心"(SQL 你来写,框架只管把结果映射成对象)。国内企业用 **MyBatis-Plus**(MP,MyBatis 的增强版)非常多,实习前要认识它。

核心差异:

| 对比项 | Spring Data JPA | MyBatis-Plus |
|--------|-----------------|--------------|
| 思路 | ORM,对象 ↔ 表 | 半自动,SQL 手写 |
| 建表 | 可以 `ddl-auto` 自动建 | 一般自己写 SQL 建表 |
| 复杂 SQL | JPQL 或 native SQL | XML 文件里写 SQL,灵活 |
| 单表 CRUD | Repository 方法名 | 继承 `BaseMapper<T>` 直接有 CRUD |
| 中文资料/岗位占比 | 较少 | 非常多 |

MyBatis-Plus 快速上手(认识即可,知道长这样):

```xml
<!-- Spring Boot 3 用这个坐标 -->
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
    <version>3.5.9</version>
</dependency>
```

```java
@Mapper
public interface TripMapper extends BaseMapper<Trip> {
    // 单表 CRUD 全自动有:selectById/insert/updateById/deleteById/selectList...
}

// 用法
tripMapper.selectById(1L);
tripMapper.selectList(new LambdaQueryWrapper<Trip>()
        .eq(Trip::getCity, "beijing")
        .orderByDesc(Trip::getCreatedAt));
```

官方中文文档:[https://baomidou.com](https://baomidou.com/)。实习面试前知道 JPA 和 MyBatis 的区别、会写 MP 的单表 CRUD 就够。

---

## 第 8 章 认证:Spring Security + JWT

> 先补概念:**认证(Authentication)** = 确认"你是谁"(登录);**授权(Authorization)** = 确认"你能干什么"(有没有权限)。比如:登录是认证,"只有自己能删自己的行程"是授权。

### 8.1 先懂原理:Session 与 JWT

如何让服务器知道"当前请求是谁"?主流有两种方案:

- **Session 方案(传统)**:登录成功后,服务器在自己内存里存一份"会话记录",返回一个 `sessionId`(会话编号)给浏览器。浏览器每次请求带上这个编号,服务器查一下记录就知道你是谁。**有状态**:服务器要记住每个登录用户,像餐厅记住了每位客人的桌号。
- **JWT 方案(现代前后端分离常用)**:登录成功后,服务器签发一个 **JWT Token** 给前端。前端每次请求在请求头里带上它(`Authorization: Bearer <token>`)。服务器**不存任何会话**,只校验 Token 的签名是否合法、是否过期。**无状态**:服务器不用记人,像发了一张盖章的通行证。

**JWT(JSON Web Token)的结构**(三段,用 `.` 连接):

```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyMSIsImV4cCI6MTc1MDAwMDAwMH0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
──────────────┬────────────── ───────────────┬────────────── ───────────────┬──────────────
         Header(算法类型)               Payload(用户id、过期时间等)         Signature(签名)
```

- **Header**:说明签名算法(如 HS256)。
- **Payload**:放用户信息(不敏感,比如 userId、username、过期时间 `exp`)。**注意:这里只是 Base64 编码,不是加密,任何人都能解码看到,所以绝对不能放密码。**
- **Signature**:用只有服务器知道的密钥,对 `Header + Payload` 做签名。**服务器靠它判断 Token 有没有被篡改。** 就像钞票上的防伪线,商家不用查账本,靠防伪特征就能验真伪。

一句话:**JWT = 一个自包含、带签名防伪标签的"身份通行证"。服务器不用记会话,只验证签名和过期时间。**

### 8.2 Spring Security 的核心思路

Spring Security 是**过滤链(Filter Chain)**机制:每个请求进来,依次经过一串过滤器(安检关卡),只有全部通过才能到达你的 Controller。

```
请求 → [安全检查过滤器] → ... → [登录过滤器] → ... → [授权过滤器] → Controller
        └────────── 认证(你是谁)──────────┘   └── 授权(你能干嘛)──┘
```

**注意**:Spring Boot 3 之后,旧的配置方式 `WebSecurityConfigurerAdapter` 已被删除,必须用 **`SecurityFilterChain` + Lambda DSL** 配置。看到老教程还在用 Adapter,直接跳过别看。

落地思路(三步):

1. **加依赖**:`spring-boot-starter-security` + `jjwt`(JWT 库)。
2. **写一个 JWT 工具类**:负责生成 Token、解析 Token、从 Token 取用户信息。
3. **写一个 JWT 过滤器 + SecurityConfig**:
   - 过滤器:从请求头取 Token → 校验 → 把用户信息放进 `SecurityContextHolder`(Spring 用来暂存"当前登录用户"的箱子)。
   - 配置类:放行登录/注册接口,其余接口要求认证;关掉 Session 和表单登录;启用无状态模式。

### 8.3 落地步骤(代码骨架)

**依赖(pom.xml)**:

```xml
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-api</artifactId>
    <version>0.12.6</version>
</dependency>
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-impl</artifactId>
    <version>0.12.6</version>
    <scope>runtime</scope>
</dependency>
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-jackson</artifactId>
    <version>0.12.6</version>
    <scope>runtime</scope>
</dependency>
```

**JWT 工具类(生成/解析)**:

```java
import io.jsonwebtoken.*;
import javax.crypto.SecretKey;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class JwtUtil {

    // 生产环境放在配置/环境变量里,别硬编码!HS256 密钥必须 >= 32 字节
    private final SecretKey key = Keys.hmacShaKeyFor("zhilyuntu-secret-key-change-me-please-32bytes!".getBytes(StandardCharsets.UTF_8));

    private final long expireMs = 24 * 60 * 60 * 1000; // 24 小时,单位毫秒

    // 生成 token
    public String generateToken(Long userId, String username) {
        Date now = new Date();
        return Jwts.builder()
                .subject(username)               // 主题,一般放用户名
                .claim("userId", userId)         // 自定义声明,放进 Payload
                .issuedAt(now)
                .expiration(new Date(now.getTime() + expireMs))
                .signWith(key, Jwts.SIG.HS256)   // 注意:0.12.x 用 Jwts.SIG.HS256
                .compact();
    }

    // 解析 token,返回其中的用户名
    public String parseToken(String token) {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload()
                .getSubject();
    }
}
```

**JWT 过滤器(每次请求验一遍 Token)**:

```java
import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtUtil jwtUtil;

    public JwtAuthenticationFilter(JwtUtil jwtUtil) { this.jwtUtil = jwtUtil; }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws java.io.IOException, jakarta.servlet.ServletException {
        String header = request.getHeader("Authorization");

        // 从请求头取 "Bearer xxx",去掉前缀 "Bearer " 拿到真正的 token
        if (header != null && header.startsWith("Bearer ")) {
            String token = header.substring(7);
            try {
                String username = jwtUtil.parseToken(token);
                // 构造"已认证"信息,塞进 SecurityContext,表示"这个请求已登录为 username"
                var auth = new UsernamePasswordAuthenticationToken(username, null, java.util.List.of());
                SecurityContextHolder.getContext().setAuthentication(auth);
            } catch (Exception e) {
                // Token 无效/过期:不设置认证信息,后续过滤器会拒绝
                SecurityContextHolder.clearContext();
            }
        }
        filterChain.doFilter(request, response);
    }
}
```

**SecurityConfig(过滤链配置)**:

```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableMethodSecurity   // 开启 @PreAuthorize 方法级权限
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthFilter;

    public SecurityConfig(JwtAuthenticationFilter jwtAuthFilter) { this.jwtAuthFilter = jwtAuthFilter; }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();  // 密码加密存储(哈希)
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())                       // 前后端分离 + JWT,关 CSRF(跨站请求伪造防护)
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS)) // 无状态
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**").permitAll()    // 登录/注册放行(不用认证)
                .requestMatchers("/api/trips/**").authenticated() // 行程接口要登录
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class); // 把我们的过滤器插进安检队伍
        return http.build();
    }
}
```

**登录接口(签发 Token)**:

```java
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UserService userService;
    private final JwtUtil jwtUtil;
    private final PasswordEncoder passwordEncoder;

    // 构造器注入...

    @PostMapping("/login")
    public Result<LoginResponse> login(@RequestBody @Valid LoginRequest req) {
        User user = userService.findByUsername(req.getUsername());
        if (user == null || !passwordEncoder.matches(req.getPassword(), user.getPassword())) {
            throw new BizException("用户名或密码错误");
        }
        String token = jwtUtil.generateToken(user.getId(), user.getUsername());
        return Result.ok(new LoginResponse(token, user.getUsername()));
    }

    @PostMapping("/register")
    public Result<Void> register(@RequestBody @Valid RegisterRequest req) {
        // 密码用 passwordEncoder.encode(req.getPassword()) 加密后再存
        userService.register(req);
        return Result.ok();
    }
}
```

**当前用户信息怎么拿**(常见做法):在 `JwtAuthenticationFilter` 里已经往 `SecurityContext` 塞了认证信息,所以 Controller 里可以这样拿当前登录用户名:

```java
@GetMapping("/me")
public Result<String> me() {
    String username = SecurityContextHolder.getContext().getAuthentication().getName();
    return Result.ok(username);
}
```

### 8.4 小练习 3(3~5 天):给 Trip 加登录保护

在练习 2 的基础上:

1. 建 `User` 实体和 `UserRepository`,实现注册(密码用 BCrypt 加密)和登录(签发 JWT)。
2. 配置 `SecurityConfig`,放行 `/api/auth/**`,其余接口要认证。
3. 保存行程时带上"创建人",只有登录用户能增删改查自己的行程(查询时按当前用户过滤)。
4. 用 Postman 测:不带 Token 访问 → 401(见 0.3);登录拿 Token → 带上 `Authorization: Bearer xxx` 访问 → 200;改错 Token → 401。

**过关标准**:你能画出一条完整链路:"用户登录 → 拿到 Token → 后续请求带 Token → 过滤器验证 → Controller 拿到当前用户"。理解为什么登录接口要放行、为什么 JWT 里不能放密码。

> 提示:不用把 Security 学到很深(记住我、OAuth2、授权码这些先跳过)。**实习面试最常问的就是 JWT 原理 + Security 过滤链 + BCrypt**,这三点搞懂即可。

---

## 第 9 章 开发调试:热部署、日志、DevTools

### 9.1 Spring Boot DevTools(热部署)

改完代码不用手动重启,DevTools 自动帮你重启应用,省掉大量等待时间。

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-devtools</artifactId>
    <optional>true</optional>
</dependency>
```

- IDEA 里勾选 `File > Settings > Build > Compiler > Build project automatically`(自动编译)。
- 改代码后按 `Ctrl+F9`(手动编译),DevTools 会自动重启(比全量重启快)。
- 注意:`optional=true` 表示只在开发期用,打包不会带进生产环境——生产环境不需要自动重启。

### 9.2 日志(Logback)

**日志(Log)** = 程序运行时打印出来的"运行记录",是排查问题的第一工具。Spring Boot 默认集成 Logback,不用额外配置就能用。在类里:

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class TripService {
    private static final Logger log = LoggerFactory.getLogger(TripService.class);

    public void doSomething() {
        log.debug("调试信息: {}", userId);   // {} 是占位符,会自动替换成后面的值
        log.info("业务操作: 创建行程 id={}", id);
        log.warn("警告信息");
        log.error("错误信息", exception);    // 第二个参数传异常,会打印堆栈
    }
}
```

**日志级别**(从低到高):`TRACE < DEBUG < INFO < WARN < ERROR`。级别越高越"严重"。`application.yml` 里控制打印到哪个级别(低于该级别的就不打印):

```yaml
logging:
  level:
    root: info            # 全局默认 info
    com.zhilyuntu: debug  # 自己包下打 debug,方便开发
```

**注意**:
- 别用 `System.out.println` 打日志,一律用 `log`。前者不打时间/级别/类名,没法分级过滤,线上根本没法用。
- 日志里别打印密码、Token 等敏感信息。

### 9.3 启动参数和命令行

用命令启动项目、改端口、打环境,这些都是实习常用操作:

```bash
# 指定环境(加载 application-prod.yml)
java -jar app.jar --spring.profiles.active=prod
# 改端口
java -jar app.jar --server.port=8081
# 打包
mvn clean package
# 打包后运行
java -jar target/trip-service-0.0.1-SNAPSHOT.jar
```

### 9.4 单元测试(认识即可)

Spring Boot 对测试支持很好,常用 `@SpringBootTest` 集成测试。实习阶段能写个简单的即可:

```java
@SpringBootTest
class TripServiceTest {
    @Autowired
    private TripService tripService;

    @Test
    void shouldCreateTrip() {
        // 断言...
    }
}
```

**这个阶段知道"测试类放在 `src/test` 下、`@Test` 标记方法、断言用 AssertJ"即可,不要求精通。**

### 9.5 过关自测

1. DevTools 是干什么的?为什么打包不会带上它?
2. 打日志用 `System.out.println` 有什么问题?日志级别由低到高怎么排?
3. 线上出问题时,你靠什么定位问题?(答案:日志 + 请求链路,不是靠猜)

---

## 第 10 章 分阶段学习路径总表

> 零基础版把每一步都放慢了。**每天 2~3 小时、业余学习,大约 6~8 周过完**;如果全职学,3~4 周能过完。进度慢了不用慌,宁可每步都懂,不要囫囵吞枣。

| 阶段 | 内容 | 对应章节 | 建议时长 | 过关标准 | 对应"智旅云图"功能 |
|------|------|---------|---------|---------|---------------------|
| **0** | 学前必备知识 + 装环境(JDK/Maven/IDEA/MySQL) | 第 0、2 章 | 2~3 天 | 能用自己的话解释客户端/服务器/HTTP/数据库/JSON;`java -version`、`mvn -v` 正常 | 一切的前提 |
| **1** | Java 基础速成 | 第 3 章 | 4~6 天 | 能看懂第 3 章自测 4 问;看到类/注解/Lombok/泛型不慌 | 能看懂现有 Spring 代码结构 |
| **2** | Spring 核心原理(IoC/DI/Bean/自动配置) | 第 4 章 | 3~5 天 | 能说清 IoC/DI/Bean 三词;看懂 `@SpringBootApplication` | 看懂依赖注入如何组装各模块 |
| **3** | 第一个项目:start.spring.io、pom.xml、application.yml、三层架构 | 第 5 章 | 2~3 天 | 独立创建项目并启动;能讲清每层职责 | 项目骨架搭建(对应 backend 工程化) |
| **4** | REST API:Controller、参数绑定、统一响应、全局异常、校验 | 第 6 章 | 2~3 天 | 完成小练习 1(内存 Trip CRUD) | `GET/POST/DELETE /api/trips`、`/api/trips/stats` 这类接口 |
| **5** | 数据层:JPA Entity/Repository、事务、分页 | 第 7 章 | 3~5 天 | 完成小练习 2(MySQL 持久化 CRUD) | `trip` 表持久化、保存行程、历史列表、分页 |
| **6** | 认证:Security + JWT | 第 8 章 | 3~5 天 | 完成小练习 3(登录保护 + 按用户隔离数据) | 用户体系、保存行程需登录、多用户数据隔离 |
| **7** | 外部接口调用 + 日志/调试 | 第 9 章 | 2~3 天 | 能调通一个外部 HTTP 接口(如天气 API);日志分级 | 调用高德地图 POI、天气接口;`token_usage` 统计日志 |

**总计:约 6~8 周(业余每天 2~3 小时)。** 第 6 阶段(认证)可以放到后面,先做通 CRUD 也行——很多公司实习前 1 个月也就要求"会 CRUD + 懂三层 + 会 JPA/MyBatis"。

**进阶方向(实习前可挑着看,不必全学)**:
- Redis 缓存(项目里用了 Redis 缓存天气/地图/RAG 结果)
- Swagger/SpringDoc 接口文档
- 消息队列、分布式、微服务(先不用碰)

---

## 第 11 章 资源清单

### 11.1 官方文档(最权威,优先)

| 资源 | 链接 | 用途 |
|------|------|------|
| Spring 官方快速入门 | [https://spring.io/quickstart](https://spring.io/quickstart) | 官方 Hello World,5 分钟 |
| Spring Initializr(项目脚手架) | [https://start.spring.io](https://start.spring.io) | 创建项目用,最高频 |
| Spring Boot 参考文档(索引) | [https://docs.spring.io/spring-boot/index.html](https://docs.spring.io/spring-boot/index.html) | 查配置项、查特性,权威 |
| Spring Boot 3.5 版本文档 | [https://docs.spring.io/spring-boot/3.5/reference/](https://docs.spring.io/spring-boot/3.5/reference/) | 跟教程版本一致的文档 |
| Spring Data JPA 官方文档 | [https://docs.spring.io/spring-data/jpa/reference/](https://docs.spring.io/spring-data/jpa/reference/) | 学 Repository 方法命名、查询 |
| Spring Security 参考文档 | [https://docs.spring.io/spring-security/reference/](https://docs.spring.io/spring-security/reference/) | 认证授权权威资料 |

> 使用建议:不用从头读官方文档(很长)。**当成"字典"查**:遇到配置不会写、某个注解不确定,先来这里搜。

### 11.2 免费中文视频教程(挑一个跟到底即可,别贪多)

| 教程 | 链接 | 特点 |
|------|------|------|
| **尚硅谷新版 SpringBoot3 教程** | [https://www.bilibili.com/video/BV1XC4y1R7kU](https://www.bilibili.com/video/BV1XC4y1R7kU) | 94 集,基于 JDK17,从入门到原理到实战,资料全,口碑好 |
| **黑马程序员 SpringBoot3+Vue3 全套** | [https://www.bilibili.com/video/BV14z4y1N7pg](https://www.bilibili.com/video/BV14z4y1N7pg) | 112 集,企业级实战(含 JWT、MyBatis、Redis、大事件项目),适合"能干活"目标 |
| **狂神说 Java SpringBoot 教程** | [https://www.bilibili.com/video/av75233634](https://www.bilibili.com/video/av75233634) | 61 集,通俗易懂,经典入门,覆盖 SpringSecurity/MyBatis/Dubbo |
| 尚硅谷 SSM 全套(Spring6+SpringBoot3) | [https://www.bilibili.com/video/BV1AP411s7D7](https://www.bilibili.com/video/BV1AP411s7D7) | 想补 Spring 底层基础再看 |

> **学习建议**:不要三个都看。选**一个**从头跟到尾(推荐黑马或尚硅谷),学完再回来对照本教程做练习。视频 + 本教程 + 官方文档三件套配合。

> 关于"廖雪峰":他没有专门的 Spring Boot 入门教程,但他有面向 Java 新手的基础教程(含面向对象、集合),零基础 Java 语法薄弱可补;进阶有《手写 Spring》(Summer Framework)帮理解 IoC/AOP 原理,不急着看。

### 11.3 值得模仿的开源示例项目

| 项目 | 链接 | 为什么值得看 |
|------|------|-------------|
| **若依 RuoYi** | Gitee:[https://gitee.com/y_project/RuoYi](https://gitee.com/y_project/RuoYi)(前后端分离版 RuoYi-Vue:[https://gitee.com/y_project/RuoYi-Vue](https://gitee.com/y_project/RuoYi-Vue)) | 后台管理系统标杆,SpringBoot + Security + JWT + 代码生成器,架构清晰、文档全。**国内实习常见背景,强烈推荐读它的分层和权限设计** |
| **macrozheng/mall(商城)** | GitHub:[https://github.com/macrozheng/macrozheng.github.io](https://github.com/macrozheng/macrozheng.github.io) / 项目:[https://github.com/macrozheng/mall](https://github.com/macrozheng/mall) | 大型单体电商项目(60k+ Star),SpringBoot + MyBatis + Redis + ES,配套大量文章,适合看"真实业务项目长什么样" |

> **阅读建议**:不要从零通读源码(会劝退)。**先跑起来**,然后只看三个东西:`controller` 怎么分层、`application.yml` 配了哪些东西、`SecurityConfig` 怎么写的。

### 11.4 其他常用资料(按需)

| 资源 | 链接 | 用途 |
|------|------|------|
| MyBatis-Plus 官方中文文档 | [https://baomidou.com](https://baomidou.com/) | 学 MP,国内公司高频 |
| Spring Boot 中文文档镜像 | [https://springdoc.tech](https://springdoc.tech) | 看中文版官方文档 |
| JavaGuide(Java 面试/基础) | [https://javaguide.cn](https://javaguide.cn) | 补 Java 基础、面试前突击 |

---

## 附:与"智旅云图"项目的关系

你学的每个能力,最后都会落到"智旅云图"这个真实项目上。项目里后端要做的事,和本教程的对应关系如下:

| 项目里的功能需求 | 你在教程里学到的对应实现 |
|------------------|--------------------------|
| 行程管理(增删改查行程) | 第 6、7 章的 Trip CRUD(`TripController` + `TripService` + `TripRepository` + `trip` 表) |
| 行程列表分页、按城市筛选 | 第 7 章的 `Page` 分页 + `findByCity` 方法命名查询 |
| 保存行程、历史行程记录 | 第 7 章 `Trip` 实体持久化到 MySQL |
| 用户注册/登录 | 第 8 章的 `User` 实体 + 注册/登录接口 + BCrypt 密码加密 |
| 只有登录用户能操作自己的行程(多用户数据隔离) | 第 8 章的 JWT 登录保护 + 按当前用户过滤查询 |
| 调用天气、高德地图 POI 等外部接口 | 第 9 章讲的"调外部 HTTP 接口"能力(配合日志排查) |
| `token_usage` 统计、运行日志 | 第 9 章的日志分级与请求链路排查 |

**学习顺序建议(对应真实开发流程)**:

1. 先搭骨架和三层架构(第 5 章)。
2. 做 Trip 的 CRUD(第 6、7 章)——这对应项目里"行程管理"最核心的功能。
3. 加用户登录(第 8 章)——让保存行程必须登录、多用户数据隔离。
4. 最后接天气/地图等外部接口 + 完善日志(第 9 章)。

**每完成一步,都跑一遍,保持系统随时可用。** 不要憋大招,一次改完所有东西再启动——那样报错都不知道是哪里的问题。

祝学习顺利。六到八周后,你会发现:后端的世界其实就那几个套路,你会读懂大多数 Spring Boot 项目,并且可以自信地走进任何一家 Java 公司的实习面试。
