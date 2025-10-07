import React, { useState, useEffect } from "react";
import {
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Line,
  Bar,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
  Cell,
} from "recharts";
import { CustomCandlestick } from "./CustomCandlestick";
import {
  StockData,
  generateSampleData,
  MovingAverageSettings,
  defaultMASettings,
  calculateMovingAverages,
} from "../types/stockData";

interface StockChartProps {
  stockCode: string;
  maSettings?: MovingAverageSettings;
}

interface StockChartProps {
  stockCode: string;
  maSettings?: MovingAverageSettings;
}

// カスタムツールチップ
const CustomTooltip: React.FC<any> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="custom-tooltip">
        <p className="tooltip-date">{`日付: ${label}`}</p>
        <p className="tooltip-open">{`始値: ¥${data.open?.toLocaleString()}`}</p>
        <p className="tooltip-high">{`高値: ¥${data.high?.toLocaleString()}`}</p>
        <p className="tooltip-low">{`安値: ¥${data.low?.toLocaleString()}`}</p>
        <p className="tooltip-close">{`終値: ¥${data.close?.toLocaleString()}`}</p>
        <p className="tooltip-volume">{`出来高: ${data.volume?.toLocaleString()}`}</p>
        {data.ma1 && (
          <p className="tooltip-ma1">{`MA1: ¥${data.ma1.toLocaleString()}`}</p>
        )}
        {data.ma2 && (
          <p className="tooltip-ma2">{`MA2: ¥${data.ma2.toLocaleString()}`}</p>
        )}
        {data.ma3 && (
          <p className="tooltip-ma3">{`MA3: ¥${data.ma3.toLocaleString()}`}</p>
        )}
      </div>
    );
  }
  return null;
};

export const StockChart: React.FC<StockChartProps> = ({
  stockCode,
  maSettings = defaultMASettings,
}) => {
  const [data, setData] = useState<StockData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError("");

      try {
        // バックエンドAPIの完全URLを指定
        const apiUrl = `http://localhost:8000/api/stocks/${stockCode}`;
        console.log(`APIリクエスト: ${apiUrl}`);

        const response = await fetch(apiUrl, {
          method: "GET",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
        });

        console.log("レスポンス状況:", response.status, response.statusText);
        console.log(
          "レスポンスヘッダー:",
          Object.fromEntries(response.headers.entries())
        );

        if (!response.ok) {
          const errorText = await response.text();
          console.error("エラーレスポンス:", errorText);
          throw new Error(
            `API Error: ${response.status} ${response.statusText} - ${errorText}`
          );
        }

        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
          const responseText = await response.text();
          console.error("非JSON レスポンス:", responseText.substring(0, 200));
          throw new Error(
            `Expected JSON but got ${contentType}: ${responseText.substring(
              0,
              100
            )}`
          );
        }

        const result = await response.json();
        console.log("APIレスポンス:", result); // APIレスポンスの構造を確認してデータを設定
        if (result.data && Array.isArray(result.data)) {
          // 移動平均線を計算
          const dataWithMA = calculateMovingAverages(result.data, maSettings);
          setData(dataWithMA);
        } else {
          throw new Error("Invalid API response format");
        }

        setLoading(false);
      } catch (err: any) {
        console.error("データ取得エラー:", err);
        setError(
          `データの取得に失敗しました: ${err.message || err.toString()}`
        );

        // フォールバック: エラー時はサンプルデータを使用
        console.log("フォールバックとしてサンプルデータを使用します");
        const sampleData = generateSampleData(stockCode, maSettings);
        setData(sampleData);
        setLoading(false);
      }
    };

    fetchData();
  }, [stockCode, maSettings]);

  if (loading) {
    return (
      <div className="chart-loading">
        <p>データを読み込み中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="chart-error">
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="stock-chart" style={{ width: "100%" }}>
      {/* 価格チャート（ローソク足 + 移動平均線） */}
      <div className="price-chart">
        <div style={{ position: "relative", width: "100%" }}>
          {/* カスタムローソク足チャート */}
          <ResponsiveContainer width="100%" height={400}>
            <div style={{ width: "100%", height: "100%" }}>
              <CustomCandlestick
                data={data}
                width={0} // ResponsiveContainerから動的に取得
                height={400}
                margin={{ top: 20, right: 30, bottom: 50, left: 60 }}
              />
            </div>
          </ResponsiveContainer>

          {/* 移動平均線用のオーバーレイチャート */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              pointerEvents: "none",
            }}
          >
            <ResponsiveContainer width="100%" height={400}>
              <ComposedChart
                data={data}
                margin={{ top: 20, right: 30, bottom: 50, left: 60 }}
              >
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={false}
                />
                <YAxis
                  domain={["dataMin - 50", "dataMax + 50"]}
                  axisLine={false}
                  tickLine={false}
                  tick={false}
                />

                {/* 移動平均線のみ表示 */}
                {maSettings.ma1.enabled && (
                  <Line
                    type="monotone"
                    dataKey="ma1"
                    stroke={maSettings.ma1.color}
                    strokeWidth={2}
                    dot={false}
                    name={`MA${maSettings.ma1.period}`}
                  />
                )}
                {maSettings.ma2.enabled && (
                  <Line
                    type="monotone"
                    dataKey="ma2"
                    stroke={maSettings.ma2.color}
                    strokeWidth={2}
                    dot={false}
                    name={`MA${maSettings.ma2.period}`}
                  />
                )}
                {maSettings.ma3.enabled && (
                  <Line
                    type="monotone"
                    dataKey="ma3"
                    stroke={maSettings.ma3.color}
                    strokeWidth={2}
                    dot={false}
                    name={`MA${maSettings.ma3.period}`}
                  />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 出来高チャート */}
      <div className="volume-chart">
        <ResponsiveContainer width="100%" height={150}>
          <ComposedChart
            data={data}
            margin={{ top: 5, right: 30, bottom: 50, left: 60 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10 }}
              tickFormatter={(value) =>
                new Date(value).toLocaleDateString("ja-JP", {
                  month: "short",
                  day: "numeric",
                })
              }
            />
            <YAxis
              tick={{ fontSize: 10 }}
              tickFormatter={(value) => `${Math.round(value / 1000)}K`}
            />
            <Tooltip
              formatter={(value: number) => [
                `${value.toLocaleString()}`,
                "出来高",
              ]}
              labelFormatter={(value) => `日付: ${value}`}
            />
            <Bar dataKey="volume" fill="#82ca9d" name="出来高" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
