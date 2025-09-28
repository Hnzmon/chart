#!/usr/bin/env python3
"""
東証プライム銘柄のマスターデータを取得・投入するスクリプト
"""
import pandas as pd
import mysql.connector
import requests
import yfinance as yf
import time
import logging
from datetime import datetime

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_prime_stocks_from_excel():
    """
    ローカルのExcelファイル（data_j.xls）から東証プライム銘柄一覧を取得
    """
    try:
        excel_path = "/app/data_j.xls"  # Dockerコンテナ内のパス
        logger.info(f"Excelファイルから銘柄一覧を読み込み中: {excel_path}")
        
        # Excelファイルを読み込み（複数のシート名の可能性を考慮）
        try:
            # 最初のシートを読み込み
            df = pd.read_excel(excel_path, sheet_name=0)
        except Exception as e:
            logger.error(f"Sheet1での読み込み失敗: {e}")
            # 他のシート名も試行
            df = pd.read_excel(excel_path)
        
        logger.info(f"読み込んだデータ: {len(df)}行, {len(df.columns)}列")
        logger.info(f"カラム名: {list(df.columns)}")
        
        # 東証プライムのみを抽出
        prime_df = None
        
        # 市場区分カラムを探す
        market_columns = [col for col in df.columns if '市場' in str(col) or 'Market' in str(col) or '区分' in str(col)]
        
        if market_columns:
            market_col = market_columns[0]
            logger.info(f"市場区分カラム: {market_col}")
            
            # プライム市場のデータを抽出
            prime_df = df[df[market_col].astype(str).str.contains('プライム|Prime', na=False)]
            logger.info(f"東証プライム銘柄数: {len(prime_df)}件")
        else:
            logger.warning("市場区分カラムが見つかりません。全銘柄を使用します")
            prime_df = df
        
        if len(prime_df) == 0:
            logger.warning("プライム銘柄が見つかりません。全銘柄を使用します")
            prime_df = df
        
        # データの前処理
        result_data = []
        for _, row in prime_df.iterrows():
            # 銘柄コードの取得（複数の可能性のあるカラム名を試行）
            code = None
            for code_col in ['銘柄コード', 'コード', 'Code', 'Symbol', '証券コード']:
                if code_col in row and pd.notna(row[code_col]):
                    code = str(row[code_col]).replace('.0', '').zfill(4)
                    break
            
            # 銘柄名の取得
            name = None
            for name_col in ['銘柄名', '会社名', 'Name', 'CompanyName', '銘柄略称']:
                if name_col in row and pd.notna(row[name_col]):
                    name = str(row[name_col])
                    break
            
            # 業種の取得
            sector = None
            for sector_col in ['業種', 'Sector', '33業種区分', '業種分類']:
                if sector_col in row and pd.notna(row[sector_col]):
                    sector = str(row[sector_col])
                    break
            
            if code and name:
                result_data.append({
                    'code': code,
                    'name': name,
                    'sector': sector or ''
                })
        
        result_df = pd.DataFrame(result_data)
        logger.info(f"処理後の銘柄数: {len(result_df)}件")
        return result_df
        
    except Exception as e:
        logger.error(f"Excelファイル読み込みエラー: {e}")
        return None



def validate_symbol_with_yfinance(symbol):
    """
    yfinanceでシンボルが有効かチェック
    """
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # 基本的な情報があるかチェック
        if info and len(info) > 10:
            return True, info.get('longName', ''), info.get('sector', '')
        return False, '', ''
        
    except Exception as e:
        return False, '', ''

def save_stock_master_to_db(df, mode='update'):
    """
    銘柄マスターデータをMySQLに保存
    
    :param df: 銘柄データのDataFrame
    :param mode: 保存モード
        - 'update': 既存データがあれば更新（デフォルト）
        - 'skip': 既存データがあればスキップ（新規のみ追加）
        - 'replace': 既存データを完全に置き換え
    """
    conn = None
    try:
        conn = mysql.connector.connect(
            host='db',
            user='root',
            password='example',
            database='chart',
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        cursor = conn.cursor()
        
        success_count = 0
        skip_count = 0
        existing_count = 0
        
        for _, row in df.iterrows():
            code = str(row['code']).zfill(4)  # 4桁にパディング
            symbol = f"{code}.T"
            name = row['name']
            sector = row.get('sector', '')
            
            # 既存データチェック（skipモードの場合）
            if mode == 'skip':
                check_query = "SELECT COUNT(*) FROM stock_master WHERE code = %s"
                cursor.execute(check_query, (code,))
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    existing_count += 1
                    logger.info(f"⏭️ スキップ（既存）: {code} ({name})")
                    continue
            
            # yfinanceでの有効性チェック
            logger.info(f"検証中: {code} ({name})")
            is_valid, name_en, yf_sector = validate_symbol_with_yfinance(symbol)
            
            if is_valid:
                if mode == 'update':
                    # 既存データがあれば更新、なければ挿入
                    insert_query = """
                    INSERT INTO stock_master (code, symbol, name, name_en, sector, industry) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    name_en = VALUES(name_en),
                    sector = VALUES(sector),
                    industry = VALUES(industry),
                    updated_at = CURRENT_TIMESTAMP
                    """
                elif mode == 'skip':
                    # 新規のみ挿入（重複は無視）
                    insert_query = """
                    INSERT IGNORE INTO stock_master (code, symbol, name, name_en, sector, industry) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                elif mode == 'replace':
                    # 既存データを完全に置き換え
                    delete_query = "DELETE FROM stock_master WHERE code = %s"
                    cursor.execute(delete_query, (code,))
                    
                    insert_query = """
                    INSERT INTO stock_master (code, symbol, name, name_en, sector, industry) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                
                values = (
                    code,
                    symbol, 
                    name,
                    name_en or '',
                    sector,
                    yf_sector or ''
                )
                
                cursor.execute(insert_query, values)
                success_count += 1
                logger.info(f"✅ 保存成功: {code} {name}")
            else:
                skip_count += 1
                logger.warning(f"⚠️ スキップ: {code} {name} (yfinanceで取得不可)")
            
            # レート制限対応
            time.sleep(0.5)
        
        conn.commit()
        
        total_processed = success_count + skip_count + existing_count
        logger.info(f"銘柄マスター保存完了:")
        logger.info(f"  - 成功: {success_count}件")
        logger.info(f"  - スキップ（yfinance無効）: {skip_count}件") 
        logger.info(f"  - スキップ（既存データ）: {existing_count}件")
        logger.info(f"  - 処理済み総数: {total_processed}件")
        
    except Exception as e:
        logger.error(f"データベース保存エラー: {e}")
    finally:
        if conn:
            conn.close()

def main():
    # コマンドライン引数からモードを取得
    import sys
    mode = 'skip'  # デフォルト
    if len(sys.argv) > 1:
        if sys.argv[1] in ['skip', 'update', 'replace']:
            mode = sys.argv[1]
        else:
            logger.error("無効なモード。使用可能: skip, update, replace")
            return
    
    logger.info(f"=== 東証プライム銘柄マスター投入開始（モード: {mode}） ===")
    
    # 1. ローカルExcelファイルから銘柄一覧取得
    df = get_prime_stocks_from_excel()
    
    if df is not None and len(df) > 0:
        # 2. データベースに保存
        save_stock_master_to_db(df, mode=mode)
        
        logger.info("=== 銘柄マスター投入完了 ===")
    else:
        logger.error("Excelファイルから銘柄データが取得できませんでした")

if __name__ == "__main__":
    main()