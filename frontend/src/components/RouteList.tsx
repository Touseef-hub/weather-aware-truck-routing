import { formatDateTime, formatDuration } from "../format";
import { RISK_COLORS, RISK_LABELS, riskColor, riskLabel } from "../risk";
import type { RoutePlan } from "../types";

interface Props {
  routes: RoutePlan[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export const ROUTE_COLORS: Record<string, string> = {
  "route-a": "#1f6feb",
  "route-b": "#8250df",
  "route-c": "#0a8f8f",
};

function RiskBar({ route }: { route: RoutePlan }) {
  const total = route.distance_mi || 1;
  return (
    <div className="riskbar" role="img" aria-label="Miles by risk level">
      {RISK_LABELS.map((label, level) => {
        const miles = route.summary.miles_by_risk[label] ?? 0;
        return miles > 0 ? (
          <span key={label} title={`${label}: ${miles} mi`} style={{ width: `${(miles / total) * 100}%`, background: RISK_COLORS[level] }} />
        ) : null;
      })}
    </div>
  );
}

export default function RouteList({ routes, selectedId, onSelect }: Props) {
  return (
    <ul className="routes">
      {routes.map((r) => (
        <li key={r.id}>
          <button className={`route-card ${r.id === selectedId ? "selected" : ""}`} onClick={() => onSelect(r.id)}>
            <div className="route-head">
              <span className="swatch" style={{ background: ROUTE_COLORS[r.id] }} />
              <strong>{r.label}</strong>
              {r.recommended && <span className="badge">Recommended</span>}
              <span className="worst" style={{ color: riskColor(r.summary.worst_risk) }}>
                Worst: {riskLabel(r.summary.worst_risk)}
              </span>
            </div>
            <div className="route-meta">
              {r.distance_mi.toFixed(0)} mi · {formatDuration(r.duration_s)} · arrive {formatDateTime(r.arrival)}
            </div>
            <RiskBar route={r} />
            <div className="route-stats">
              <span>Severe {r.summary.severe_miles} mi</span>
              <span>High {r.summary.high_miles} mi</span>
              <span>Avg risk {r.summary.avg_risk.toFixed(2)}</span>
            </div>
            {r.summary.no_travel_miles > 0 && (
              <p className="warn">⚠ {r.summary.no_travel_miles} mi rated No Travel</p>
            )}
            {r.summary.forecast_gaps > 0 && (
              <p className="note">{r.summary.forecast_gaps} checkpoints fall beyond the forecast window.</p>
            )}
            {r.reason && <p className="reason">{r.reason}</p>}
          </button>
        </li>
      ))}
    </ul>
  );
}
