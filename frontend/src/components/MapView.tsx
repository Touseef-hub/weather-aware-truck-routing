import L from "leaflet";
import { useEffect } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import { formatDateTime } from "../format";
import { riskColor } from "../risk";
import type { Place, RoutePlan } from "../types";
import HeatLayer from "./HeatLayer";
import { ROUTE_COLORS } from "./RouteList";

interface Props {
  routes: RoutePlan[];
  selectedId: string | null;
  origin: Place | null;
  destination: Place | null;
  showHeat: boolean;
  hour: number;
  intervalMiles: number;
  onSelect: (id: string) => void;
}

const TILE_URL = import.meta.env.VITE_TILE_URL ?? "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const US_CENTER: L.LatLngTuple = [39.5, -98.35];

function FitToRoutes({ routes }: { routes: RoutePlan[] }) {
  const map = useMap();
  useEffect(() => {
    if (routes.length === 0) return;
    const bounds = L.latLngBounds(routes.flatMap((r) => r.geometry));
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [map, routes]);
  return null;
}

export default function MapView({ routes, selectedId, origin, destination, showHeat, hour, intervalMiles, onSelect }: Props) {
  // Draw the selected route last so it sits on top.
  const ordered = [...routes].sort((a, b) => Number(a.id === selectedId) - Number(b.id === selectedId));

  return (
    <MapContainer center={US_CENTER} zoom={4} preferCanvas className="map">
      <TileLayer url={TILE_URL} attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' />
      <FitToRoutes routes={routes} />

      {ordered.map((r) => {
        const selected = r.id === selectedId;
        return (
          <Polyline
            key={r.id}
            positions={r.geometry}
            eventHandlers={{ click: () => onSelect(r.id) }}
            pathOptions={{ color: ROUTE_COLORS[r.id], weight: selected ? 6 : 3, opacity: selected ? 0.9 : 0.5 }}
          />
        );
      })}

      {showHeat && <HeatLayer routes={routes} hour={hour} intervalMiles={intervalMiles} />}

      {ordered.flatMap((r) =>
        r.checkpoints.map((c) => (
          <CircleMarker
            key={`${r.id}-${c.index}`}
            center={[c.lat, c.lon]}
            radius={r.id === selectedId ? 6 : 4}
            pathOptions={{ color: "#fff", weight: 1, fillColor: riskColor(c.risk.level), fillOpacity: 0.95 }}
          >
            <Popup>
              <strong>
                {r.label} · mile {c.mile}
              </strong>
              <br />
              ETA {formatDateTime(c.eta)}
              <br />
              Risk: <b style={{ color: riskColor(c.risk.level) }}>{c.risk.label}</b>
              {c.risk.drivers.length > 0 && ` (${c.risk.drivers.join(", ")})`}
              <br />
              Wind {c.weather.wind_mph} mph · Rain {c.weather.rain_in_hr} in/hr · Snow {c.weather.snow_in_hr} in/hr
              {!c.forecast_available && <><br /><em>Beyond forecast window</em></>}
            </Popup>
          </CircleMarker>
        )),
      )}

      {origin && <CircleMarker center={[origin.lat, origin.lon]} radius={9} pathOptions={{ color: "#111", fillColor: "#fff", fillOpacity: 1, weight: 3 }}><Popup>Origin: {origin.label}</Popup></CircleMarker>}
      {destination && <CircleMarker center={[destination.lat, destination.lon]} radius={9} pathOptions={{ color: "#111", fillColor: "#111", fillOpacity: 1, weight: 3 }}><Popup>Destination: {destination.label}</Popup></CircleMarker>}
    </MapContainer>
  );
}
