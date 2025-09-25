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
} from "recharts";
import {
  StockData,
  generateSampleData,
  MovingAverageSettings,
  defaultMASettings,
} from "../types/stockData";

interface StockChartProps {
  stockCode: string;
  maSettings?: MovingAverageSettings;
}

// カスタムローソク足コンポーネント
const CandlestickBar: React.FC<any> = (props) => {
  const { payload, x, y, width, height } = props;
  if (!payload) return null;

  const { open, close, high, low } = payload;
  const isPositive = close >= open;
  const color = isPositive ? "#00C853" : "#FF1744";
  const bodyHeight =
    (Math.abs(close - open) * height) / (payload.high - payload.low);
  const bodyY =
    y +
    ((Math.max(close, open) - payload.high) * height) /
      (payload.high - payload.low);

  return (
    <g>
      {/* 高値・安値の線 */}
      <line
        x1={x + width / 2}
        y1={y}
        x2={x + width / 2}
        y2={y + height}
        stroke={color}
        strokeWidth={1}
      />
      {/* ローソク足の本体 */}
      <rect
        x={x + width * 0.2}
        y={bodyY}
        width={width * 0.6}
        height={bodyHeight}
        fill={isPositive ? color : color}
        stroke={color}
        strokeWidth={1}
      />
    </g>
  );
};

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
        // 実際のAPIができるまではサンプルデータを使用
        setTimeout(() => {
          const sampleData = generateSampleData(stockCode, maSettings);
          setData(sampleData);
          setLoading(false);
        }, 1000); // ローディング効果のための遅延

        // 実際のAPI呼び出しは以下のようになる予定
        // const response = await fetch(`/api/stocks/${stockCode}`);
        // const result = await response.json();
        // setData(result.data);
      } catch (err) {
        setError("データの取得に失敗しました");
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

  // 価格データの範囲を計算（3本の移動平均線を含む）
  const priceData = data
    .map((d) => [d.high, d.low, d.ma1 || 0, d.ma2 || 0, d.ma3 || 0])
    .flat()
    .filter((v) => v > 0);
  const minPrice = Math.min(...priceData) * 0.95;
  const maxPrice = Math.max(...priceData) * 1.05;

  // 出来高の最大値
  const maxVolume = Math.max(...data.map((d) => d.volume));

  return (
    <div className="stock-chart">
      {/* 価格チャート */}
      <div className="price-chart">
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart
            data={data}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              tickFormatter={(value) =>
                new Date(value).toLocaleDateString("ja-JP", {
                  month: "short",
                  day: "numeric",
                })
              }
            />
            <YAxis
              domain={[minPrice, maxPrice]}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) =>
                `¥${Math.round(value).toLocaleString()}`
              }
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />

            {/* ローソク足（バーで代用） */}
            <Bar
              dataKey="close"
              fill="#8884d8"
              shape={<CandlestickBar />}
              name="価格"
            />

            {/* 移動平均線（3本） */}
            {maSettings.ma1.enabled && (
              <Line
                type="monotone"
                dataKey="ma1"
                stroke={maSettings.ma1.color}
                strokeWidth={2}
                dot={false}
                name={maSettings.ma1.name}
              />
            )}
            {maSettings.ma2.enabled && (
              <Line
                type="monotone"
                dataKey="ma2"
                stroke={maSettings.ma2.color}
                strokeWidth={2}
                dot={false}
                name={maSettings.ma2.name}
              />
            )}
            {maSettings.ma3.enabled && (
              <Line
                type="monotone"
                dataKey="ma3"
                stroke={maSettings.ma3.color}
                strokeWidth={2}
                dot={false}
                name={maSettings.ma3.name}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* 出来高チャート */}
      <div className="volume-chart">
        <ResponsiveContainer width="100%" height={150}>
          <ComposedChart
            data={data}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
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
