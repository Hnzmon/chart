#!/bin/bash

# 下髭・連続下落シグナル検出バッチ
# Usage: ./detect_hammer_signals.sh [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/data_collector/hammer_signal_detector.py"
LOG_FILE="$SCRIPT_DIR/hammer_signal_detection.log"

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
下髭・連続下落シグナル検出バッチ

下記条件を満たす銘柄を検出します:
1. 最新または1営業日前の日足が下髭（ハンマー）
   - 終値が安値より高い (close > low)
   - 終値と安値の差 ≥ 高値と始値の差 (close-low ≥ high-open)

2. 下髭より前に4営業日以上の連続下落

使用方法:
  ./detect_hammer_signals.sh [オプション]

オプション:
  -h, --help          このヘルプを表示
  -t, --test          テストモード (最初の10銘柄のみ)
  -c, --create-table  テーブル作成
  -s, --show-results  検出結果を表示
  -q, --quiet         詳細ログを抑制

例:
  ./detect_hammer_signals.sh                # 通常実行
  ./detect_hammer_signals.sh --test         # テスト実行
  ./detect_hammer_signals.sh --create-table # テーブル作成
  ./detect_hammer_signals.sh --show-results # 結果表示

EOF
}

# 検出結果表示
show_results() {
    print_header "最新検出結果"
    
    # Docker環境でMySQLに接続して結果表示
    if command -v docker &> /dev/null && docker ps | grep -q chart-db-1; then
        print_info "検出結果を表示中..."
        
        docker exec chart-db-1 mysql -u stock_user -pstock_password chart -e "
        SELECT 
            symbol as '銘柄コード',
            signal_date as 'シグナル日',
            CONCAT(stock_name, ' (', market, ')') as '銘柄名',
            CONCAT(decline_days, '日') as '下落日数',
            CONCAT(total_decline_pct, '%') as '総下落率',
            CONCAT(lower_shadow_ratio, '%') as '下髭比率',
            detection_date as '検出日時'
        FROM signal_detections 
        ORDER BY detection_date DESC, total_decline_pct DESC 
        LIMIT 20;
        " 2>/dev/null || {
            print_warning "結果表示でエラーが発生しました"
            print_info "テーブルが存在しない可能性があります。--create-table オプションを試してください"
        }
    else
        print_error "MySQLコンテナが起動していません"
        print_info "docker compose up -d db を実行してください"
    fi
}

# 統計情報表示
show_stats() {
    print_info "検出統計:"
    
    if command -v docker &> /dev/null && docker ps | grep -q chart-db-1; then
        docker exec chart-db-1 mysql -u stock_user -pstock_password chart -e "
        SELECT 
            COUNT(*) as '総検出数',
            COUNT(DISTINCT symbol) as 'ユニーク銘柄数',
            AVG(decline_days) as '平均下落日数',
            AVG(total_decline_pct) as '平均下落率(%)',
            AVG(lower_shadow_ratio) as '平均下髭比率(%)',
            MAX(detection_date) as '最新検出日時'
        FROM signal_detections;
        " 2>/dev/null
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
    
    if ! python3 -c "import pandas" &> /dev/null; then
        missing_packages+=("pandas")
    fi
    
    if ! python3 -c "import mysql.connector" &> /dev/null; then
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
    local test_mode=false
    local create_table=false
    local show_results_flag=false
    local quiet_mode=false
    
    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -t|--test)
                python_args+=("--test")
                test_mode=true
                shift
                ;;
            -c|--create-table)
                python_args+=("--create-table")
                create_table=true
                shift
                ;;
            -s|--show-results)
                show_results_flag=true
                shift
                ;;
            -q|--quiet)
                quiet_mode=true
                shift
                ;;
            *)
                print_error "不明なオプション: $1"
                print_info "使用方法については --help を参照してください"
                exit 1
                ;;
        esac
    done
    
    # 結果表示のみの場合
    if [[ "$show_results_flag" = true ]]; then
        show_results
        echo
        show_stats
        exit 0
    fi
    
    # ヘッダー表示
    print_header "下髭・連続下落シグナル検出バッチ"
    
    # 環境チェック
    check_python_requirements
    check_docker_environment
    
    # 実行設定表示
    print_info "実行設定:"
    if [[ "$create_table" = true ]]; then
        print_info "  モード: テーブル作成"
    elif [[ "$test_mode" = true ]]; then
        print_info "  モード: テスト（10銘柄）"
    else
        print_info "  モード: 全銘柄検出"
    fi
    print_info "  ログファイル: $LOG_FILE"
    
    # 検出条件の説明
    if [[ "$create_table" = false ]]; then
        print_info ""
        print_info "検出条件:"
        print_info "  ✓ 下髭が全体値幅の50%以上"
        print_info "  ✓ 上髭が全体値幅の30%以下"
        print_info "  ✓ 4営業日以上の連続下落後"
        print_info "  ✓ 最新または1営業日前に発生"
    fi
    
    # 実行開始
    print_header "処理開始"
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
        if [[ "$create_table" = true ]]; then
            print_success "テーブル作成が完了しました"
        else
            print_success "シグナル検出が正常に完了しました"
            
            # 検出結果の簡易表示
            if [[ "$quiet_mode" = false ]]; then
                echo
                show_stats
                echo
                print_info "詳細結果を表示するには: ./detect_hammer_signals.sh --show-results"
            fi
        fi
        
        print_info "詳細ログ: $LOG_FILE"
    else
        print_error "処理中にエラーが発生しました (終了コード: $exit_status)"
        print_info "ログを確認してください: $LOG_FILE"
        exit $exit_status
    fi
}

# スクリプト実行
main "$@"