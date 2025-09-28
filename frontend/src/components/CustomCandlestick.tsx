import React from "react";
import { StockData } from "../types/stockData";

interface CustomCandlestickProps {
  data: StockData[];
  width: number;
  height: number;
  margin: { top: number; right: number; bottom: number; left: number };
}

export const CustomCandlestick: React.FC<CustomCandlestickProps> = ({
  data,
  width,
  height,
  margin,
}) => {
  if (!data || data.length === 0) return null;

  // データの価格レンジを計算
  const prices = data.flatMap((d) => [d.open, d.high, d.low, d.close]);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceRange = maxPrice - minPrice;

  // 描画エリアのサイズ
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;
  const candleWidth = (chartWidth / data.length) * 0.8;

  // 価格をY座標に変換する関数
  const priceToY = (price: number) => {
    return margin.top + (chartHeight * (maxPrice - price)) / priceRange;
  };

  return (
    <svg width={width} height={height}>
      {/* グリッド線 */}
      <defs>
        <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
          <path
            d="M 10 0 L 0 0 0 10"
            fill="none"
            stroke="#e1e1e1"
            strokeWidth="0.5"
          />
        </pattern>
      </defs>
      <rect
        width={chartWidth}
        height={chartHeight}
        x={margin.left}
        y={margin.top}
        fill="url(#grid)"
      />

      {/* ローソク足を描画 */}
      {data.map((item, index) => {
        const x =
          margin.left +
          (index * chartWidth) / data.length +
          (chartWidth / data.length - candleWidth) / 2;
        const centerX = x + candleWidth / 2;

        const openY = priceToY(item.open);
        const highY = priceToY(item.high);
        const lowY = priceToY(item.low);
        const closeY = priceToY(item.close);

        const isUp = item.close >= item.open;
        const bodyTop = Math.min(openY, closeY);
        const bodyHeight = Math.abs(openY - closeY);
        const bodyColor = isUp ? "#4CAF50" : "#F44336";
        const wickColor = "#666";

        return (
          <g key={index}>
            {/* 上ヒゲ */}
            <line
              x1={centerX}
              y1={highY}
              x2={centerX}
              y2={bodyTop}
              stroke={wickColor}
              strokeWidth={1}
            />
            {/* 下ヒゲ */}
            <line
              x1={centerX}
              y1={bodyTop + bodyHeight}
              x2={centerX}
              y2={lowY}
              stroke={wickColor}
              strokeWidth={1}
            />
            {/* ローソク足の実体 */}
            <rect
              x={x}
              y={bodyTop}
              width={candleWidth}
              height={Math.max(bodyHeight, 1)}
              fill={isUp ? bodyColor : bodyColor}
              fillOpacity={isUp ? 0.8 : 1}
              stroke={bodyColor}
              strokeWidth={1}
            />
            {/* 十字線（同値の場合） */}
            {bodyHeight === 0 && (
              <line
                x1={x}
                y1={openY}
                x2={x + candleWidth}
                y2={openY}
                stroke={bodyColor}
                strokeWidth={2}
              />
            )}
          </g>
        );
      })}

      {/* Y軸の価格ラベル */}
      {[minPrice, (minPrice + maxPrice) / 2, maxPrice].map((price, index) => (
        <g key={index}>
          <line
            x1={margin.left - 5}
            y1={priceToY(price)}
            x2={margin.left}
            y2={priceToY(price)}
            stroke="#666"
            strokeWidth={1}
          />
          <text
            x={margin.left - 10}
            y={priceToY(price) + 4}
            fontSize="10"
            fill="#666"
            textAnchor="end"
          >
            ¥{Math.round(price).toLocaleString()}
          </text>
        </g>
      ))}

      {/* X軸の日付ラベル（簡略版） */}
      {data
        .filter((_, index) => index % Math.ceil(data.length / 5) === 0)
        .map((item, index) => {
          const x =
            margin.left +
            (index * Math.ceil(data.length / 5) * chartWidth) / data.length;
          return (
            <g key={index}>
              <line
                x1={x}
                y1={margin.top + chartHeight}
                x2={x}
                y2={margin.top + chartHeight + 5}
                stroke="#666"
                strokeWidth={1}
              />
              <text
                x={x}
                y={margin.top + chartHeight + 18}
                fontSize="10"
                fill="#666"
                textAnchor="middle"
              >
                {new Date(item.date).toLocaleDateString("ja-JP", {
                  month: "short",
                  day: "numeric",
                })}
              </text>
            </g>
          );
        })}
    </svg>
  );
};
