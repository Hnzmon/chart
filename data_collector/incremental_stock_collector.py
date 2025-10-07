#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
差分更新対応株価データ取得スクリプト
既存データの最新日から実行日までの差分のみを効率的に取得
"""

import yfinance as yf
import pandas as pd
import time
import logging
from datetime import datetime, timedelta
import mysql.connector
import os
import sys
from typing import List, Dict, Optional, Tuple
from business_day_utils import BusinessDayCalculator

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('incremental_stock_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IncrementalStockCollector:
    def __init__(self, delay_seconds=1.0, batch_size=50, max_retries=3, test_limit=None):
        """
        差分更新対応株価データ取得クラス
        
        Args:
            delay_seconds: リクエスト間の待機時間（秒）
            batch_size: バッチサイズ
            max_retries: 最大リトライ回数
            test_limit: テスト用の処理銘柄数制限
        """
        self.delay_seconds = delay_seconds
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.base_start_date = "2025-01-06"  # 2025年大発会
        self.test_limit = test_limit
        self.business_day_calc = BusinessDayCalculator()
        
    def get_db_connection(self):
        """データベース接続を取得"""
        return mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'stock_user'),
            password=os.getenv('DB_PASSWORD', 'stock_password'),
            database=os.getenv('DB_NAME', 'chart'),
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )

    def get_all_stocks_from_master(self) -> List[Dict]:
        """マスターテーブルから全銘柄を取得"""
        conn = self.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = """
            SELECT code, symbol, name, sector 
            FROM stock_master 
            ORDER BY code
            """
            cursor.execute(query)
            stocks = cursor.fetchall()
            logger.info(f"マスターから{len(stocks)}銘柄を取得しました")
            return stocks
            
        finally:
            cursor.close()
            conn.close()

    def get_stock_date_range(self, symbol: str) -> Tuple[Optional[str], Optional[str]]:
        """
        銘柄の既存データの日付範囲を取得
        
        Returns:
            (start_date, end_date) または (None, None)
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            query = """
            SELECT 
                MIN(date) as start_date,
                MAX(date) as end_date,
                COUNT(*) as record_count
            FROM stocks 
            WHERE symbol = %s
            """
            cursor.execute(query, (symbol,))
            result = cursor.fetchone()
            
            if result and result[2] > 0:  # record_count > 0
                return result[0].strftime('%Y-%m-%d'), result[1].strftime('%Y-%m-%d')
            else:
                return None, None
            
        finally:
            cursor.close()
            conn.close()

    def calculate_fetch_period(self, symbol: str, target_end_date: str) -> Tuple[str, str, str]:
        """
        取得すべき期間を計算
        
        Args:
            symbol: 銘柄シンボル
            target_end_date: 目標終了日（通常は実行日）
            
        Returns:
            (fetch_start_date, fetch_end_date, status)
            status: 'new', 'update', 'skip'
        """
        existing_start, existing_end = self.get_stock_date_range(symbol)
        
        if existing_start is None:
            # 新規取得: 2025/01/06から実行日まで
            return self.base_start_date, target_end_date, 'new'
        
        # 既存データあり
        existing_end_date = datetime.strptime(existing_end, '%Y-%m-%d')
        target_end_date_obj = datetime.strptime(target_end_date, '%Y-%m-%d')
        
        if existing_end_date >= target_end_date_obj:
            # 既存データが最新: スキップ
            return existing_end, target_end_date, 'skip'
        
        # 差分更新: 既存の最新日の翌日から実行日まで
        next_day = existing_end_date + timedelta(days=1)
        fetch_start = next_day.strftime('%Y-%m-%d')
        
        return fetch_start, target_end_date, 'update'

    def fetch_stock_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        単一銘柄のデータを安全に取得
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"データ取得中: {symbol} ({start_date} ～ {end_date}) "
                           f"(試行 {attempt + 1}/{self.max_retries})")
                
                ticker = yf.Ticker(symbol)
                data = ticker.history(start=start_date, end=end_date)
                
                if data.empty:
                    logger.debug(f"データなし: {symbol} ({start_date} ～ {end_date})")
                    return None
                
                logger.debug(f"取得成功: {symbol} ({len(data)}件)")
                return data
                
            except Exception as e:
                logger.warning(f"取得エラー {symbol} (試行 {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.debug(f"リトライまで{wait_time}秒待機...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"最大リトライ回数に達しました: {symbol}")
        
        return None

    def save_stock_data(self, symbol: str, data: pd.DataFrame) -> bool:
        """株価データをデータベースに保存"""
        if data.empty:
            return True
            
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            records = []
            for date, row in data.iterrows():
                records.append({
                    'symbol': symbol,
                    'date': date.strftime('%Y-%m-%d'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume'])
                })
            
            query = """
            INSERT INTO stocks (symbol, date, open, high, low, close, volume)
            VALUES (%(symbol)s, %(date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
            ON DUPLICATE KEY UPDATE
            open = VALUES(open),
            high = VALUES(high),
            low = VALUES(low),
            close = VALUES(close),
            volume = VALUES(volume)
            """
            
            cursor.executemany(query, records)
            conn.commit()
            logger.debug(f"データベース保存完了: {symbol} ({len(records)}件)")
            return True
            
        except Exception as e:
            logger.error(f"データベース保存エラー {symbol}: {e}")
            return False
            
        finally:
            cursor.close()
            conn.close()

    def get_data_statistics(self):
        """現在のデータ統計を取得"""
        conn = self.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 全体統計
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT symbol) as unique_stocks,
                    COUNT(*) as total_records,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM stocks
            """)
            overall_stats = cursor.fetchone()
            
            # 銘柄別最新日統計
            cursor.execute("""
                SELECT 
                    date as latest_date,
                    COUNT(*) as stock_count
                FROM (
                    SELECT symbol, MAX(date) as date
                    FROM stocks
                    GROUP BY symbol
                ) as latest_by_stock
                GROUP BY date
                ORDER BY date DESC
                LIMIT 5
            """)
            latest_dates = cursor.fetchall()
            
            return overall_stats, latest_dates
            
        finally:
            cursor.close()
            conn.close()

    def collect_incremental_data(self, target_end_date: Optional[str] = None):
        """
        差分データを効率的に取得
        
        Args:
            target_end_date: 目標終了日（Noneの場合は実行日）
        """
        if target_end_date is None:
            # 実行日の直近営業日を取得
            business_date = self.business_day_calc.get_latest_business_day()
            target_end_date = self.business_day_calc.format_date(business_date)
        else:
            # 指定日の直近営業日を取得
            business_date = self.business_day_calc.get_latest_business_day(target_end_date)
            target_end_date = self.business_day_calc.format_date(business_date)
            
        logger.info("=== 差分株価データ取得開始 ===")
        logger.info(f"基準開始日: {self.base_start_date}")
        logger.info(f"目標終了日: {target_end_date} (営業日調整済み)")
        logger.info(f"リクエスト間隔: {self.delay_seconds}秒")
        
        # 現在のデータ統計
        overall_stats, latest_dates = self.get_data_statistics()
        logger.info("=== 現在のデータ統計 ===")
        logger.info(f"登録銘柄数: {overall_stats.get('unique_stocks', 0)}")
        logger.info(f"総レコード数: {overall_stats.get('total_records', 0):,}")
        if overall_stats.get('earliest_date'):
            logger.info(f"最古データ: {overall_stats['earliest_date']}")
            logger.info(f"最新データ: {overall_stats['latest_date']}")
        
        logger.info("=== 最新日別銘柄数 ===")
        for stat in latest_dates:
            logger.info(f"{stat['latest_date']}: {stat['stock_count']}銘柄")
        
        # 全銘柄取得
        all_stocks = self.get_all_stocks_from_master()
        if not all_stocks:
            logger.error("銘柄マスターが空です")
            return
            
        # テスト制限の適用
        if self.test_limit is not None:
            all_stocks = all_stocks[:self.test_limit]
            logger.info(f"テストモード: 最初の{len(all_stocks)}銘柄のみ処理します")
        
        # 処理計画の分析
        new_stocks = 0
        update_stocks = 0
        skip_stocks = 0
        total_expected_days = 0
        
        logger.info("=== 処理計画の分析中... ===")
        
        for i, stock in enumerate(all_stocks):
            if i % 100 == 0:
                logger.info(f"分析進捗: {i+1}/{len(all_stocks)}")
                
            symbol = stock['symbol']
            fetch_start, fetch_end, status = self.calculate_fetch_period(symbol, target_end_date)
            
            if status == 'new':
                new_stocks += 1
                # 2025/01/06から実行日までの営業日数を概算
                days = (datetime.strptime(target_end_date, '%Y-%m-%d') - 
                       datetime.strptime(self.base_start_date, '%Y-%m-%d')).days
                total_expected_days += days
            elif status == 'update':
                update_stocks += 1
                # 差分日数を概算
                days = (datetime.strptime(fetch_end, '%Y-%m-%d') - 
                       datetime.strptime(fetch_start, '%Y-%m-%d')).days
                total_expected_days += days
            else:
                skip_stocks += 1
        
        logger.info("=== 処理計画 ===")
        logger.info(f"新規取得: {new_stocks}銘柄")
        logger.info(f"差分更新: {update_stocks}銘柄")
        logger.info(f"スキップ: {skip_stocks}銘柄")
        logger.info(f"処理対象: {new_stocks + update_stocks}銘柄")
        logger.info(f"推定データ量: {total_expected_days:,}レコード")
        
        estimated_time = (new_stocks + update_stocks) * self.delay_seconds
        logger.info(f"推定処理時間: {estimated_time/60:.1f}分")
        
        # 実際の処理開始
        logger.info("=== 実際の処理開始 ===")
        
        processed_stocks = 0
        successful_new = 0
        successful_update = 0
        failed_stocks = 0
        total_new_records = 0
        
        for batch_start in range(0, len(all_stocks), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(all_stocks))
            batch_stocks = all_stocks[batch_start:batch_end]
            
            logger.info(f"=== バッチ {batch_start//self.batch_size + 1} "
                       f"({batch_start + 1}-{batch_end}/{len(all_stocks)}) ===")
            
            for stock in batch_stocks:
                symbol = stock['symbol']
                name = stock['name']
                processed_stocks += 1
                
                try:
                    # 取得期間計算
                    fetch_start, fetch_end, status = self.calculate_fetch_period(symbol, target_end_date)
                    
                    if status == 'skip':
                        logger.debug(f"スキップ ({processed_stocks}/{len(all_stocks)}): {name} ({symbol})")
                        continue
                    
                    # データ取得
                    logger.info(f"処理中 ({processed_stocks}/{len(all_stocks)}): "
                               f"{name} ({symbol}) [{status}] {fetch_start}～{fetch_end}")
                    
                    data = self.fetch_stock_data(symbol, fetch_start, fetch_end)
                    
                    if data is not None and not data.empty:
                        # データ保存
                        if self.save_stock_data(symbol, data):
                            if status == 'new':
                                successful_new += 1
                                logger.info(f"✅ 新規: {name} ({symbol}) {len(data)}件")
                            else:
                                successful_update += 1
                                logger.info(f"🔄 更新: {name} ({symbol}) {len(data)}件")
                            total_new_records += len(data)
                        else:
                            failed_stocks += 1
                            logger.error(f"❌ 保存失敗: {name} ({symbol})")
                    else:
                        if status == 'new':
                            logger.warning(f"⚠️  データなし: {name} ({symbol})")
                        else:
                            logger.info(f"ℹ️  差分なし: {name} ({symbol})")
                
                except Exception as e:
                    failed_stocks += 1
                    logger.error(f"❌ エラー: {name} ({symbol}) - {e}")
                
                # 進捗表示
                if processed_stocks % 50 == 0:
                    progress = (processed_stocks / len(all_stocks)) * 100
                    logger.info(f"進捗: {progress:.1f}% "
                               f"(新規:{successful_new}, 更新:{successful_update}, "
                               f"失敗:{failed_stocks}, 新レコード:{total_new_records:,})")
                
                # 待機
                if processed_stocks < len(all_stocks):
                    time.sleep(self.delay_seconds)
        
        # 最終結果
        logger.info("=== 差分取得完了 ===")
        logger.info(f"処理済み銘柄: {processed_stocks}")
        logger.info(f"新規取得成功: {successful_new}")
        logger.info(f"差分更新成功: {successful_update}")
        logger.info(f"失敗: {failed_stocks}")
        logger.info(f"新規追加レコード: {total_new_records:,}件")
        
        # 最終統計
        final_stats, _ = self.get_data_statistics()
        logger.info("=== 更新後データ統計 ===")
        logger.info(f"総銘柄数: {final_stats.get('unique_stocks', 0)}")
        logger.info(f"総レコード数: {final_stats.get('total_records', 0):,}")
        logger.info(f"最新データ: {final_stats.get('latest_date', 'N/A')}")

def main():
    """メイン処理"""
    # 設定
    delay_seconds = 1.0
    batch_size = 50
    target_date = None  # Noneで実行日
    test_limit = None
    
    # コマンドライン引数
    if len(sys.argv) > 1:
        if "--fast" in sys.argv:
            delay_seconds = 0.5
            logger.warning("⚠️  高速モード: 0.5秒間隔")
        elif "--slow" in sys.argv:
            delay_seconds = 2.0
            logger.info("🐌 安全モード: 2秒間隔")
        
        if "--date" in sys.argv:
            try:
                date_idx = sys.argv.index("--date")
                target_date = sys.argv[date_idx + 1]
                logger.info(f"📅 指定日まで取得: {target_date}")
            except (ValueError, IndexError):
                logger.error("--date オプションには日付を指定してください (YYYY-MM-DD)")
                return
        
        if "--batch" in sys.argv:
            try:
                batch_idx = sys.argv.index("--batch")
                batch_size = int(sys.argv[batch_idx + 1])
                logger.info(f"📦 バッチサイズ: {batch_size}")
            except (ValueError, IndexError):
                logger.error("--batch オプションには数値を指定してください")
                return
        
        if "--test-limit" in sys.argv:
            try:
                limit_idx = sys.argv.index("--test-limit")
                test_limit = int(sys.argv[limit_idx + 1])
                logger.info(f"🧪 テスト制限: {test_limit}銘柄")
            except (ValueError, IndexError):
                logger.error("--test-limit オプションには数値を指定してください")
                return
    
    # コレクター実行
    collector = IncrementalStockCollector(
        delay_seconds=delay_seconds,
        batch_size=batch_size,
        test_limit=test_limit
    )
    
    collector.collect_incremental_data(target_date)

if __name__ == "__main__":
    main()