import { riskLabel, RISK_COLORS } from "../risk";

interface Props {
  hour: number;
  maxHour: number;
  departure: string;
  show: boolean;
  onHour: (hour: number) => void;
  onToggle: (show: boolean) => void;
}

export default function HeatmapControls({ hour, maxHour, departure, show, onHour, onToggle }: Props) {
  const when = new Date(new Date(departure).getTime() + hour * 3_600_000);
  return (
    <div className="heat-controls">
      <label className="toggle">
        <input type="checkbox" checked={show} onChange={(e) => onToggle(e.target.checked)} />
        Weather heatmap
      </label>
      <input
        type="range"
        min={0}
        max={maxHour}
        value={hour}
        disabled={!show}
        onChange={(e) => onHour(Number(e.target.value))}
        aria-label="Forecast hour after departure"
      />
      <span className="hour">
        +{hour}h · {when.toLocaleString(undefined, { weekday: "short", hour: "numeric" })}
      </span>
      <div className="legend">
        {RISK_COLORS.map((color, level) => (
          <span key={level}>
            <i style={{ background: color }} />
            {riskLabel(level)}
          </span>
        ))}
      </div>
    </div>
  );
}
