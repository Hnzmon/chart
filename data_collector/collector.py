import time
import requests
import mysql.connector
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

# ログの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_stock_data(symbol, period="1y"):
    """
    Yahoo Financeから株価データを取得
    :param symbol: 銘柄シンボル (例: "AAPL", "GOOGL")
    :param period: 取得期間 ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
    :return: データフレーム
    """
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=period)
        
        if data.empty:
            logger.error(f"データが取得できませんでした: {symbol}")
            return None
            
        logger.info(f"{symbol}のデータを取得しました: {len(data)}件")
        return data
        
    except Exception as e:
        logger.error(f"データ取得エラー ({symbol}): {e}")
        return None

def save_to_database(symbol, data):
    """
    株価データをMySQLに保存
    """
    conn = None
    try:
        conn = mysql.connector.connect(
            host='db',
            user='root',
            password='example',
            database='chart'
        )
        cursor = conn.cursor()
        
        # データを整形してINSERT
        for date, row in data.iterrows():
            insert_query = """
            INSERT INTO stocks (symbol, date, open, high, low, close, volume) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            open = VALUES(open),
            high = VALUES(high),
            low = VALUES(low),
            close = VALUES(close),
            volume = VALUES(volume)
            """
            
            values = (
                symbol,
                date.date(),
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                int(row['Volume'])
            )
            
            cursor.execute(insert_query, values)
        
        conn.commit()
        logger.info(f"{symbol}のデータを{len(data)}件保存しました")
        
    except Exception as e:
        logger.error(f"データベース保存エラー: {e}")
    finally:
        if conn:
            conn.close()

def test_single_stock():
    """
    単一銘柄のテスト取得
    """
    logger.info("=== 単一銘柄データ取得テスト開始 ===")
    
    # Appleの株価を取得
    symbol = "AAPL"
    logger.info(f"銘柄 {symbol} のデータを取得します...")
    
    data = fetch_stock_data(symbol, period="1mo")  # 過去1ヶ月
    
    if data is not None:
        logger.info(f"データ取得成功: {len(data)}件")
        logger.info(f"データ期間: {data.index[0]} - {data.index[-1]}")
        logger.info(f"最新の終値: ${data['Close'].iloc[-1]:.2f}")
        
        # データベースに保存
        save_to_database(symbol, data)
        
        logger.info("=== テスト完了 ===")
    else:
        logger.error("データ取得に失敗しました")

def main():
    logger.info("データコレクター開始")
    
    # 初回実行時に単一銘柄をテスト
    test_single_stock()
    
    # 定期実行ループ
    while True:
        logger.info("定期データ更新を実行...")
        
        # 主要銘柄のデータを更新
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        
        for symbol in symbols:
            logger.info(f"{symbol} データ更新中...")
            data = fetch_stock_data(symbol, period="5d")  # 過去5日分
            if data is not None:
                save_to_database(symbol, data)
            
            # レート制限のため少し待機
            time.sleep(2)
        
        logger.info(f"次回更新まで30分待機...")
        time.sleep(30 * 60)  # 30分ごとに実行

if __name__ == "__main__":
    main()
