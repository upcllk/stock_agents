-- Agent1 建表脚本（与 plans/agent1.md 一致）
-- 使用方式：psql -U xu.liu9 -d postgres -f scripts/init_db.sql

-- 先断开所有连到 stock_agents 的会话，否则 DROP 会报 "is being accessed by other users"
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'stock_agents' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS stock_agents;
CREATE DATABASE stock_agents;
\c stock_agents

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

-- ========== 表与列注释 ==========

COMMENT ON TABLE company_watchlist IS '公司关注列表，用于定时抓取的公司/标的';
COMMENT ON COLUMN company_watchlist.id IS '主键';
COMMENT ON COLUMN company_watchlist.ticker IS '股票代码';
COMMENT ON COLUMN company_watchlist.company_name IS '公司名称';
COMMENT ON COLUMN company_watchlist.market IS '市场，如 US、HK';
COMMENT ON COLUMN company_watchlist.enabled IS '是否启用抓取';
COMMENT ON COLUMN company_watchlist.created_at IS '创建时间';

COMMENT ON TABLE news_event IS '新闻事件表，存储抓取到的公司相关新闻';
COMMENT ON COLUMN news_event.id IS '主键';
COMMENT ON COLUMN news_event.ticker IS '股票代码';
COMMENT ON COLUMN news_event.title IS '新闻标题';
COMMENT ON COLUMN news_event.source IS '来源';
COMMENT ON COLUMN news_event.url IS '新闻链接';
COMMENT ON COLUMN news_event.publish_time IS '发布时间';
COMMENT ON COLUMN news_event.raw_summary IS '原始摘要';
COMMENT ON COLUMN news_event.created_at IS '创建时间';

COMMENT ON TABLE event_analysis IS '事件分析表，LLM 对新闻的影响分析结果';
COMMENT ON COLUMN event_analysis.id IS '主键';
COMMENT ON COLUMN event_analysis.news_id IS '关联新闻 ID（news_event.id）';
COMMENT ON COLUMN event_analysis.event_type IS '事件类型：earnings/product/order/policy/management/risk/other';
COMMENT ON COLUMN event_analysis.impact_direction IS '影响方向：bullish/bearish/neutral';
COMMENT ON COLUMN event_analysis.impact_strength IS '影响强度 1-5';
COMMENT ON COLUMN event_analysis.impact_horizon IS '影响周期：short_term/mid_term/long_term';
COMMENT ON COLUMN event_analysis.confidence IS '置信度 0-1';
COMMENT ON COLUMN event_analysis.reasoning IS '分析理由';
COMMENT ON COLUMN event_analysis.created_at IS '创建时间';

COMMENT ON TABLE news_hash IS '新闻去重表，hash = sha256(title + source) 避免重复抓取';
COMMENT ON COLUMN news_hash.hash IS 'sha256(title + source)，用于去重';
COMMENT ON COLUMN news_hash.created_at IS '创建时间';
