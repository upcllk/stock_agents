下面给你一份 **可以直接作为项目 README / 技术方案的 MVP 文档**。
目标：**Agent1 第一版只用 LLM 联网搜索，不写爬虫。**

这样可以：

* **2–3 天内跑起来**
* 避开反爬
* 快速验证思路

等验证价值后，再升级爬虫。

---

# Agent1 技术方案（MVP版）

**目标：**

每天定时抓取公司动态 → LLM总结 → 结构化事件 → 入库

**第一版约束**

* 不写爬虫
* 只用 LLM 联网搜索
* 只做 10–20 只股票
* 每天运行 2–4 次

---

# 一、整体架构

系统流程：

```
定时任务
   │
   ▼
公司列表
   │
   ▼
LLM联网搜索
   │
   ▼
获取新闻列表
   │
   ▼
LLM结构化分析
   │
   ▼
JSON结果
   │
   ▼
写入数据库
   │
   ▼
生成日报
```

核心组件：

```
scheduler  -> 定时任务
search     -> LLM联网搜索
analyzer   -> LLM事件分析
storage    -> DB存储
report     -> 日报生成
```

---

# 二、信息采集方案对比

## 方案1：LLM联网搜索（推荐MVP）

利用模型的 **web search能力**。

例如：

* GPT search
* DeepSeek search
* Perplexity
* Gemini

流程：

```
输入公司名称
   ↓
LLM联网搜索
   ↓
返回最近新闻
```

示例 prompt：

```
搜索最近24小时关于 Tesla 的新闻。
只返回与公司经营、产品、财报、政策相关的新闻。

返回JSON：

[
 {title, source, date, url, summary}
]
```

---

## 优点

开发成本极低：

* 不用写爬虫
* 不处理反爬
* 不处理解析

可以 **2小时写完**

---

## 缺点

1 不稳定

搜索结果可能变化

2 成本

LLM调用成本

3 覆盖度不可控

---

## 适合阶段

**MVP验证阶段**

---

# 三、为什么暂时不用爬虫

传统方案：

```
RSS
网站爬虫
公告接口
财经API
```

问题：

| 问题   | 原因           |
| ---- | ------------ |
| 反爬   | IP限制         |
| 验证码  | Cloudflare   |
| JS渲染 | 需要Playwright |
| 解析复杂 | 每个网站结构不同     |

维护成本非常高。

---

# 四、LLM Prompt 设计

Agent1需要 **两次LLM调用**

---

# Step1：联网搜索

目标：

找到新闻。

Prompt：

```
你是金融研究助手。

任务：
搜索最近24小时关于公司 "{company}" 的重要新闻。

要求：
1 只关注对股价可能有影响的信息
2 忽略无关媒体报道
3 返回最多10条

返回JSON：

[
{
"title": "",
"source": "",
"date": "",
"url": "",
"summary": ""
}
]
```

---

# Step2：事件分析

对每条新闻进行分析。

Prompt：

```
你是股票事件分析助手。

任务：
分析下面新闻对股价的影响。

新闻：
{news_text}

返回JSON：

{
"event_type":"",
"impact_direction":"",
"impact_strength":1-5,
"impact_horizon":"",
"confidence":0-1,
"reasoning":""
}

event_type可选：
earnings
product
order
policy
management
risk
other

impact_direction：
bullish
bearish
neutral

impact_horizon：
short_term
mid_term
long_term
```

---

# 五、是否需要历史上下文

MVP阶段：

**不需要**

原因：

* 每条新闻独立
* 不需要对话

未来可以加：

```
RAG + 历史事件
```

---

# 六、数据库设计

推荐：

**PostgreSQL**

原因：

* JSON支持好
* SQL分析方便
* 稳定

---

# 表1：公司列表

```
CREATE TABLE company_watchlist (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    company_name VARCHAR(200),
    market VARCHAR(20),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

# 表2：新闻表

```
CREATE TABLE news_event (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    title TEXT,
    source VARCHAR(100),
    url TEXT,
    publish_time TIMESTAMP,
    raw_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

# 表3：事件分析表

```
CREATE TABLE event_analysis (
    id SERIAL PRIMARY KEY,
    news_id INT REFERENCES news_event(id),
    event_type VARCHAR(50),
    impact_direction VARCHAR(20),
    impact_strength INT,
    impact_horizon VARCHAR(20),
    confidence FLOAT,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

# 表4：去重表（重要）

避免重复抓新闻。

```
CREATE TABLE news_hash (
    hash VARCHAR(64) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

hash：

```
sha256(title + source)
```

---

# 七、代码架构

推荐Python。

目录结构：

```
stock_agents/
│
├── app/
│
│   ├── agents/
│   │
│   │   └── news_agent.py
│   │
│   ├── services/
│   │
│   │   ├── search_service.py
│   │   ├── analysis_service.py
│   │   ├── storage_service.py
│   │   └── report_service.py
│
│   ├── db/
│   │
│   │   ├── database.py
│   │   └── models.py
│
│   ├── scheduler/
│   │
│   │   └── job_runner.py
│
│   ├── utils/
│   │
│   │   ├── hash_util.py
│   │   └── logger.py
│
├── scripts/
│
│   └── init_db.sql
│
├── config/
│
│   └── settings.py
│
├── main.py
│
└── requirements.txt
```

---

# 每个模块作用

---

# news_agent

核心Agent。

流程：

```
获取公司列表
   ↓
调用search
   ↓
去重
   ↓
调用analysis
   ↓
写入数据库
```

---

# search_service

负责：

```
调用LLM联网搜索
```

输入：

```
company
```

输出：

```
news_list
```

---

# analysis_service

负责：

```
新闻 → 事件结构
```

输入：

```
news
```

输出：

```
event_json
```

---

# storage_service

负责：

```
数据库写入
```

函数：

```
save_news()
save_analysis()
```

---

# report_service

生成：

```
每日公司动态报告
```

---

# scheduler

定时任务。

使用：

```
APScheduler
```

例：

```
每天 08:00
每天 12:00
每天 18:00
```

---

# utils

通用工具。

例如：

```
hash
logging
```

---

# 八、关键代码示例

示例：Agent流程

```
for company in watchlist:

    news_list = search_service.search_news(company)

    for news in news_list:

        if storage.exists(news):
            continue

        news_id = storage.save_news(news)

        analysis = analysis_service.analyze(news)

        storage.save_analysis(news_id, analysis)
```

---

# 九、LLM成本估算

假设：

```
20公司
每天2次
每次10新闻
```

调用次数：

```
搜索 40
分析 400
```

一天约：

```
440 calls
```

完全可控。

---

# 十、日志设计

必须记录：

```
搜索请求
LLM返回
解析错误
入库失败
```

否则调试会很痛苦。

---

# 十一、MVP开发任务拆解

按顺序做。

---

# Step1

创建项目：

```
mkdir stock_agents
```

---

# Step2

创建数据库。

执行：

```
init_db.sql
```

---

# Step3

实现：

```
database.py
```

连接Postgres。

---

# Step4

实现：

```
search_service
```

调用LLM搜索新闻。

---

# Step5

实现：

```
analysis_service
```

分析新闻影响。

---

# Step6

实现：

```
storage_service
```

存入数据库。

---

# Step7

实现：

```
news_agent
```

串联流程。

---

# Step8

实现：

```
scheduler
```

每天自动运行。

---

# Step9

实现：

```
report_service
```

生成日报。

---

# Step10

部署运行：

```
python main.py
```

每天自动抓取。

---

如果你愿意，我可以 **下一步直接给你一份完整的 Python MVP 项目模板**：

包含：

* 可运行代码
* Postgres连接
* LLM调用封装
* Agent实现
* 定时任务

你只需要：

```
pip install
python main.py
```

系统就能开始抓新闻。
