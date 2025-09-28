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

  // 銘柄コードから固定シードを生成（リロード毎の変化を防ぐ）
  const seed = stockCode
    .split("")
    .reduce((acc, char) => acc + char.charCodeAt(0), 0);
  let randomSeed = seed;
  const seededRandom = () => {
    randomSeed = (randomSeed * 9301 + 49297) % 233280;
    return randomSeed / 233280;
  };

  const basePrice = 1000 + seededRandom() * 2000; // 基準価格
  let currentPrice = basePrice;

  // 過去180日分のデータを生成（固定基準日を使用）
  const baseDate = new Date("2024-12-01"); // 固定基準日
  for (let i = 179; i >= 0; i--) {
    const date = new Date(baseDate);
    date.setDate(baseDate.getDate() - i);

    // 価格変動（シード化されたランダムウォーク）
    const change = (seededRandom() - 0.5) * 0.08; // -4%から+4%の変動
    currentPrice = currentPrice * (1 + change);

    // 当日の高値・安値・始値・終値を生成
    const dailyVolatility = 0.025; // 日中変動率
    const open = currentPrice;
    const volatilityRange = currentPrice * dailyVolatility;

    const high = currentPrice + seededRandom() * volatilityRange;
    const low = currentPrice - seededRandom() * volatilityRange;

    // 終値は現在価格の変動後の値
    const close = currentPrice;

    // 始値と終値の関係を調整
    const adjustedOpen = Math.min(Math.max(open, low), high);
    const adjustedClose = Math.min(Math.max(close, low), high);

    // 出来高（シード化されたランダム）
    const volume = Math.floor(100000 + seededRandom() * 500000);

    data.push({
      date: date.toISOString().split("T")[0],
      open: Math.round(adjustedOpen),
      high: Math.round(high),
      low: Math.round(low),
      close: Math.round(adjustedClose),
      volume,
    });
  }

  // 移動平均線を計算
  return calculateMovingAverages(data, maSettings);
};

// 移動平均線計算（3本対応）
export const calculateMovingAverages = (
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
