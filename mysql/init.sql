-- 株価データテーブル
CREATE TABLE IF NOT EXISTS stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open FLOAT,
    high FLOAT,
    low FLOAT,
    close FLOAT,
    volume BIGINT,
    UNIQUE KEY unique_stock_date (symbol, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 銘柄マスターテーブル（東証プライム）
CREATE TABLE IF NOT EXISTS stock_master (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,      -- 銘柄コード (例: "6501")
    symbol VARCHAR(15) NOT NULL UNIQUE,    -- yfinance用シンボル (例: "6501.T")
    name VARCHAR(255) NOT NULL,            -- 銘柄名 (例: "株式会社日立製作所")
    name_en VARCHAR(255),                  -- 英語名 (例: "Hitachi, Ltd.")
    market VARCHAR(50) DEFAULT 'プライム', -- 市場区分
    sector VARCHAR(100),                   -- 業種
    industry VARCHAR(100),                 -- 業界
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_code (code),
    INDEX idx_symbol (symbol),
    INDEX idx_sector (sector)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
