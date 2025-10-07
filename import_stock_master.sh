#!/bin/bash
# 東証プライム銘柄マスター投入スクリプト
# 使用方法: ./import_stock_master.sh [mode]
# mode: skip(デフォルト) | update | replace

MODE=${1:-skip}  # 第1引数がなければ'skip'をデフォルトに

# ヘルプ表示
if [[ "$MODE" == "--help" || "$MODE" == "-h" ]]; then
    echo "東証プライム銘柄マスター投入スクリプト"
    echo ""
    echo "使用方法:"
    echo "  ./import_stock_master.sh [mode]"
    echo ""
    echo "モード:"
    echo "  skip     既存データがあればスキップ、新規のみ追加（デフォルト）"
    echo "  update   既存データがあれば更新、なければ追加"
    echo "  replace  既存データを完全に置き換え"
    echo ""
    echo "例:"
    echo "  ./import_stock_master.sh           # スキップモード"
    echo "  ./import_stock_master.sh skip      # スキップモード"
    echo "  ./import_stock_master.sh update    # 更新モード"
    echo "  ./import_stock_master.sh replace   # 置換モード"
    exit 0
fi

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
docker compose exec data_collector python stock_master_importer.py $MODE

echo "=== 銘柄マスター投入完了 ==="

# 投入されたデータの概要を表示
echo ""
echo "=== 投入データ概要 ==="
docker compose exec db mysql -u stock_user -pstock_password chart -e "
SELECT 
    COUNT(*) as total_stocks,
    COUNT(DISTINCT sector) as sectors,
    MIN(code) as min_code,
    MAX(code) as max_code
FROM stock_master;
"

echo ""
echo "=== 業種別銘柄数 ==="
docker compose exec db mysql -u stock_user -pstock_password chart -e "
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
docker compose exec db mysql -u stock_user -pstock_password chart -e "
SELECT 
    code,
    symbol,
    name,
    sector
FROM stock_master 
ORDER BY code 
LIMIT 10;
"