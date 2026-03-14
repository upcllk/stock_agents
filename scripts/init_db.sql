-- Agent1 建表脚本（与 plans/agent1.md 一致）
-- 使用前请先创建数据库：createdb stock_agents

-- 表1：公司列表
CREATE TABLE IF NOT EXISTS company_watchlist (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    company_name VARCHAR(200),
    market VARCHAR(20),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 表2：新闻表
CREATE TABLE IF NOT EXISTS news_event (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    title TEXT,
    source VARCHAR(100),
    url TEXT,
    publish_time TIMESTAMP,
    raw_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 表3：事件分析表
CREATE TABLE IF NOT EXISTS event_analysis (
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

-- 表4：去重表（hash = sha256(title + source)）
CREATE TABLE IF NOT EXISTS news_hash (
    hash VARCHAR(64) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
