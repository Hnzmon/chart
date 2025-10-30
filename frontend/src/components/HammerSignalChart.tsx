import React, { useEffect, useRef } from "react";
import {
  createChart,
  IChartApi,
  CandlestickData,
  HistogramData,
  LineData,
  Time,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
} from "lightweight-charts";
import { HammerChartData } from "../types/stockData";

// 移動平均計算関数
const calculateMovingAverage = (data: any[], period: number): LineData[] => {
  const result: LineData[] = [];
  for (let i = period - 1; i < data.length; i++) {
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) {
      sum += data[j].close;
    }
    const average = sum / period;
    result.push({
      time: data[i].date,
      value: average,
    });
  }
  return result;
};

interface HammerSignalChartProps {
  chartData: HammerChartData;
  signalDate: string;
}

export const HammerSignalChart: React.FC<HammerSignalChartProps> = ({
  chartData,
  signalDate,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || !chartData.data.length) return;

    // チャート初期化
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: "white" },
        textColor: "#333",
      },
      grid: {
        vertLines: { color: "#f0f0f0" },
        horzLines: { color: "#f0f0f0" },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: "#cccccc",
      },
      timeScale: {
        borderColor: "#cccccc",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // v5の正しいAPIを使用してローソク足シリーズ作成
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#ef5350",
      downColor: "#26a69a",
      borderDownColor: "#26a69a",
      borderUpColor: "#ef5350",
      wickDownColor: "#26a69a",
      wickUpColor: "#ef5350",
    });

    // v5の正しいAPIを使用して出来高シリーズ作成
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#26a69a",
      priceFormat: {
        type: "volume",
      },
      priceScaleId: "volume",
    });

    // 出来高の価格軸を下部に配置
    chart.priceScale("volume").applyOptions({
      scaleMargins: {
        top: 0.7,
        bottom: 0,
      },
    });

    // データを変換してセット
    const candlestickData: CandlestickData[] = chartData.data.map((item) => ({
      time: item.date,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    }));

    const volumeData: HistogramData[] = chartData.data.map((item) => ({
      time: item.date,
      value: item.volume,
      color: item.close >= item.open ? "#ef535080" : "#26a69a80",
    }));

    candlestickSeries.setData(candlestickData);
    volumeSeries.setData(volumeData);

    // 移動平均線を追加
    const ma5Series = chart.addSeries(LineSeries, {
      color: "#FF6B35",
      lineWidth: 2,
    });

    const ma25Series = chart.addSeries(LineSeries, {
      color: "#4ECDC4",
      lineWidth: 2,
    });

    const ma75Series = chart.addSeries(LineSeries, {
      color: "#9C27B0",
      lineWidth: 2,
    });

    // 移動平均データを計算してセット
    const ma5Data = calculateMovingAverage(chartData.data, 5);
    const ma25Data = calculateMovingAverage(chartData.data, 25);
    const ma75Data = calculateMovingAverage(chartData.data, 75);

    ma5Series.setData(ma5Data);
    ma25Series.setData(ma25Data);
    ma75Series.setData(ma75Data);

    // シグナル日にマーカーを追加（v5では異なる方法を使用）
    const signalDateString = new Date(signalDate).toISOString().split("T")[0];
    const signalMarker = candlestickData.find(
      (data) => data.time === signalDateString
    );

    // ハンマーシグナルのマーカー表示は省略（タイトル表示を削除）

    // リサイズ対応
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);

    // クリーンアップ
    return () => {
      window.removeEventListener("resize", handleResize);
      if (chart) {
        chart.remove();
      }
    };
  }, [chartData, signalDate]);

  if (!chartData.data.length) {
    return (
      <div
        style={{
          height: "400px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#f8f9fa",
          borderRadius: "4px",
          color: "#666",
        }}
      >
        チャートデータがありません
      </div>
    );
  }

  return (
    <div>
      <div
        style={{
          marginBottom: "10px",
          fontSize: "14px",
          color: "#666",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span>期間: 1年分 ({chartData.count}件のデータ)</span>
        <span>
          🔨 ハンマーシグナル:{" "}
          {new Date(signalDate).toLocaleDateString("ja-JP")}
        </span>
      </div>
      <div
        ref={chartContainerRef}
        style={{
          width: "100%",
          height: "400px",
          border: "1px solid #e0e0e0",
          borderRadius: "4px",
        }}
      />
    </div>
  );
};
