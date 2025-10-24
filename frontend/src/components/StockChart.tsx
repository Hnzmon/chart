import React, { useState, useEffect } from "react";
import { LightweightChart } from "./LightweightChart";
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
      {/* Lightweight Charts（ローソク足 + 出来高 + 移動平均線） */}
      <LightweightChart data={data} maSettings={maSettings} />
    </div>
  );
};
