export interface Place {
  label: string;
  lat: number;
  lon: number;
}

export interface PlanInput {
  origin: Place;
  destination: Place;
  departure: string; // ISO 8601
  load_lb: number;
  interval_miles: 10 | 25 | 50;
}

export interface Checkpoint {
  index: number;
  mile: number;
  lat: number;
  lon: number;
  eta: string;
  forecast_available: boolean;
  weather: { wind_mph: number; rain_in_hr: number; snow_in_hr: number };
  risk: { level: number; label: string; drivers: string[] };
  /** Risk level (0-4) for each hour 0..48 after departure. */
  hourly_risk: number[];
}

export interface RouteSummary {
  miles_by_risk: Record<string, number>;
  no_travel_miles: number;
  severe_miles: number;
  high_miles: number;
  avg_risk: number;
  worst_risk: number;
  forecast_gaps: number;
  checkpoint_count: number;
}

export interface RoutePlan {
  id: string;
  label: string;
  distance_mi: number;
  duration_s: number;
  departure: string;
  arrival: string;
  geometry: [number, number][];
  checkpoints: Checkpoint[];
  summary: RouteSummary;
  rank: number;
  recommended: boolean;
  reason?: string;
}

export interface PlanResponse {
  recommended_route_id: string;
  load_lb: number;
  interval_miles: number;
  heatmap_hours: number;
  routes: RoutePlan[];
}
