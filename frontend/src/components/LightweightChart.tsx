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
import {
  StockData,
  MovingAverageSettings,
  defaultMASettings,
} from "../types/stockData";

interface LightweightChartProps {
  data: StockData[];
  maSettings?: MovingAverageSettings;
}

export const LightweightChart: React.FC<LightweightChartProps> = ({
  data,
  maSettings = defaultMASettings,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    // チャートが既に存在する場合は削除
    if (chartRef.current) {
      chartRef.current.remove();
    }

    // 新しいチャートを作成
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 550,
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

    // v5の正しいAPIを使用
    try {
      // ローソク足シリーズの追加（v5の正しい方法）
      const candlestickSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#4CAF50",
        downColor: "#F44336",
        borderDownColor: "#F44336",
        borderUpColor: "#4CAF50",
        wickDownColor: "#F44336",
        wickUpColor: "#4CAF50",
      });

      // 出来高シリーズの追加（v5の正しい方法）
      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: "#82ca9d",
        priceFormat: {
          type: "volume",
        },
        priceScaleId: "volume",
      });

      // 出来高用の価格スケールを調整
      chart.priceScale("volume").applyOptions({
        scaleMargins: {
          top: 0.7, // ローソク足の下70%
          bottom: 0,
        },
      });

      // 移動平均線シリーズの追加（v5の正しい方法）
      let ma1Series, ma2Series, ma3Series;

      if (maSettings.ma1.enabled) {
        ma1Series = chart.addSeries(LineSeries, {
          color: maSettings.ma1.color,
          lineWidth: 2,
          title: `MA${maSettings.ma1.period}`,
        });
      }

      if (maSettings.ma2.enabled) {
        ma2Series = chart.addSeries(LineSeries, {
          color: maSettings.ma2.color,
          lineWidth: 2,
          title: `MA${maSettings.ma2.period}`,
        });
      }

      if (maSettings.ma3.enabled) {
        ma3Series = chart.addSeries(LineSeries, {
          color: maSettings.ma3.color,
          lineWidth: 2,
          title: `MA${maSettings.ma3.period}`,
        });
      }

      // データの変換とシリーズへの設定
      const candlestickData: CandlestickData[] = data.map((item) => ({
        time: (new Date(item.date).getTime() / 1000) as Time,
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
      }));

      const volumeData: HistogramData[] = data.map((item) => ({
        time: (new Date(item.date).getTime() / 1000) as Time,
        value: item.volume,
        color: item.close >= item.open ? "#4CAF50" : "#F44336",
      }));

      // ローソク足と出来高データを設定
      candlestickSeries.setData(candlestickData);
      volumeSeries.setData(volumeData);

      // 移動平均線データを設定
      if (maSettings.ma1.enabled && ma1Series) {
        const ma1Data: LineData[] = data
          .filter((item) => item.ma1 !== null)
          .map((item) => ({
            time: (new Date(item.date).getTime() / 1000) as Time,
            value: item.ma1!,
          }));
        ma1Series.setData(ma1Data);
      }

      if (maSettings.ma2.enabled && ma2Series) {
        const ma2Data: LineData[] = data
          .filter((item) => item.ma2 !== null)
          .map((item) => ({
            time: (new Date(item.date).getTime() / 1000) as Time,
            value: item.ma2!,
          }));
        ma2Series.setData(ma2Data);
      }

      if (maSettings.ma3.enabled && ma3Series) {
        const ma3Data: LineData[] = data
          .filter((item) => item.ma3 !== null)
          .map((item) => ({
            time: (new Date(item.date).getTime() / 1000) as Time,
            value: item.ma3!,
          }));
        ma3Series.setData(ma3Data);
      }

      // ツールチップの追加設定（Lightweight Charts v4/v5互換）
      chart.subscribeCrosshairMove((param: any) => {
        if (param.time) {
          // カスタムツールチップロジックをここに追加できます
          console.log("Crosshair moved:", param);
        }
      });
    } catch (error) {
      console.error("Lightweight Charts API error:", error);
      // フォールバック：エラーがある場合は表示だけ行う
    }

    // チャートのリサイズ対応（改善版）
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    // ResizeObserverを使ってより正確なリサイズ対応
    let resizeObserver: ResizeObserver | null = null;
    if (chartContainerRef.current) {
      resizeObserver = new ResizeObserver(handleResize);
      resizeObserver.observe(chartContainerRef.current);
    }

    window.addEventListener("resize", handleResize);

    // クリーンアップ関数
    return () => {
      window.removeEventListener("resize", handleResize);
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [data, maSettings]);

  return (
    <div
      ref={chartContainerRef}
      style={{
        width: "100%",
        height: "550px",
        position: "relative",
      }}
    />
  );
};
