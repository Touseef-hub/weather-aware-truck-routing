import type { Layer } from "leaflet";
import { HeatLayer as LeafletHeatLayer } from "leaflet.heat";
import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import type { RoutePlan } from "../types";

interface Props {
  routes: RoutePlan[];
  hour: number;
  intervalMiles: number;
}

type HeatPoint = [number, number, number];

const GRADIENT = { 0.2: "#2e9e5b", 0.4: "#e6c229", 0.6: "#f08a24", 0.8: "#d93a2b", 1.0: "#5b1a8f" };

/**
 * Corridor heatmap. The heat layer is created once; the slider only swaps its
 * data (a cheap canvas redraw), so scrubbing never re-renders React children.
 */
export default function HeatLayer({ routes, hour, intervalMiles }: Props) {
  const map = useMap();
  const layerRef = useRef<LeafletHeatLayer | null>(null);

  useEffect(() => {
    const layer = new LeafletHeatLayer([], { radius: 28, blur: 22, minOpacity: 0.35, max: 1, gradient: GRADIENT });
    // leaflet.heat's types target Leaflet 2; at runtime it is a normal Leaflet 1.9 layer.
    const asLayer = layer as unknown as Layer;
    map.addLayer(asLayer);
    layerRef.current = layer;
    return () => {
      map.removeLayer(asLayer);
      layerRef.current = null;
    };
  }, [map]);

  useEffect(() => {
    // Wider spacing leaves gaps, so grow the blob radius with the checkpoint interval.
    layerRef.current?.setOptions({ radius: Math.max(22, intervalMiles * 1.1), blur: 22 });
  }, [intervalMiles]);

  useEffect(() => {
    const points: HeatPoint[] = routes.flatMap((r) =>
      r.checkpoints.map((c): HeatPoint => [c.lat, c.lon, (c.hourly_risk[hour] + 0.5) / 4.5]),
    );
    layerRef.current?.setLatLngs(points);
  }, [routes, hour]);

  return null;
}
