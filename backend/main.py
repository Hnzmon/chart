from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

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
    'collation': 'utf8mb4_unicode_ci',
    'use_unicode': True,
    'autocommit': True
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

@app.get("/api/test-date")
def test_date(date: Optional[str] = Query(None)):
    """dateパラメータのテスト用エンドポイント"""
    return {
        "received_date": date,
        "date_type": str(type(date)),
        "is_string": isinstance(date, str),
        "is_none": date is None
    }

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

@app.get("/api/hammer-signals/dates")
def get_hammer_signal_dates():
    """ハンマーシグナルが存在する日付一覧を取得（新しい順）"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT DISTINCT signal_date 
        FROM signal_detections 
        ORDER BY signal_date DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # 日付を適切な文字列形式に変換
        dates = []
        for row in results:
            date_value = row['signal_date']
            if isinstance(date_value, str):
                dates.append(date_value)
            elif hasattr(date_value, 'strftime'):
                dates.append(date_value.strftime('%Y-%m-%d'))
            else:
                dates.append(str(date_value))
        
        return {
            "dates": dates,
            "count": len(dates)
        }
        
    except Exception as e:
        print(f"ハンマーシグナル日付取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ハンマーシグナル日付の取得に失敗しました: {str(e)}")

@app.get("/api/hammer-signals")
def get_hammer_signals(date: Optional[str] = Query(None)):
    """指定日のハンマーシグナル検出結果を取得（dateが未指定の場合は最新日）"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # 指定された日付または最新日を取得
        if date:
            target_date = date
        else:
            cursor.execute("SELECT MAX(signal_date) as latest_date FROM signal_detections")
            latest_result = cursor.fetchone()
            target_date = latest_result['latest_date']
        
        if not target_date:
            return {"signals": [], "count": 0, "target_date": None}
        
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
        
        cursor.execute(query, (target_date,))
        results = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # 結果セットの全ての値を適切な型に変換（特に日付フィールド）
        for result in results:
            for key, value in result.items():
                if value is None:
                    continue
                elif key in ['signal_date', 'detection_date']:
                    if hasattr(value, 'strftime'):
                        result[key] = value.strftime('%Y-%m-%d' if key == 'signal_date' else '%Y-%m-%d %H:%M:%S')
                    else:
                        result[key] = str(value)
        
        # target_dateを適切な文字列形式で返す
        if isinstance(target_date, str):
            target_date_str = target_date
        elif hasattr(target_date, 'strftime'):
            target_date_str = target_date.strftime('%Y-%m-%d')
        else:
            target_date_str = str(target_date) if target_date else None
        
        return {
            "signals": results,
            "count": len(results),
            "target_date": target_date_str
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
        
        # 日付を適切な文字列形式に変換
        for row in results:
            date_value = row['date']
            if isinstance(date_value, str):
                row['date'] = date_value
            elif hasattr(date_value, 'strftime'):
                row['date'] = date_value.strftime('%Y-%m-%d')
            else:
                row['date'] = str(date_value)
        
        return {
            "symbol": symbol,
            "stock_info": stock_info,
            "data": results,
            "count": len(results)
        }
        
    except Exception as e:
        print(f"チャートデータ取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"チャートデータの取得に失敗しました: {str(e)}")
