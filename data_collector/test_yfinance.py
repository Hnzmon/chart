#!/usr/bin/env python3
"""
yfinanceのAPIが使えるかをテストするスクリプト
"""
import yfinance as yf
from datetime import datetime

def test_yfinance():
    """
    yfinanceライブラリのテスト
    """
    print("=== yfinance APIテスト開始 ===")
    
    # Appleの株価を取得（テスト）
    symbol = "AAPL"
    print(f"銘柄: {symbol}")
    
    try:
        # Tickerオブジェクト作成
        stock = yf.Ticker(symbol)
        
        # 基本情報を取得
        info = stock.info
        print(f"企業名: {info.get('longName', 'N/A')}")
        print(f"セクター: {info.get('sector', 'N/A')}")
        print(f"現在価格: ${info.get('currentPrice', 'N/A')}")
        
        # 過去1ヶ月の株価データを取得
        data = stock.history(period="1mo")
        
        if not data.empty:
            print(f"\n取得データ数: {len(data)}件")
            print(f"データ期間: {data.index[0].date()} - {data.index[-1].date()}")
            print(f"最新終値: ${data['Close'][-1]:.2f}")
            
            # 最新5日分のデータを表示
            print("\n=== 最新5日分のデータ ===")
            latest_data = data.tail(5)
            for date, row in latest_data.iterrows():
                print(f"{date.date()}: 始値${row['Open']:.2f}, 高値${row['High']:.2f}, 安値${row['Low']:.2f}, 終値${row['Close']:.2f}, 出来高{int(row['Volume']):,}")
            
            print("\n✅ yfinance API正常動作確認")
        else:
            print("❌ データが取得できませんでした")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_yfinance()