#!/bin/bash
# 東証プライム銘柄マスター投入スクリプト
# 使用方法: ./import_stock_master.sh [mode]
# mode: skip(デフォルト) | update | replace

MODE=${1:-skip}  # 第1引数がなければ'skip'をデフォルトに

echo "=== 東証プライム銘柄マスター投入開始（モード: $MODE） ==="

# モードの説明
case $MODE in
    "skip")
        echo "📝 モード: SKIP - 既存データがあればスキップ、新規のみ追加"
        ;;
    "update") 
        echo "📝 モード: UPDATE - 既存データがあれば更新、なければ追加"
        ;;
    "replace")
        echo "📝 モード: REPLACE - 既存データを完全に置き換え"
        ;;
    *)
        echo "❌ 無効なモード: $MODE"
        echo "使用可能なモード: skip, update, replace"
        exit 1
        ;;
esac

# 銘柄マスター投入を実行
docker-compose run --rm data_collector python stock_master_importer.py $MODE

echo "=== 銘柄マスター投入完了 ==="

# 投入されたデータの概要を表示
echo ""
echo "=== 投入データ概要 ==="
docker exec -it chart_db_1 mysql -u root -pexample chart -e "
SELECT 
    COUNT(*) as total_stocks,
    COUNT(DISTINCT sector) as sectors,
    MIN(code) as min_code,
    MAX(code) as max_code
FROM stock_master;
"

echo ""
echo "=== 業種別銘柄数 ==="
docker exec -it chart_db_1 mysql -u root -pexample chart -e "
SELECT 
    sector,
    COUNT(*) as count
FROM stock_master 
WHERE sector != '' 
GROUP BY sector 
ORDER BY count DESC 
LIMIT 10;
"

echo ""
echo "=== サンプル銘柄（先頭10件） ==="
docker exec -it chart_db_1 mysql -u root -pexample chart -e "
SELECT 
    code,
    symbol,
    name,
    sector
FROM stock_master 
ORDER BY code 
LIMIT 10;
"