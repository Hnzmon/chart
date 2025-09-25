// 株価データの型定義
export interface StockData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma1?: number; // 移動平均線1
  ma2?: number; // 移動平均線2
  ma3?: number; // 移動平均線3
}

// 移動平均線設定の型
export interface MovingAverageSettings {
  ma1: { period: number; enabled: boolean; color: string; name: string };
  ma2: { period: number; enabled: boolean; color: string; name: string };
  ma3: { period: number; enabled: boolean; color: string; name: string };
}

// デフォルト移動平均線設定
export const defaultMASettings: MovingAverageSettings = {
  ma1: { period: 5, enabled: true, color: "#FF6B35", name: "MA5" },
  ma2: { period: 25, enabled: true, color: "#4ECDC4", name: "MA25" },
  ma3: { period: 75, enabled: true, color: "#9C27B0", name: "MA75" },
};

// APIレスポンスの型
export interface StockApiResponse {
  code: string;
  data: StockData[];
}

// サンプルデータ生成関数（実際のAPIができるまでの仮データ）
export const generateSampleData = (
  stockCode: string,
  maSettings: MovingAverageSettings = defaultMASettings
): StockData[] => {
  const data: StockData[] = [];
  const basePrice = 1000 + Math.random() * 2000; // 基準価格
  let currentPrice = basePrice;

  // 過去180日分のデータを生成
  for (let i = 179; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);

    // 価格変動（ランダムウォーク）
    const change = (Math.random() - 0.5) * 0.1; // -5%から+5%の変動
    currentPrice = currentPrice * (1 + change);

    // ローソク足データ生成
    const high = currentPrice * (1 + Math.random() * 0.05); // 高値
    const low = currentPrice * (1 - Math.random() * 0.05); // 安値
    const open = low + Math.random() * (high - low); // 始値
    const close = low + Math.random() * (high - low); // 終値
    const volume = Math.floor(100000 + Math.random() * 500000); // 出来高

    data.push({
      date: date.toISOString().split("T")[0],
      open: Math.round(open),
      high: Math.round(high),
      low: Math.round(low),
      close: Math.round(close),
      volume,
    });
  }

  // 移動平均線を計算
  return calculateMovingAverages(data, maSettings);
};

// 移動平均線計算（3本対応）
const calculateMovingAverages = (
  data: StockData[],
  maSettings: MovingAverageSettings
): StockData[] => {
  return data.map((item, index) => {
    // MA1
    if (maSettings.ma1.enabled && index >= maSettings.ma1.period - 1) {
      const sum = data
        .slice(index - maSettings.ma1.period + 1, index + 1)
        .reduce((sum, d) => sum + d.close, 0);
      item.ma1 = Math.round(sum / maSettings.ma1.period);
    }

    // MA2
    if (maSettings.ma2.enabled && index >= maSettings.ma2.period - 1) {
      const sum = data
        .slice(index - maSettings.ma2.period + 1, index + 1)
        .reduce((sum, d) => sum + d.close, 0);
      item.ma2 = Math.round(sum / maSettings.ma2.period);
    }

    // MA3
    if (maSettings.ma3.enabled && index >= maSettings.ma3.period - 1) {
      const sum = data
        .slice(index - maSettings.ma3.period + 1, index + 1)
        .reduce((sum, d) => sum + d.close, 0);
      item.ma3 = Math.round(sum / maSettings.ma3.period);
    }

    return item;
  });
};
