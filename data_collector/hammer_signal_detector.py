#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下髭・連続下落シグナル検出バッチ
最新または1営業日前の下髭 + 3営業日以上の連続下落を検出
"""

import mysql.connector
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
import sys
import argparse

# 親ディレクトリをパスに追加（business_day_utilsを使用するため）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_collector.business_day_utils import BusinessDayCalculator

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HammerSignalDetector:
    def __init__(self):
        """下髭シグナル検出クラス"""
        self.business_day_calc = BusinessDayCalculator()
        
        # 連続下落の最低日数
        self.min_decline_days = 4  # 最低4営業日の連続下落
        
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

    def get_target_dates(self) -> List[str]:
        """
        検査対象日を取得（最新日と1営業日前）
        
        Returns:
            検査対象日のリスト
        """
        latest_business_day = self.business_day_calc.get_latest_business_day()
        
        # 1営業日前を計算
        prev_business_day = latest_business_day - timedelta(days=1)
        while not self.business_day_calc.is_business_day(prev_business_day):
            prev_business_day -= timedelta(days=1)
        
        target_dates = [
            self.business_day_calc.format_date(latest_business_day),
            self.business_day_calc.format_date(prev_business_day)
        ]
        
        logger.info(f"検査対象日: {target_dates}")
        return target_dates

    def get_all_symbols(self) -> List[str]:
        """すべての銘柄コードを取得"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            query = """
            SELECT DISTINCT symbol 
            FROM stocks 
            WHERE symbol IS NOT NULL 
            ORDER BY symbol
            """
            cursor.execute(query)
            symbols = [row[0] for row in cursor.fetchall()]
            logger.info(f"検査対象銘柄数: {len(symbols)}")
            return symbols
            
        finally:
            cursor.close()
            conn.close()

    def get_stock_data(self, symbol: str, start_date: str, limit: int = 20) -> pd.DataFrame:
        """
        指定銘柄の株価データを取得
        
        Args:
            symbol: 銘柄コード
            start_date: 開始日（この日以前のデータを取得）
            limit: 取得件数上限
        """
        conn = self.get_db_connection()
        
        try:
            query = """
            SELECT date, open, high, low, close, volume
            FROM stocks 
            WHERE symbol = %s 
              AND date <= %s
            ORDER BY date DESC 
            LIMIT %s
            """
            df = pd.read_sql(query, conn, params=(symbol, start_date, limit))
            
            if not df.empty:
                # 日付順に並び替え（古い順）
                df = df.sort_values('date').reset_index(drop=True)
                
            return df
            
        finally:
            conn.close()

    def is_hammer_candle(self, row: pd.Series) -> Tuple[bool, Dict]:
        """
        下髭（ハンマー）の判定
        要件: lowよりもcloseの値が高く、その差がopenとhighの差と同じか大きい
        
        Args:
            row: 株価データの1行
            
        Returns:
            (is_hammer, metrics)
        """
        open_price = float(row['open'])
        high_price = float(row['high'])
        low_price = float(row['low'])
        close_price = float(row['close'])
        
        # 全体の値幅
        total_range = high_price - low_price
        if total_range == 0:
            return False, {}
        
        # 実体（始値と終値の差）
        body_size = abs(close_price - open_price)
        
        # 上髭と下髭の計算
        upper_shadow = high_price - max(open_price, close_price)
        lower_shadow = min(open_price, close_price) - low_price
        
        # 比率計算
        lower_shadow_ratio = lower_shadow / total_range
        upper_shadow_ratio = upper_shadow / total_range
        body_ratio = body_size / total_range
        
        # 要件に基づく下髭判定条件
        close_low_diff = close_price - low_price  # 終値と安値の差
        high_open_diff = high_price - open_price  # 高値と始値の差
        
        is_hammer = (
            close_price > low_price and  # lowよりもcloseの値が高い
            close_low_diff >= high_open_diff  # その差がopenとhighの差と同じか大きい
        )
        
        metrics = {
            'lower_shadow_ratio': round(lower_shadow_ratio * 100, 2),
            'upper_shadow_ratio': round(upper_shadow_ratio * 100, 2),
            'body_ratio': round(body_ratio * 100, 2),
            'total_range': total_range,
            'lower_shadow': lower_shadow,
            'upper_shadow': upper_shadow,
            'body_size': body_size,
            'close_low_diff': close_low_diff,
            'high_open_diff': high_open_diff,
            'hammer_condition_met': close_low_diff >= high_open_diff
        }
        
        return is_hammer, metrics

    def check_consecutive_decline(self, df: pd.DataFrame, hammer_index: int) -> Tuple[bool, Dict]:
        """
        連続下落の確認
        要件: 下髭より前の日足が4営業日以上連続して下落している
        
        Args:
            df: 株価データ
            hammer_index: 下髭の位置
            
        Returns:
            (is_consecutive_decline, decline_info)
        """
        if hammer_index < self.min_decline_days:
            return False, {}
        
        # 下髭の前日から遡って連続下落をチェック
        decline_days = 0
        
        # 下髭の前日から遡る
        for i in range(hammer_index - 1, 0, -1):  # hammer_index-1から1まで（0は除く）
            current_close = float(df.iloc[i]['close'])
            prev_close = float(df.iloc[i - 1]['close'])
            
            # 前日より下落している場合
            if current_close < prev_close:
                decline_days += 1
            else:
                # 下落が止まったら終了
                break
        
        is_consecutive_decline = decline_days >= self.min_decline_days
        
        decline_info = {}
        if is_consecutive_decline:
            # 下落開始日のインデックス
            decline_start_index = hammer_index - 1 - decline_days
            
            start_price = float(df.iloc[decline_start_index]['close'])
            end_price = float(df.iloc[hammer_index - 1]['close'])  # 下髭の前日
            total_decline_pct = ((start_price - end_price) / start_price) * 100
            
            decline_info = {
                'decline_days': decline_days,
                'decline_start_date': df.iloc[decline_start_index]['date'],
                'decline_start_price': start_price,
                'decline_end_price': end_price,
                'total_decline_pct': round(total_decline_pct, 2)
            }
        
        return is_consecutive_decline, decline_info

    def get_stock_info(self, symbol: str) -> Dict:
        """銘柄情報を取得"""
        conn = self.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = """
            SELECT name, sector, market 
            FROM stock_master 
            WHERE symbol = %s
            """
            cursor.execute(query, (symbol,))
            result = cursor.fetchone()
            return result or {}
            
        finally:
            cursor.close()
            conn.close()

    def save_signal(self, signal_data: Dict):
        """シグナルをデータベースに保存"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            query = """
            INSERT INTO signal_detections (
                symbol, signal_date, signal_type, detection_date,
                hammer_open, hammer_high, hammer_low, hammer_close, hammer_volume,
                lower_shadow_ratio, upper_shadow_ratio, body_ratio,
                decline_days, decline_start_date, total_decline_pct,
                stock_name, market, sector
            ) VALUES (
                %(symbol)s, %(signal_date)s, %(signal_type)s, NOW(),
                %(hammer_open)s, %(hammer_high)s, %(hammer_low)s, %(hammer_close)s, %(hammer_volume)s,
                %(lower_shadow_ratio)s, %(upper_shadow_ratio)s, %(body_ratio)s,
                %(decline_days)s, %(decline_start_date)s, %(total_decline_pct)s,
                %(stock_name)s, %(market)s, %(sector)s
            )
            ON DUPLICATE KEY UPDATE
                detection_date = NOW(),
                lower_shadow_ratio = VALUES(lower_shadow_ratio),
                upper_shadow_ratio = VALUES(upper_shadow_ratio),
                body_ratio = VALUES(body_ratio),
                decline_days = VALUES(decline_days),
                total_decline_pct = VALUES(total_decline_pct)
            """
            
            cursor.execute(query, signal_data)
            conn.commit()
            
        finally:
            cursor.close()
            conn.close()

    def detect_signals(self, test_mode: bool = False):
        """メイン検出処理"""
        logger.info("=== 下髭・連続下落シグナル検出開始 ===")
        
        target_dates = self.get_target_dates()
        symbols = self.get_all_symbols()
        
        if test_mode:
            symbols = symbols[:10]  # テスト時は10銘柄のみ
            logger.info(f"テストモード: {len(symbols)}銘柄のみ処理")
        
        signals_found = 0
        processed_count = 0
        
        for symbol in symbols:
            try:
                processed_count += 1
                
                # 進捗表示
                if processed_count % 100 == 0:
                    logger.info(f"処理進捗: {processed_count}/{len(symbols)} ({processed_count/len(symbols)*100:.1f}%)")
                
                # 各検査対象日について確認
                for target_date in target_dates:
                    # 株価データ取得（検査日の20営業日前まで）
                    df = self.get_stock_data(symbol, target_date, 20)
                    
                    if df.empty or len(df) < self.min_decline_days + 1:
                        continue
                    
                    # 最新の日が下髭かチェック
                    latest_row = df.iloc[-1]
                    if str(latest_row['date']) != target_date:
                        continue  # 対象日のデータが存在しない
                    
                    is_hammer, hammer_metrics = self.is_hammer_candle(latest_row)
                    
                    if is_hammer:
                        # 連続下落チェック
                        hammer_index = len(df) - 1
                        is_decline, decline_info = self.check_consecutive_decline(df, hammer_index)
                        
                        if is_decline:
                            # 銘柄情報取得
                            stock_info = self.get_stock_info(symbol)
                            
                            # シグナルデータ作成
                            signal_data = {
                                'symbol': symbol,
                                'signal_date': target_date,
                                'signal_type': 'hammer_after_decline',
                                'hammer_open': float(latest_row['open']),
                                'hammer_high': float(latest_row['high']),
                                'hammer_low': float(latest_row['low']),
                                'hammer_close': float(latest_row['close']),
                                'hammer_volume': int(latest_row['volume']),
                                'lower_shadow_ratio': hammer_metrics['lower_shadow_ratio'],
                                'upper_shadow_ratio': hammer_metrics['upper_shadow_ratio'],
                                'body_ratio': hammer_metrics['body_ratio'],
                                'decline_days': decline_info['decline_days'],
                                'decline_start_date': decline_info['decline_start_date'],
                                'total_decline_pct': decline_info['total_decline_pct'],
                                'stock_name': stock_info.get('name'),
                                'market': stock_info.get('market'),
                                'sector': stock_info.get('sector')
                            }
                            
                            # データベースに保存
                            self.save_signal(signal_data)
                            signals_found += 1
                            
                            logger.info(f"シグナル検出: {symbol} ({target_date}) - "
                                      f"下落{decline_info['decline_days']}日 "
                                      f"close-low:{hammer_metrics['close_low_diff']:.2f} "
                                      f"high-open:{hammer_metrics['high_open_diff']:.2f}")
                            
                            # 1つ見つかったら次の銘柄へ（同じ銘柄で複数日検出を避ける）
                            break
                    
            except Exception as e:
                logger.error(f"銘柄 {symbol} の処理でエラー: {e}")
                continue
        
        logger.info("=== 検出完了 ===")
        logger.info(f"処理銘柄数: {processed_count}")
        logger.info(f"シグナル検出数: {signals_found}")
        
        return signals_found

def main():
    parser = argparse.ArgumentParser(description='下髭・連続下落シグナル検出')
    parser.add_argument('--test', action='store_true', help='テストモード（10銘柄のみ）')
    parser.add_argument('--create-table', action='store_true', help='テーブル作成')
    
    args = parser.parse_args()
    
    detector = HammerSignalDetector()
    
    if args.create_table:
        logger.info("テーブル作成モード")
        # テーブル作成SQLを実行
        sql_file = os.path.join(os.path.dirname(__file__), '..', 'sql', 'create_signal_detections_table.sql')
        if os.path.exists(sql_file):
            conn = detector.get_db_connection()
            cursor = conn.cursor()
            try:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql = f.read()
                cursor.execute(sql)
                conn.commit()
                logger.info("テーブル作成完了")
            except Exception as e:
                logger.error(f"テーブル作成エラー: {e}")
            finally:
                cursor.close()
                conn.close()
        return
    
    # シグナル検出実行
    signals_count = detector.detect_signals(test_mode=args.test)
    
    if signals_count > 0:
        logger.info(f"✅ {signals_count}件のシグナルを検出しました")
    else:
        logger.info("❌ 条件に該当するシグナルは見つかりませんでした")

if __name__ == "__main__":
    main()