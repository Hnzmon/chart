#!/bin/bash

# 差分株価データ取得シェルスクリプト
# Usage: ./collect_stock_data.sh [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/data_collector/incremental_stock_collector.py"
LOG_FILE="$SCRIPT_DIR/stock_collection.log"

# 色付きメッセージ関数
print_info() {
    echo -e "\e[34m[INFO]\e[0m $1"
}

print_success() {
    echo -e "\e[32m[SUCCESS]\e[0m $1"
}

print_warning() {
    echo -e "\e[33m[WARNING]\e[0m $1"
}

print_error() {
    echo -e "\e[31m[ERROR]\e[0m $1"
}

print_header() {
    echo
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

# ヘルプメッセージ
show_help() {
    cat << EOF
株価データ差分取得スクリプト

使用方法:
  ./collect_stock_data.sh [オプション]

オプション:
  -h, --help          このヘルプを表示
  -f, --fast          高速モード (0.5秒間隔、注意: API制限リスクあり)
  -s, --slow          安全モード (2秒間隔)
  -d, --date DATE     指定日まで取得 (YYYY-MM-DD形式)
  -t, --test          テストモード (最初の10銘柄のみ)
  -q, --quiet         詳細ログを抑制
  -l, --log           ログファイルを表示
  --status            現在のデータ状況を表示
  --clean-log         ログファイルをクリア

例:
  ./collect_stock_data.sh                    # 標準モードで実行
  ./collect_stock_data.sh --fast             # 高速モード
  ./collect_stock_data.sh --date 2025-10-01  # 指定日まで
  ./collect_stock_data.sh --test             # テスト実行
  ./collect_stock_data.sh --status           # データ状況確認

EOF
}

# データ状況確認
check_status() {
    print_header "現在のデータ状況確認"
    
    if ! docker ps | grep -q chart-db-1; then
        print_error "MySQLコンテナが起動していません"
        print_info "docker compose up -d db を実行してください"
        exit 1
    fi
    
    # データベース統計取得
    docker exec chart-db-1 mysql -u stock_user -pstock_password -D chart -e "
        SELECT 
            COUNT(DISTINCT symbol) as '銘柄数',
            COUNT(*) as '総レコード数',
            MIN(date) as '最古データ',
            MAX(date) as '最新データ'
        FROM stocks;
        
        SELECT '=== 最新データ日別銘柄数 ===' as '';
        
        SELECT 
            latest_date as '日付',
            stock_count as '銘柄数'
        FROM (
            SELECT 
                MAX(date) as latest_date,
                COUNT(*) as stock_count
            FROM (
                SELECT symbol, MAX(date) as date
                FROM stocks
                GROUP BY symbol
            ) as latest_by_stock
            GROUP BY latest_date
            ORDER BY latest_date DESC
            LIMIT 10
        ) as stats;
    " 2>/dev/null || {
        print_warning "データベース接続エラー、または初回実行です"
        print_info "初回実行時は全銘柄の新規取得が行われます（推定27分）"
    }
}

# ログファイル表示
show_log() {
    if [[ -f "$LOG_FILE" ]]; then
        print_header "最新ログ (最後の50行)"
        tail -n 50 "$LOG_FILE"
    else
        print_warning "ログファイルが見つかりません: $LOG_FILE"
    fi
}

# ログファイルクリア
clean_log() {
    if [[ -f "$LOG_FILE" ]]; then
        > "$LOG_FILE"
        print_success "ログファイルをクリアしました"
    else
        print_info "ログファイルは存在しません"
    fi
}

# Python環境チェック
check_python_requirements() {
    print_info "Python環境をチェック中..."
    
    # Python3の確認
    if ! command -v python3 &> /dev/null; then
        print_error "python3が見つかりません"
        exit 1
    fi
    
    # 必要なパッケージの確認
    local missing_packages=()
    
    if ! python3 -c "import yfinance" 2>/dev/null; then
        missing_packages+=("yfinance")
    fi
    
    if ! python3 -c "import pandas" 2>/dev/null; then
        missing_packages+=("pandas")
    fi
    
    if ! python3 -c "import mysql.connector" 2>/dev/null; then
        missing_packages+=("mysql-connector-python")
    fi
    
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        print_error "必要なPythonパッケージが不足しています: ${missing_packages[*]}"
        print_info "以下のコマンドでインストールしてください:"
        print_info "pip3 install ${missing_packages[*]}"
        exit 1
    fi
    
    print_success "Python環境OK"
}

# Docker環境チェック
check_docker_environment() {
    print_info "Docker環境をチェック中..."
    
    # Dockerの確認
    if ! command -v docker &> /dev/null; then
        print_error "dockerが見つかりません"
        exit 1
    fi
    
    # MySQLコンテナの確認
    if ! docker ps | grep -q chart-db-1; then
        print_warning "MySQLコンテナが起動していません"
        print_info "MySQLコンテナを起動中..."
        
        if docker compose up -d db; then
            print_success "MySQLコンテナを起動しました"
            print_info "データベース初期化のため5秒待機..."
            sleep 5
        else
            print_error "MySQLコンテナの起動に失敗しました"
            exit 1
        fi
    else
        print_success "MySQLコンテナ稼働中"
    fi
}

# メイン処理
main() {
    local python_args=()
    local mode="standard"
    local target_date=""
    local test_mode=false
    local quiet_mode=false
    
    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -f|--fast)
                python_args+=("--fast")
                mode="fast"
                shift
                ;;
            -s|--slow)
                python_args+=("--slow")
                mode="slow"
                shift
                ;;
            -d|--date)
                if [[ -z "$2" ]] || [[ "$2" =~ ^- ]]; then
                    print_error "--date オプションには日付を指定してください (YYYY-MM-DD)"
                    exit 1
                fi
                python_args+=("--date" "$2")
                target_date="$2"
                shift 2
                ;;
            -t|--test)
                python_args+=("--test-limit" "10")
                test_mode=true
                shift
                ;;
            -q|--quiet)
                quiet_mode=true
                shift
                ;;
            -l|--log)
                show_log
                exit 0
                ;;
            --status)
                check_status
                exit 0
                ;;
            --clean-log)
                clean_log
                exit 0
                ;;
            *)
                print_error "不明なオプション: $1"
                print_info "ヘルプを表示するには --help を使用してください"
                exit 1
                ;;
        esac
    done
    
    # ヘッダー表示
    print_header "株価データ差分取得スクリプト"
    
    # 環境チェック
    check_python_requirements
    check_docker_environment
    
    # 実行設定表示
    print_info "実行設定:"
    print_info "  モード: $mode"
    if [[ -n "$target_date" ]]; then
        print_info "  指定日: $target_date"
    else
        print_info "  指定日: $(date '+%Y-%m-%d') (実行日)"
    fi
    print_info "  テスト: $test_mode"
    print_info "  ログファイル: $LOG_FILE"
    
    # テストモード時の警告
    if [[ "$test_mode" = true ]]; then
        print_warning "テストモードで実行します (最初の10銘柄のみ)"
    fi
    
    # 高速モード時の警告
    if [[ "$mode" = "fast" ]]; then
        print_warning "高速モードは API制限 のリスクがあります"
        print_info "5秒後に開始します... (Ctrl+Cでキャンセル)"
        sleep 5
    fi
    
    # 実行開始
    print_header "データ取得開始"
    print_info "開始時刻: $(date '+%Y-%m-%d %H:%M:%S')"
    
    local start_time=$(date +%s)
    
    # Pythonスクリプト実行
    if [[ "$quiet_mode" = true ]]; then
        if python3 "$PYTHON_SCRIPT" "${python_args[@]}" >> "$LOG_FILE" 2>&1; then
            local exit_status=0
        else
            local exit_status=$?
        fi
    else
        if python3 "$PYTHON_SCRIPT" "${python_args[@]}" | tee -a "$LOG_FILE"; then
            local exit_status=0
        else
            local exit_status=$?
        fi
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local duration_min=$((duration / 60))
    local duration_sec=$((duration % 60))
    
    # 結果表示
    print_header "実行完了"
    print_info "終了時刻: $(date '+%Y-%m-%d %H:%M:%S')"
    print_info "実行時間: ${duration_min}分${duration_sec}秒"
    
    if [[ $exit_status -eq 0 ]]; then
        print_success "株価データ取得が正常に完了しました"
        print_info "詳細ログ: $LOG_FILE"
        
        # 完了後の統計表示
        if [[ "$quiet_mode" = false ]]; then
            print_info ""
            check_status
        fi
    else
        print_error "株価データ取得中にエラーが発生しました (終了コード: $exit_status)"
        print_info "ログを確認してください: $LOG_FILE"
        print_info "または './collect_stock_data.sh --log' でログを表示"
        exit $exit_status
    fi
}

# スクリプト実行
main "$@"