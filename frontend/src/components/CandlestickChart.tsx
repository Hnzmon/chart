import React, { useEffect, useRef, MutableRefObject } from "react";
// @ts-ignore
import { createChart } from "lightweight-charts";
import { StockData, MovingAverageSettings } from "../types/stockData";

interface CandlestickChartProps {
  data: StockData[];
  maSettings: MovingAverageSettings;
  height?: number;
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  data,
  maSettings,
  height = 400,
}) => {
  const chartContainerRef: MutableRefObject<HTMLDivElement | null> =
    useRef(null);
  const chartRef: MutableRefObject<any> = useRef(null);
  const candleSeriesRef: MutableRefObject<any> = useRef(null);
  const ma1SeriesRef: MutableRefObject<any> = useRef(null);
  const ma2SeriesRef: MutableRefObject<any> = useRef(null);
  const ma3SeriesRef: MutableRefObject<any> = useRef(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // チャートの初期化
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: "#ffffff" },
        textColor: "#333",
      },
      grid: {
        vertLines: { color: "#e1e1e1" },
        horzLines: { color: "#e1e1e1" },
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

    // ローソク足シリーズの追加
    // @ts-ignore
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#00C853",
      downColor: "#FF1744",
      borderDownColor: "#FF1744",
      borderUpColor: "#00C853",
      wickDownColor: "#FF1744",
      wickUpColor: "#00C853",
    });

    candleSeriesRef.current = candleSeries;

    // 移動平均線シリーズの追加
    if (maSettings.ma1.enabled) {
      // @ts-ignore
      ma1SeriesRef.current = chart.addLineSeries({
        color: maSettings.ma1.color,
        lineWidth: 2,
        title: maSettings.ma1.name,
      });
    }

    if (maSettings.ma2.enabled) {
      // @ts-ignore
      ma2SeriesRef.current = chart.addLineSeries({
        color: maSettings.ma2.color,
        lineWidth: 2,
        title: maSettings.ma2.name,
      });
    }

    if (maSettings.ma3.enabled) {
      // @ts-ignore
      ma3SeriesRef.current = chart.addLineSeries({
        color: maSettings.ma3.color,
        lineWidth: 2,
        title: maSettings.ma3.name,
      });
    }

    // ウィンドウリサイズ対応
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [height, maSettings]);

  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current || !data.length) return;

    // ローソク足データを変換
    const candleData: any[] = data.map((item) => ({
      time: item.date,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    }));

    candleSeriesRef.current.setData(candleData);

    // 移動平均線データを設定
    if (maSettings.ma1.enabled && ma1SeriesRef.current) {
      const ma1Data: any[] = data
        .filter((item) => item.ma1 !== undefined)
        .map((item) => ({
          time: item.date,
          value: item.ma1!,
        }));
      ma1SeriesRef.current.setData(ma1Data);
    }

    if (maSettings.ma2.enabled && ma2SeriesRef.current) {
      const ma2Data: any[] = data
        .filter((item) => item.ma2 !== undefined)
        .map((item) => ({
          time: item.date,
          value: item.ma2!,
        }));
      ma2SeriesRef.current.setData(ma2Data);
    }

    if (maSettings.ma3.enabled && ma3SeriesRef.current) {
      const ma3Data: any[] = data
        .filter((item) => item.ma3 !== undefined)
        .map((item) => ({
          time: item.date,
          value: item.ma3!,
        }));
      ma3SeriesRef.current.setData(ma3Data);
    }

    // チャートを最新データにフィット
    chartRef.current.timeScale().fitContent();
  }, [data, maSettings]);

  return (
    <div
      ref={chartContainerRef}
      style={{ width: "100%", height: `${height}px`, position: "relative" }}
    />
  );
};
