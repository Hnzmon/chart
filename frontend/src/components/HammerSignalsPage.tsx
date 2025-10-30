import React, { useState, useEffect } from "react";
import { HammerChartData } from "../types/stockData";
import { HammerSignalChart } from "./HammerSignalChart";
import "../App.css";

// ハンマーシグナルの型定義
export interface HammerSignal {
  symbol: string;
  signal_date: string;
  decline_days: number;
  total_decline_pct: number;
  lower_shadow_ratio: number;
  detection_date: string;
  name: string;
  market: string;
  sector: string;
}

// ハンマーシグナルAPIレスポンスの型
export interface HammerSignalsResponse {
  signals: HammerSignal[];
  count: number;
  latest_date: string | null;
}

interface HammerSignalsPageProps {
  onBack: () => void;
}

export const HammerSignalsPage: React.FC<HammerSignalsPageProps> = ({
  onBack,
}) => {
  const [signals, setSignals] = useState<HammerSignal[]>([]);
  const [latestDate, setLatestDate] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [chartData, setChartData] = useState<Record<string, HammerChartData>>(
    {}
  );
  const [loadingCharts, setLoadingCharts] = useState<Set<string>>(new Set());

  // ハンマーシグナル一覧を取得
  useEffect(() => {
    fetchHammerSignals();
  }, []);

  const fetchHammerSignals = async () => {
    try {
      setLoading(true);
      const response = await fetch("http://localhost:8000/api/hammer-signals");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data: HammerSignalsResponse = await response.json();
      setSignals(data.signals);
      setLatestDate(data.latest_date);

      // 各銘柄のチャートデータを取得
      if (data.signals.length > 0) {
        fetchAllChartData(data.signals);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "データの取得に失敗しました"
      );
    } finally {
      setLoading(false);
    }
  };

  const fetchAllChartData = async (signalList: HammerSignal[]) => {
    const newLoadingCharts = new Set(signalList.map((s) => s.symbol));
    setLoadingCharts(newLoadingCharts);

    const chartDataPromises = signalList.map(async (signal) => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/hammer-signals/chart-data/${signal.symbol}`
        );
        if (!response.ok) {
          throw new Error(`Failed to fetch chart data for ${signal.symbol}`);
        }
        const data: HammerChartData = await response.json();
        return { symbol: signal.symbol, data };
      } catch (error) {
        console.error(`Error fetching chart data for ${signal.symbol}:`, error);
        return { symbol: signal.symbol, data: null };
      }
    });

    const results = await Promise.all(chartDataPromises);
    const newChartData: Record<string, HammerChartData> = {};

    results.forEach((result) => {
      if (result.data) {
        newChartData[result.symbol] = result.data;
      }
      newLoadingCharts.delete(result.symbol);
    });

    setChartData(newChartData);
    setLoadingCharts(new Set());
  };

  if (loading) {
    return (
      <div className="hammer-signals-page">
        <button onClick={onBack} className="back-button">
          ← TOPに戻る
        </button>
        <div>ハンマーシグナルを読み込み中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="hammer-signals-page">
        <button onClick={onBack} className="back-button">
          ← TOPに戻る
        </button>
        <div style={{ color: "red" }}>エラー: {error}</div>
      </div>
    );
  }

  return (
    <div className="hammer-signals-page">
      <div className="hammer-signals-header">
        <button onClick={onBack} className="back-button">
          ← TOPに戻る
        </button>
        <h1>ハンマーシグナル検出結果</h1>
        {latestDate && (
          <span className="hammer-signals-date">
            検出日: {new Date(latestDate).toLocaleDateString("ja-JP")}
          </span>
        )}
      </div>

      {signals.length === 0 ? (
        <div className="hammer-signals-empty">
          <h3>ハンマーシグナルが見つかりませんでした</h3>
          <p>
            4営業日以上の連続下落後のハンマーパターンに該当する銘柄がありません。
          </p>
        </div>
      ) : (
        <div>
          <div className="hammer-signals-summary">
            <strong>{signals.length}件</strong>のハンマーシグナルを検出しました
          </div>

          {/* シグナル一覧テーブル */}
          <div className="hammer-signals-table-container">
            <table className="hammer-signals-table">
              <thead>
                <tr>
                  <th>銘柄コード</th>
                  <th>銘柄名</th>
                  <th>市場</th>
                  <th className="center">シグナル日</th>
                  <th className="center">下落日数</th>
                  <th className="center">総下落率</th>
                  <th className="center">下髭比率</th>
                </tr>
              </thead>
              <tbody>
                {signals.map((signal, index) => (
                  <tr key={`${signal.symbol}-${signal.signal_date}`}>
                    <td>{signal.symbol}</td>
                    <td>{signal.name || "N/A"}</td>
                    <td>{signal.market || "N/A"}</td>
                    <td className="center">
                      {new Date(signal.signal_date).toLocaleDateString("ja-JP")}
                    </td>
                    <td className="center">{signal.decline_days}日</td>
                    <td className="center">
                      {signal.total_decline_pct.toFixed(2)}%
                    </td>
                    <td className="center">
                      {signal.lower_shadow_ratio.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* チャート表示 */}
          <div className="hammer-signals-charts">
            <h2>チャート表示（1年分）</h2>
            {signals.map((signal) => {
              const isLoading = loadingCharts.has(signal.symbol);
              const data = chartData[signal.symbol];

              return (
                <div key={signal.symbol} className="hammer-chart-item">
                  <h3 className="hammer-chart-header">
                    {signal.symbol} - {signal.name || "N/A"}
                    <span className="hammer-chart-subheader">
                      ({signal.market}) シグナル日:{" "}
                      {new Date(signal.signal_date).toLocaleDateString("ja-JP")}
                    </span>
                  </h3>

                  {isLoading ? (
                    <div className="hammer-chart-loading">
                      チャートデータを読み込み中...
                    </div>
                  ) : data ? (
                    <HammerSignalChart
                      chartData={data}
                      signalDate={signal.signal_date}
                    />
                  ) : (
                    <div className="hammer-chart-error">
                      チャートデータの取得に失敗しました
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
