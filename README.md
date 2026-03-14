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

### 一键安装 Python 依赖

在项目根目录执行（建议先激活虚拟环境）：

```bash
pip install -r requirements.txt
```

会安装：`psycopg2-binary`（PostgreSQL）、`APScheduler`（定时任务）、`python-dotenv`（配置）。LLM 相关依赖在 `requirements.txt` 中已注释，按需取消注释后再次执行上述命令。

### 安装与启动（完整步骤）

```bash
# 1. 进入项目根目录
cd /path/to/stock_agents

# 2. 创建并激活虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. 一键安装依赖
pip install -r requirements.txt

# 4. 安装并启动 PostgreSQL，创建数据库并执行建表（见上方「本地安装 PostgreSQL」）
createdb stock_agents
psql -d stock_agents -f scripts/init_db.sql

# 5. 配置 .env（复制 .env.example 为 .env，填写 DATABASE_URL 等）
cp .env.example .env
# 编辑 .env，设置 DATABASE_URL=postgresql://你的用户名@localhost:5432/stock_agents

# 6. 运行
python main.py
```

### 验证数据库连接

在项目根目录、已激活虚拟环境且配置好 `.env` 中的 `DATABASE_URL` 后，执行：

```bash
python scripts/check_db.py
```

- **成功**：会打印「成功连接 PostgreSQL」、版本号以及当前库中的表（若已执行过 `init_db.sql` 会看到 `company_watchlist`、`news_event` 等）。
- **失败**：会打印「连接失败」和具体报错（如密码错误、数据库不存在、服务未启动等），根据提示检查 `.env` 和 PostgreSQL 状态即可。

---

## 项目结构及目录职责

```
stock_agents/
├── app/                    # 应用主包
│   ├── agents/             # Agent 层：串联业务流程（规划）
│   │   └── news_agent.py   # 核心 Agent：拉取公司列表 → 搜索 → 去重 → 分析 → 入库
│   ├── services/           # 业务服务层（每类服务一个子包：base + mock + 具体实现）
│   │   ├── search/         # 搜索：base、mock、deepseek 等
│   │   │   ├── base.py     # NewsItem、SearchService 协议、Prompt 模板
│   │   │   ├── mock.py     # MockSearchService
│   │   │   └── deepseek.py # DeepSeekSearchService（占位）
│   │   ├── analysis/       # 分析：base、mock
│   │   │   ├── base.py     # EventAnalysis、AnalysisService 协议
│   │   │   └── mock.py     # MockAnalysisService
│   │   ├── storage/        # 存储：base、mock、postgres
│   │   │   ├── base.py     # StorageService 协议
│   │   │   ├── mock.py     # MockStorageService
│   │   │   └── postgres.py # PostgresStorageService
│   │   └── report/         # 报告：base、mock
│   │       ├── base.py     # ReportService 协议
│   │       └── mock.py     # MockReportService
│   ├── db/                 # 数据访问层
│   │   └── database.py     # PostgreSQL 连接与会话管理
│   ├── scheduler/          # 定时任务（规划）
│   │   └── job_runner.py   # APScheduler 配置与调度
│   └── utils/              # 通用工具（规划）
│       ├── hash_util.py    # 新闻去重 hash
│       └── logger.py       # 统一日志
├── scripts/
│   ├── init_db.sql         # 建表脚本：company_watchlist、news_event、event_analysis、news_hash
│   ├── check_db.py         # 验证数据库连接
│   └── check_search.py     # 验证 search 服务（mock/deepseek）
├── config/
│   └── settings.py         # 配置：DATABASE_URL、SEARCH_PROVIDER、DEEPSEEK_API_KEY 等
├── main.py                 # 入口：启动调度或单次跑批
├── requirements.txt        # Python 依赖
└── plans/
    └── agent1.md           # Agent1 技术方案与实现说明
```

### 职责速览

| 目录/文件 | 职责 |
|-----------|------|
| **app/agents/** | 编排流程：拿公司列表 → 调 search → 去重 → 调 analysis → 写库 |
| **app/services/search/** | LLM 联网搜索：输入公司名，输出新闻列表。实现：mock（默认）、deepseek（占位） |
| **app/services/analysis/** | 新闻 → 事件结构化分析（event_type、impact_direction 等）。实现：mock |
| **app/services/storage/** | 新闻与事件分析落库、基于 hash 去重。实现：mock、postgres（默认） |
| **app/services/report/** | 按日/按公司生成动态报告。实现：mock |
| **app/db/** | 数据库连接，与 `init_db.sql` 一致 |
| **app/scheduler/** | 定时触发抓取与报告任务 |
| **app/utils/** | hash、日志等通用工具 |
| **config/** | 环境与运行配置（含 SEARCH_PROVIDER、STORAGE_PROVIDER 等） |
| **scripts/init_db.sql** | 首次部署时执行，创建全部表结构 |
| **scripts/check_db.py** | 验证 PostgreSQL 连接与表 |
| **scripts/check_search.py** | 验证 search 服务是否可用 |

### 验证 search 服务

在项目根目录、已激活虚拟环境后执行：

```bash
python scripts/check_search.py
```

- **成功**：打印当前 `SEARCH_PROVIDER`、`search_news('Tesla')` 返回条数及前几条的 title/source/date。
- **失败**：打印调用失败原因。未配置真实 API 时使用 `SEARCH_PROVIDER=mock`（默认）即可。

更细的流程与表结构、Prompt 设计见 [plans/agent1.md](plans/agent1.md)。
