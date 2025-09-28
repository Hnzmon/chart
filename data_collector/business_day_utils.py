#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
営業日判定ユーティリティ
土日祝日を考慮して直近の営業日を取得
"""

import pandas as pd
import requests
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class BusinessDayCalculator:
    def __init__(self, data_dir="data_collector"):
        """
        営業日計算クラス
        
        Args:
            data_dir: 祝日CSVを保存するディレクトリ
        """
        self.data_dir = data_dir
        self.holidays = set()
        self.current_year = datetime.now().year
        
    def download_holidays_csv(self, year):
        """
        内閣府から祝日CSVをダウンロード
        
        Args:
            year: 対象年
        """
        csv_path = os.path.join(self.data_dir, f"{year}.csv")
        
        # 既に存在する場合はスキップ
        if os.path.exists(csv_path):
            logger.info(f"祝日CSV既存: {csv_path}")
            return csv_path
        
        # ディレクトリ作成
        os.makedirs(self.data_dir, exist_ok=True)
        
        # CSVダウンロード
        url = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"
        
        try:
            logger.info(f"祝日CSVをダウンロード中: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # CSVファイルに保存
            with open(csv_path, 'wb') as f:
                f.write(response.content)
                
            logger.info(f"祝日CSV保存完了: {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"祝日CSVダウンロード失敗: {e}")
            raise
    
    def load_holidays(self, year):
        """
        祝日データを読み込み
        
        Args:
            year: 対象年
        """
        csv_path = self.download_holidays_csv(year)
        
        try:
            # CSVを読み込み（エンコーディングを複数試行）
            encodings = ['utf-8', 'shift_jis', 'cp932']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_path, encoding=encoding)
                    logger.info(f"祝日CSV読み込み成功: {encoding}エンコーディング")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError("祝日CSVの読み込みに失敗しました")
            
            # 祝日日付を抽出
            holidays = set()
            
            # CSVの最初のカラムが日付と仮定
            date_column = df.columns[0]
            
            for date_str in df[date_column]:
                try:
                    # 日付文字列を解析
                    if isinstance(date_str, str):
                        # YYYY/MM/DD, YYYY-MM-DD などの形式に対応
                        date_str = date_str.replace('/', '-')
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        # 指定年の祝日のみ追加
                        if date_obj.year == year:
                            holidays.add(date_obj)
                            
                except (ValueError, TypeError):
                    continue
            
            logger.info(f"{year}年の祝日を{len(holidays)}日読み込みました")
            self.holidays = holidays
            return holidays
            
        except Exception as e:
            logger.error(f"祝日データ読み込みエラー: {e}")
            # エラー時は空のセットを返す（土日のみ考慮）
            self.holidays = set()
            return set()
    
    def is_business_day(self, date_obj):
        """
        営業日判定
        
        Args:
            date_obj: datetime.date オブジェクト
            
        Returns:
            bool: 営業日の場合True
        """
        # 土日チェック（月曜=0, 火曜=1, ..., 土曜=5, 日曜=6）
        weekday = date_obj.weekday()
        if weekday == 5 or weekday == 6:  # 土曜=5, 日曜=6
            return False
        
        # 祝日チェック
        if date_obj in self.holidays:
            return False
        
        return True
    
    def get_latest_business_day(self, target_date=None):
        """
        指定日以前の直近営業日を取得
        
        Args:
            target_date: 基準日（Noneの場合は実行日）
            
        Returns:
            datetime.date: 直近営業日
        """
        if target_date is None:
            target_date = datetime.now().date()
        elif isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        # 対象年の祝日を読み込み
        if target_date.year != self.current_year or not self.holidays:
            self.load_holidays(target_date.year)
            self.current_year = target_date.year
        
        # 直近営業日を遡って検索
        check_date = target_date
        max_days_back = 10  # 最大10日遡る
        
        for i in range(max_days_back):
            if self.is_business_day(check_date):
                if check_date != target_date:
                    logger.info(f"営業日調整: {target_date} -> {check_date}")
                else:
                    logger.info(f"営業日確認: {check_date} (調整不要)")
                return check_date
            
            check_date -= timedelta(days=1)
        
        # 10日遡っても営業日が見つからない場合（通常ありえない）
        logger.warning(f"直近営業日が見つかりません: {target_date}")
        return target_date
    
    def get_business_days_until(self, start_date, end_date):
        """
        指定期間の営業日リストを取得
        
        Args:
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            List[datetime.date]: 営業日のリスト
        """
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # 年をまたぐ場合は両方の年の祝日を読み込み
        years = {start_date.year, end_date.year}
        for year in years:
            if year != self.current_year or not self.holidays:
                self.load_holidays(year)
        
        business_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if self.is_business_day(current_date):
                business_days.append(current_date)
            current_date += timedelta(days=1)
        
        return business_days
    
    def format_date(self, date_obj):
        """
        日付を文字列形式で返す
        
        Args:
            date_obj: datetime.date
            
        Returns:
            str: YYYY-MM-DD形式の日付文字列
        """
        return date_obj.strftime('%Y-%m-%d')

# テスト用の関数
def test_business_day_calculator():
    """営業日計算のテスト"""
    calc = BusinessDayCalculator()
    
    # テスト日付
    test_dates = [
        "2025-09-28",  # 土曜日
        "2025-09-29",  # 日曜日  
        "2025-09-30",  # 月曜日
        "2025-10-14",  # 体育の日（祝日）
        "2025-12-31",  # 大晦日
    ]
    
    print("=== 営業日判定テスト ===")
    for date_str in test_dates:
        target = datetime.strptime(date_str, '%Y-%m-%d').date()
        latest_business = calc.get_latest_business_day(target)
        is_business = calc.is_business_day(target)
        weekday = target.weekday()  # 0=月曜, 6=日曜
        weekday_names = ['月', '火', '水', '木', '金', '土', '日']
        
        print(f"{date_str} ({weekday_names[weekday]}曜日, weekday={weekday}) "
              f"-> {'営業日' if is_business else '非営業日'} -> 調整後: {latest_business}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_business_day_calculator()