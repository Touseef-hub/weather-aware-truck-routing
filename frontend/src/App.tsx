import { useCallback, useRef, useState } from "react";
import HeatmapControls from "./components/HeatmapControls";
import MapView from "./components/MapView";
import PlanForm from "./components/PlanForm";
import RouteList from "./components/RouteList";
import { planRoutes } from "./services/api";
import type { PlanInput, PlanResponse } from "./types";

export default function App() {
  const [input, setInput] = useState<PlanInput | null>(null);
  const [result, setResult] = useState<PlanResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHeat, setShowHeat] = useState(true);
  const [hour, setHour] = useState(0);
  const inflight = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(async (next: PlanInput) => {
    inflight.current?.abort();
    const controller = new AbortController();
    inflight.current = controller;

    setLoading(true);
    setError(null);
    try {
      const data = await planRoutes(next, controller.signal);
      setInput(next);
      setResult(data);
      setSelectedId(data.recommended_route_id);
      setHour(0);
    } catch (err) {
      if ((err as Error).name !== "AbortError") setError((err as Error).message);
    } finally {
      if (inflight.current === controller) setLoading(false);
    }
  }, []);

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>Weather-Aware Truck Routing</h1>
        <PlanForm loading={loading} onSubmit={handleSubmit} />
        {error && <p className="error banner">{error}</p>}
        {result && <RouteList routes={result.routes} selectedId={selectedId} onSelect={setSelectedId} />}
      </aside>
      <main className="map-wrap">
        <MapView
          routes={result?.routes ?? []}
          selectedId={selectedId}
          origin={input?.origin ?? null}
          destination={input?.destination ?? null}
          showHeat={showHeat && !!result}
          hour={hour}
          intervalMiles={result?.interval_miles ?? 25}
          onSelect={setSelectedId}
        />
        {result && input && (
          <HeatmapControls
            hour={hour}
            maxHour={result.heatmap_hours}
            departure={input.departure}
            show={showHeat}
            onHour={setHour}
            onToggle={setShowHeat}
          />
        )}
      </main>
    </div>
  );
}
