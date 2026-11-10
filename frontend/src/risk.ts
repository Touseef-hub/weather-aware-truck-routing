export const RISK_LABELS = ["Low", "Moderate", "High", "Severe", "No Travel"] as const;

export const RISK_COLORS = ["#2e9e5b", "#e6c229", "#f08a24", "#d93a2b", "#5b1a8f"] as const;

export const riskColor = (level: number): string => RISK_COLORS[Math.min(Math.max(level, 0), 4)];
export const riskLabel = (level: number): string => RISK_LABELS[Math.min(Math.max(level, 0), 4)];
