-- 表结构扩展脚本（基于 plans/3. news_hash_sql.md）
-- 在已有 stock_agents 库上执行，不删库不删表，仅做最小侵入式扩展
-- 使用方式：psql -d stock_agents -f "scripts/1. news_hash.sql"

\c stock_agents

-- ========== 1. 扩展 news_event ==========
ALTER TABLE news_event
ADD COLUMN IF NOT EXISTS content_text TEXT,
ADD COLUMN IF NOT EXISTS cleaned_text TEXT,
ADD COLUMN IF NOT EXISTS content_length INT,
ADD COLUMN IF NOT EXISTS title_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS simhash BIGINT,
ADD COLUMN IF NOT EXISTS duplicate_status VARCHAR(20) DEFAULT 'unique',
ADD COLUMN IF NOT EXISTS duplicate_of INT,
ADD COLUMN IF NOT EXISTS cluster_id BIGINT,
ADD COLUMN IF NOT EXISTS event_id BIGINT,
ADD COLUMN IF NOT EXISTS language VARCHAR(20),
ADD COLUMN IF NOT EXISTS fetch_batch_id BIGINT;

COMMENT ON COLUMN news_event.content_text IS '原始正文或新闻片段';
COMMENT ON COLUMN news_event.cleaned_text IS '清洗后文本，用于 SimHash / 聚类';
COMMENT ON COLUMN news_event.content_length IS '清洗后长度';
COMMENT ON COLUMN news_event.title_hash IS '标题标准化后 hash';
COMMENT ON COLUMN news_event.simhash IS '近重复检测指纹';
COMMENT ON COLUMN news_event.duplicate_status IS 'unique / exact_duplicate / near_duplicate / ignored';
COMMENT ON COLUMN news_event.duplicate_of IS '若重复，指向主新闻 ID';
COMMENT ON COLUMN news_event.cluster_id IS '新闻主题簇';
COMMENT ON COLUMN news_event.event_id IS '归并到的事件 ID';
COMMENT ON COLUMN news_event.language IS '语言';
COMMENT ON COLUMN news_event.fetch_batch_id IS '抓取批次号';

-- ========== 2. 新建 news_fingerprint（指纹表） ==========
CREATE TABLE IF NOT EXISTS news_fingerprint (
    id SERIAL PRIMARY KEY,
    news_id INT NOT NULL,
    exact_hash VARCHAR(64),
    title_hash VARCHAR(64),
    simhash BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE news_fingerprint IS '新闻指纹表，存储精确去重和近重复去重所需指纹';
COMMENT ON COLUMN news_fingerprint.news_id IS '关联新闻 ID';
COMMENT ON COLUMN news_fingerprint.exact_hash IS '正文清洗后精确 hash';
COMMENT ON COLUMN news_fingerprint.title_hash IS '标题标准化后 hash';
COMMENT ON COLUMN news_fingerprint.simhash IS '用于近重复检测的 SimHash 指纹';

-- ========== 3. 新建 news_cluster（新闻聚类表） ==========
CREATE TABLE IF NOT EXISTS news_cluster (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    cluster_key VARCHAR(100),
    topic_label VARCHAR(200),
    first_publish_time TIMESTAMP,
    last_publish_time TIMESTAMP,
    news_count INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE news_cluster IS '新闻聚类表，同一主题的一组新闻';
COMMENT ON COLUMN news_cluster.ticker IS '股票代码';
COMMENT ON COLUMN news_cluster.cluster_key IS '聚类唯一键';
COMMENT ON COLUMN news_cluster.topic_label IS '主题标签，如 earnings / product launch / lawsuit';
COMMENT ON COLUMN news_cluster.first_publish_time IS '簇内最早发布时间';
COMMENT ON COLUMN news_cluster.last_publish_time IS '簇内最晚发布时间';
COMMENT ON COLUMN news_cluster.news_count IS '簇内新闻数量';
COMMENT ON COLUMN news_cluster.status IS '状态 active/merged/closed';

-- ========== 4. 新建 event_group（事件归并表） ==========
CREATE TABLE IF NOT EXISTS event_group (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    event_key VARCHAR(100),
    event_type VARCHAR(50),
    event_title TEXT,
    status VARCHAR(20) DEFAULT 'open',
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    representative_news_id INT,
    summary_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE event_group IS '事件归并表，表示同一投资事件';
COMMENT ON COLUMN event_group.ticker IS '股票代码';
COMMENT ON COLUMN event_group.event_key IS '事件唯一键';
COMMENT ON COLUMN event_group.event_type IS '事件类型';
COMMENT ON COLUMN event_group.event_title IS '事件标题';
COMMENT ON COLUMN event_group.status IS '事件状态 open/closed/updated';
COMMENT ON COLUMN event_group.start_time IS '事件开始时间';
COMMENT ON COLUMN event_group.end_time IS '事件结束时间';
COMMENT ON COLUMN event_group.representative_news_id IS '代表新闻 ID';
COMMENT ON COLUMN event_group.summary_text IS '事件级汇总摘要';

-- ========== 5. 新建 event_news_mapping（事件与新闻关联表） ==========
CREATE TABLE IF NOT EXISTS event_news_mapping (
    id SERIAL PRIMARY KEY,
    event_id INT NOT NULL,
    news_id INT NOT NULL,
    relation_type VARCHAR(20) DEFAULT 'member',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, news_id)
);

COMMENT ON TABLE event_news_mapping IS '事件与新闻的关联表';
COMMENT ON COLUMN event_news_mapping.event_id IS '事件 ID';
COMMENT ON COLUMN event_news_mapping.news_id IS '新闻 ID';
COMMENT ON COLUMN event_news_mapping.relation_type IS '关系类型：member / representative / update';

-- ========== 6. 扩展 event_analysis ==========
ALTER TABLE event_analysis
ADD COLUMN IF NOT EXISTS event_id INT,
ADD COLUMN IF NOT EXISTS summary_level VARCHAR(20) DEFAULT 'news',
ADD COLUMN IF NOT EXISTS signal_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS signal_score FLOAT;

COMMENT ON COLUMN event_analysis.event_id IS '支持事件级分析';
COMMENT ON COLUMN event_analysis.summary_level IS 'news / cluster / event';
COMMENT ON COLUMN event_analysis.signal_type IS '如 buy_signal / risk_signal / watch_signal / neutral';
COMMENT ON COLUMN event_analysis.signal_score IS '数值化信号强度';

-- ========== 7. 新建 fetch_batch（抓取批次表） ==========
CREATE TABLE IF NOT EXISTS fetch_batch (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    company_name VARCHAR(200),
    fetch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    news_count INT DEFAULT 0,
    unique_count INT DEFAULT 0,
    duplicate_count INT DEFAULT 0,
    cluster_count INT DEFAULT 0,
    event_count INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'success',
    remark TEXT
);

COMMENT ON TABLE fetch_batch IS '抓取批次表，记录一次定时抓取任务的统计信息';
COMMENT ON COLUMN fetch_batch.ticker IS '股票代码';
COMMENT ON COLUMN fetch_batch.company_name IS '公司名称';
COMMENT ON COLUMN fetch_batch.fetch_time IS '抓取时间';
COMMENT ON COLUMN fetch_batch.news_count IS '抓取新闻数';
COMMENT ON COLUMN fetch_batch.unique_count IS '去重后唯一数';
COMMENT ON COLUMN fetch_batch.duplicate_count IS '重复数';
COMMENT ON COLUMN fetch_batch.cluster_count IS '聚类数';
COMMENT ON COLUMN fetch_batch.event_count IS '事件数';
COMMENT ON COLUMN fetch_batch.status IS 'success / failed 等';
COMMENT ON COLUMN fetch_batch.remark IS '备注';

-- ========== 8. 索引 ==========
CREATE INDEX IF NOT EXISTS idx_news_event_ticker_publish_time
ON news_event (ticker, publish_time DESC);

CREATE INDEX IF NOT EXISTS idx_news_event_duplicate_status
ON news_event (duplicate_status);

CREATE INDEX IF NOT EXISTS idx_news_event_cluster_id
ON news_event (cluster_id);

CREATE INDEX IF NOT EXISTS idx_news_event_event_id
ON news_event (event_id);

CREATE INDEX IF NOT EXISTS idx_news_event_fetch_batch_id
ON news_event (fetch_batch_id);

CREATE INDEX IF NOT EXISTS idx_news_fingerprint_news_id
ON news_fingerprint (news_id);

CREATE INDEX IF NOT EXISTS idx_news_fingerprint_title_hash
ON news_fingerprint (title_hash);

CREATE INDEX IF NOT EXISTS idx_news_fingerprint_simhash
ON news_fingerprint (simhash);

CREATE INDEX IF NOT EXISTS idx_news_cluster_ticker
ON news_cluster (ticker);

CREATE INDEX IF NOT EXISTS idx_event_group_ticker
ON event_group (ticker);

CREATE INDEX IF NOT EXISTS idx_event_news_mapping_event_id
ON event_news_mapping (event_id);

CREATE INDEX IF NOT EXISTS idx_event_news_mapping_news_id
ON event_news_mapping (news_id);

CREATE INDEX IF NOT EXISTS idx_fetch_batch_ticker
ON fetch_batch (ticker);

CREATE INDEX IF NOT EXISTS idx_fetch_batch_fetch_time
ON fetch_batch (fetch_time DESC);
