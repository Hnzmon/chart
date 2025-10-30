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

@app.get("/api/stock-info/{stock_code}")
def get_stock_info(stock_code: str):
    """指定された銘柄の基本情報を取得"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # 銘柄コードから.Tなどのサフィックスを除去
        clean_code = stock_code.replace('.T', '').replace('.JP', '')
        
        # 銘柄情報を取得
        query = """
        SELECT 
            code,
            name,
            market,
            sector
        FROM stock_master 
        WHERE code = %s
        """
        
        cursor.execute(query, (clean_code,))
        result = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"銘柄コード {stock_code} の情報が見つかりません")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"銘柄情報取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"銘柄情報の取得に失敗しました: {str(e)}")

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

@app.get("/api/hammer-signals")
def get_hammer_signals():
    """最新のハンマーシグナル検出結果を取得"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # 最新のsignal_dateを取得
        cursor.execute("SELECT MAX(signal_date) as latest_date FROM signal_detections")
        latest_result = cursor.fetchone()
        latest_date = latest_result['latest_date']
        
        if not latest_date:
            return {"signals": [], "count": 0, "latest_date": None}
        
        # 最新日のシグナルを取得
        query = """
        SELECT 
            sd.symbol,
            sd.signal_date,
            sd.decline_days,
            sd.total_decline_pct,
            sd.lower_shadow_ratio,
            sd.detection_date,
            sm.name,
            sm.market,
            sm.sector
        FROM signal_detections sd
        LEFT JOIN stock_master sm ON REPLACE(sd.symbol, '.T', '') = sm.code
        WHERE sd.signal_date = %s
        ORDER BY sd.symbol
        """
        
        cursor.execute(query, (latest_date,))
        results = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return {
            "signals": results,
            "count": len(results),
            "latest_date": latest_date.isoformat() if latest_date else None
        }
        
    except Exception as e:
        print(f"ハンマーシグナル取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ハンマーシグナルの取得に失敗しました: {str(e)}")

@app.get("/api/hammer-signals/chart-data/{symbol}")
def get_hammer_signal_chart_data(symbol: str):
    """ハンマーシグナル銘柄の1年分チャートデータを取得"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # 1年分のデータを取得（今日から365日前まで）
        query = """
        SELECT 
            date,
            open,
            high,
            low,
            close,
            volume
        FROM stocks 
        WHERE symbol = %s 
        AND date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
        ORDER BY date ASC
        """
        
        cursor.execute(query, (symbol,))
        results = cursor.fetchall()
        
        # 銘柄情報も取得
        info_query = """
        SELECT name, market, sector 
        FROM stock_master 
        WHERE code = %s
        """
        cursor.execute(info_query, (symbol.replace('.T', ''),))
        stock_info = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        # 日付をISO形式に変換
        for row in results:
            row['date'] = row['date'].isoformat()
        
        return {
            "symbol": symbol,
            "stock_info": stock_info,
            "data": results,
            "count": len(results)
        }
        
    except Exception as e:
        print(f"チャートデータ取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"チャートデータの取得に失敗しました: {str(e)}")
