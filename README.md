# Stock Agents · Agent1（MVP）

每天定时抓取公司动态 → LLM 总结 → 结构化事件 → 入库。  
第一版**不写爬虫**，仅用 LLM 联网搜索，适合 2–3 天内跑通并验证思路。

---

## 环境要求与检查

开发与运行前请确认以下环境。

| 依赖 | 用途 | 检查命令 |
|------|------|----------|
| **Python 3.10+** | 运行应用 | `python3 --version` 或 `python --version` |
| **pip** | 安装依赖 | `pip3 --version` 或 `pip --version` |
| **PostgreSQL** | 存储新闻与事件分析 | 服务：`pg_isready -h localhost`；客户端：`psql --version` |

### 本地安装 PostgreSQL（macOS）

本机未安装时，可按以下方式之一安装。

**方式一：Homebrew（推荐）**

```bash
# 若提示目录不可写，先修复权限（按 brew 提示执行）：
# sudo chown -R $(whoami) /opt/homebrew /opt/homebrew/Cellar ... 等

brew install postgresql@16
brew services start postgresql@16

# 将 postgres 加入 PATH（可选，便于使用 psql）
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

**方式二：Postgres.app**

从 [postgresapp.com](https://postgresapp.com/) 下载安装，启动后即可用默认 socket 连接。

**方式三：Docker**

```bash
docker run -d --name postgres-agent1 -e POSTGRES_PASSWORD=dev -p 5432:5432 postgres:16
```

安装完成后，创建本项目用的数据库并执行建表脚本：

```bash
# 创建数据库（默认连接本地、当前系统用户）
createdb stock_agents

# 执行建表（在项目根目录）
psql -d stock_agents -f scripts/init_db.sql
```

### 数据库用户名与密码

**Homebrew / Postgres.app 默认（本机开发）：**

- 默认使用**当前系统用户名**连接（如 `mika`），且本地配置为 **trust**，**不需要密码**。
- 连接串示例：`postgresql://mika@localhost:5432/stock_agents`（把 `mika` 换成你的系统用户名）。

**若希望设置专用数据库用户和密码：**

```bash
# 用默认方式连进 postgres
psql -d postgres

# 在 psql 里执行：
CREATE USER stock_agent WITH PASSWORD '你的密码';
CREATE DATABASE stock_agents OWNER stock_agent;
\c stock_agents
\i /Users/{{your_name}}/code/agents/stock_agents/scripts/init_db.sql
\q
```

之后在 `.env` 或环境变量里配置：

```bash
DATABASE_URL=postgresql://stock_agent:你的密码@localhost:5432/stock_agents
```

**Docker 方式：** 创建容器时已通过 `-e POSTGRES_PASSWORD=dev` 设置密码，用户名为 `postgres`，连接串示例：

```bash
DATABASE_URL=postgresql://postgres:dev@localhost:5432/postgres
```

项目通过环境变量 `DATABASE_URL` 读连接串，可在项目根目录建 `.env` 并写入上述内容（不要提交到 git）。

### 快速检查脚本（可选）

```bash
# 在项目根目录执行
python3 --version && pip3 --version
# PostgreSQL
command -v psql >/dev/null && psql --version && pg_isready -h localhost || echo "PostgreSQL 未安装或未启动"
```

### 安装与启动

```bash
# 1. 创建虚拟环境（推荐）
python3 -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装并启动 PostgreSQL，创建数据库并执行 scripts/init_db.sql（见上方「本地安装 PostgreSQL」）

# 4. 配置 config/settings.py 或 .env（数据库 URL、LLM API 等）

# 5. 运行
python main.py
```

---

## 项目结构及目录职责

```
stock_agents/
├── app/                    # 应用主包
│   ├── agents/             # Agent 层：串联业务流程
│   │   └── news_agent.py   # 核心 Agent：拉取公司列表 → 搜索 → 去重 → 分析 → 入库
│   ├── services/           # 业务服务层
│   │   ├── search_service.py   # LLM 联网搜索：输入公司名，输出新闻列表
│   │   ├── analysis_service.py # 新闻 → 事件结构化分析（event_type、影响方向/强度等）
│   │   ├── storage_service.py # 数据库写入：save_news、save_analysis、去重判断
│   │   └── report_service.py  # 每日公司动态报告生成
│   ├── db/                 # 数据访问层
│   │   ├── database.py    # PostgreSQL 连接与会话管理
│   │   └── models.py      # 表/实体定义（与 init_db.sql 对应）
│   ├── scheduler/          # 定时任务
│   │   └── job_runner.py  # APScheduler 配置与调度（如 08:00 / 12:00 / 18:00）
│   └── utils/              # 通用工具
│       ├── hash_util.py   # 新闻去重用 hash（如 sha256(title + source)）
│       └── logger.py     # 统一日志（搜索请求、LLM 返回、解析/入库错误）
├── scripts/
│   └── init_db.sql        # 建表脚本：company_watchlist、news_event、event_analysis、news_hash
├── config/
│   └── settings.py       # 配置：数据库 URL、LLM API、调度间隔等
├── main.py               # 入口：启动调度或单次跑批
├── requirements.txt     # Python 依赖
└── plans/
    └── agent1.md         # Agent1 技术方案与实现说明
```

### 职责速览

| 目录/文件 | 职责 |
|-----------|------|
| **app/agents/** | 编排流程：拿公司列表 → 调 search → 去重 → 调 analysis → 写库 |
| **app/services/search_service** | 调用 LLM 联网搜索，返回指定公司近期新闻列表 |
| **app/services/analysis_service** | 对单条新闻做事件分析，输出 event_type、impact_direction、impact_strength 等 |
| **app/services/storage_service** | 新闻与事件分析落库，以及基于 hash 的重复判定 |
| **app/services/report_service** | 按日/按公司生成动态报告 |
| **app/db/** | 数据库连接与模型，与 `init_db.sql` 一致 |
| **app/scheduler/** | 定时触发抓取与报告任务 |
| **app/utils/** | hash、日志等通用工具 |
| **config/** | 环境与运行配置 |
| **scripts/init_db.sql** | 首次部署时执行，创建全部表结构 |

更细的流程与表结构、Prompt 设计见 [plans/agent1.md](plans/agent1.md)。
