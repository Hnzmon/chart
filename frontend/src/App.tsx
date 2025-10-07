import React, { useState, useEffect } from "react";
import { StockChart } from "./components/StockChart";
import { MASettingsPanel } from "./components/MASettingsPanel";
import { MovingAverageSettings, defaultMASettings } from "./types/stockData";
import "./App.css";

interface ChartComponentProps {
  stockCode: string;
  onRemove: () => void;
  maSettings: MovingAverageSettings;
}

interface StockInfo {
  code: string;
  name: string;
  market: string;
  sector: string;
}

const App: React.FC = () => {
  const [stockCode, setStockCode] = useState<string>("");
  const [displayedCharts, setDisplayedCharts] = useState<string[]>([]);
  const [maSettings, setMaSettings] =
    useState<MovingAverageSettings>(defaultMASettings);

  // ローカルストレージから表示中のチャートを読み込み
  useEffect(() => {
    const saved = localStorage.getItem("displayedCharts");
    if (saved) {
      setDisplayedCharts(JSON.parse(saved) as string[]);
    }
  }, []);

  // ローカルストレージに保存
  const saveToLocalStorage = (charts: string[]): void => {
    localStorage.setItem("displayedCharts", JSON.stringify(charts));
  };

  // チャート追加
  const addChart = (): void => {
    if (!stockCode.trim()) return;
    if (displayedCharts.length >= 50) {
      alert("最大50件まで表示できます");
      return;
    }
    if (displayedCharts.includes(stockCode)) {
      alert("既に表示されています");
      return;
    }

    const newCharts = [...displayedCharts, stockCode];
    setDisplayedCharts(newCharts);
    saveToLocalStorage(newCharts);
    setStockCode("");
  };

  // チャート削除
  const removeChart = (codeToRemove: string): void => {
    const newCharts = displayedCharts.filter(
      (code: string) => code !== codeToRemove
    );
    setDisplayedCharts(newCharts);
    saveToLocalStorage(newCharts);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === "Enter") {
      addChart();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    setStockCode(e.target.value);
  };

  return (
    <div className="app">
      <div className="header">
        <h1>株価チャートアプリ</h1>
        <div className="input-section">
          <input
            type="text"
            value={stockCode}
            onChange={handleInputChange}
            placeholder="銘柄コードを入力"
            onKeyPress={handleKeyPress}
          />
          <button onClick={addChart}>表示</button>
        </div>
        <p>表示中: {displayedCharts.length} / 50</p>

        {/* 移動平均線設定パネル */}
        <MASettingsPanel
          settings={maSettings}
          onSettingsChange={setMaSettings}
        />
      </div>

      <div className="charts-container">
        {displayedCharts.map((code) => (
          <ChartComponent
            key={code}
            stockCode={code}
            onRemove={() => removeChart(code)}
            maSettings={maSettings}
          />
        ))}
      </div>
    </div>
  );
};

// チャートコンポーネント
const ChartComponent: React.FC<ChartComponentProps> = ({
  stockCode,
  onRemove,
  maSettings,
}) => {
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null);
  const [infoLoading, setInfoLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchStockInfo = async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/stock-info/${stockCode}`
        );
        if (response.ok) {
          const info = await response.json();
          setStockInfo(info);
        }
      } catch (error) {
        console.error("銘柄情報取得エラー:", error);
      } finally {
        setInfoLoading(false);
      }
    };

    fetchStockInfo();
  }, [stockCode]);

  return (
    <div className="chart-item">
      <div className="chart-header">
        <h3>
          銘柄コード: {stockCode}
          {!infoLoading && stockInfo && (
            <span className="stock-name"> - {stockInfo.name}</span>
          )}
        </h3>
        <button className="close-btn" onClick={onRemove}>
          ×
        </button>
      </div>
      <div className="chart-content">
        <StockChart stockCode={stockCode} maSettings={maSettings} />
      </div>
    </div>
  );
};

export default App;
