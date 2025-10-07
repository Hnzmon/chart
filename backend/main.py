from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
from typing import List, Dict, Any

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # フロントエンドのURLを許可
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベース設定
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'chart'),
    'user': os.getenv('DB_USER', 'stock_user'),
    'password': os.getenv('DB_PASSWORD', 'stock_password'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def get_db_connection():
    """データベース接続を取得"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"データベース接続エラー: {e}")
        raise HTTPException(status_code=500, detail="データベース接続に失敗しました")

@app.get("/")
def read_root():
    return {"message": "Stock Chart API is running"}

@app.get("/api/stocks/{stock_code}")
def get_stock_data(stock_code: str):
    """指定された銘柄の株価データを取得"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # 過去1年分のデータを取得
        query = """
        SELECT 
            symbol as code,
            date,
            open,
            high,
            low,
            close,
            volume
        FROM stocks 
        WHERE symbol = %s 
        ORDER BY date ASC
        LIMIT 365
        """
        
        cursor.execute(query, (stock_code,))
        results = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        if not results:
            raise HTTPException(status_code=404, detail=f"銘柄コード {stock_code} のデータが見つかりません")
        
        # データを整形
        stock_data = []
        for row in results:
            stock_data.append({
                "date": row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], datetime) else str(row['date']),
                "open": float(row['open']) if row['open'] is not None else 0,
                "high": float(row['high']) if row['high'] is not None else 0,
                "low": float(row['low']) if row['low'] is not None else 0,
                "close": float(row['close']) if row['close'] is not None else 0,
                "volume": int(row['volume']) if row['volume'] is not None else 0
            })
        
        return {
            "code": stock_code,
            "data": stock_data,
            "count": len(stock_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"API エラー: {e}")
        raise HTTPException(status_code=500, detail=f"データ取得中にエラーが発生しました: {str(e)}")

@app.get("/api/stocks")
def list_available_stocks():
    """利用可能な銘柄一覧を取得"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT 
            sm.code,
            sm.name,
            sm.market,
            sm.sector,
            COUNT(s.id) as data_count,
            MAX(s.date) as latest_date
        FROM stock_master sm
        LEFT JOIN stocks s ON sm.code = s.code
        GROUP BY sm.code, sm.name, sm.market, sm.sector
        HAVING data_count > 0
        ORDER BY sm.code
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return {
            "stocks": results,
            "count": len(results)
        }
        
    except Exception as e:
        print(f"銘柄一覧取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"銘柄一覧の取得に失敗しました: {str(e)}")
