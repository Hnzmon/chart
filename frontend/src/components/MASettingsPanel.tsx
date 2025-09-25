import React from "react";
import { MovingAverageSettings } from "../types/stockData";

interface MASettingsProps {
  settings: MovingAverageSettings;
  onSettingsChange: (settings: MovingAverageSettings) => void;
}

export const MASettingsPanel: React.FC<MASettingsProps> = ({
  settings,
  onSettingsChange,
}) => {
  const handlePeriodChange = (ma: "ma1" | "ma2" | "ma3", period: number) => {
    const newSettings = {
      ...settings,
      [ma]: {
        ...settings[ma],
        period: period,
      },
    };
    onSettingsChange(newSettings);
  };

  const handleEnabledChange = (ma: "ma1" | "ma2" | "ma3", enabled: boolean) => {
    const newSettings = {
      ...settings,
      [ma]: {
        ...settings[ma],
        enabled: enabled,
      },
    };
    onSettingsChange(newSettings);
  };

  const handleColorChange = (ma: "ma1" | "ma2" | "ma3", color: string) => {
    const newSettings = {
      ...settings,
      [ma]: {
        ...settings[ma],
        color: color,
      },
    };
    onSettingsChange(newSettings);
  };

  return (
    <div className="ma-settings-panel">
      <h4>移動平均線設定</h4>

      {/* MA1設定 */}
      <div className="ma-setting-row">
        <input
          type="checkbox"
          checked={settings.ma1.enabled}
          onChange={(e) => handleEnabledChange("ma1", e.target.checked)}
        />
        <label>MA1:</label>
        <input
          type="number"
          value={settings.ma1.period}
          min={1}
          max={200}
          onChange={(e) => handlePeriodChange("ma1", parseInt(e.target.value))}
          disabled={!settings.ma1.enabled}
        />
        <span>日</span>
        <input
          type="color"
          value={settings.ma1.color}
          onChange={(e) => handleColorChange("ma1", e.target.value)}
          disabled={!settings.ma1.enabled}
        />
      </div>

      {/* MA2設定 */}
      <div className="ma-setting-row">
        <input
          type="checkbox"
          checked={settings.ma2.enabled}
          onChange={(e) => handleEnabledChange("ma2", e.target.checked)}
        />
        <label>MA2:</label>
        <input
          type="number"
          value={settings.ma2.period}
          min={1}
          max={200}
          onChange={(e) => handlePeriodChange("ma2", parseInt(e.target.value))}
          disabled={!settings.ma2.enabled}
        />
        <span>日</span>
        <input
          type="color"
          value={settings.ma2.color}
          onChange={(e) => handleColorChange("ma2", e.target.value)}
          disabled={!settings.ma2.enabled}
        />
      </div>

      {/* MA3設定 */}
      <div className="ma-setting-row">
        <input
          type="checkbox"
          checked={settings.ma3.enabled}
          onChange={(e) => handleEnabledChange("ma3", e.target.checked)}
        />
        <label>MA3:</label>
        <input
          type="number"
          value={settings.ma3.period}
          min={1}
          max={200}
          onChange={(e) => handlePeriodChange("ma3", parseInt(e.target.value))}
          disabled={!settings.ma3.enabled}
        />
        <span>日</span>
        <input
          type="color"
          value={settings.ma3.color}
          onChange={(e) => handleColorChange("ma3", e.target.value)}
          disabled={!settings.ma3.enabled}
        />
      </div>
    </div>
  );
};
