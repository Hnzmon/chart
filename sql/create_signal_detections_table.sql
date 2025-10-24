-- 下髭・連続下落シグナル検出結果テーブル
CREATE TABLE IF NOT EXISTS signal_detections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL COMMENT '銘柄コード',
    signal_date DATE NOT NULL COMMENT 'シグナル発生日（下髭の日）',
    signal_type VARCHAR(50) NOT NULL DEFAULT 'hammer_after_decline' COMMENT 'シグナル種別',
    detection_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '検出日時',
    
    -- 下髭情報
    hammer_open DECIMAL(10,2) NOT NULL COMMENT '下髭日の始値',
    hammer_high DECIMAL(10,2) NOT NULL COMMENT '下髭日の高値',
    hammer_low DECIMAL(10,2) NOT NULL COMMENT '下髭日の安値',
    hammer_close DECIMAL(10,2) NOT NULL COMMENT '下髭日の終値',
    hammer_volume BIGINT NOT NULL COMMENT '下髭日の出来高',
    
    -- 下髭の特徴値
    lower_shadow_ratio DECIMAL(5,2) NOT NULL COMMENT '下髭の比率 (下髭/(高値-安値))',
    upper_shadow_ratio DECIMAL(5,2) NOT NULL COMMENT '上髭の比率',
    body_ratio DECIMAL(5,2) NOT NULL COMMENT '実体の比率',
    
    -- 連続下落情報
    decline_days INT NOT NULL COMMENT '連続下落日数',
    decline_start_date DATE NOT NULL COMMENT '下落開始日',
    total_decline_pct DECIMAL(5,2) NOT NULL COMMENT '総下落率(%)',
    
    -- 株式情報
    stock_name VARCHAR(200) COMMENT '銘柄名',
    market VARCHAR(50) COMMENT '市場',
    sector VARCHAR(100) COMMENT 'セクター',
    
    -- インデックス
    INDEX idx_symbol_date (symbol, signal_date),
    INDEX idx_detection_date (detection_date),
    INDEX idx_signal_type (signal_type),
    
    -- 重複防止
    UNIQUE KEY uk_symbol_signal_date (symbol, signal_date, signal_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='下髭・連続下落シグナル検出結果';