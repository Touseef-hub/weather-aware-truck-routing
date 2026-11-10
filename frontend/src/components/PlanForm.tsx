import { FormEvent, useState } from "react";
import { toLocalInputValue } from "../format";
import type { PlanInput, Place } from "../types";
import PlaceInput from "./PlaceInput";

interface Props {
  loading: boolean;
  onSubmit: (input: PlanInput) => void;
}

const INTERVALS = [10, 25, 50] as const;

export default function PlanForm({ loading, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null);
  const [destination, setDestination] = useState<Place | null>(null);
  const [departure, setDeparture] = useState(() => toLocalInputValue(new Date(Date.now() + 30 * 60_000)));
  const [load, setLoad] = useState("42000");
  const [interval, setInterval] = useState<(typeof INTERVALS)[number]>(25);
  const [error, setError] = useState<string | null>(null);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const loadLb = Number(load);
    if (!origin || !destination) return setError("Pick an origin and destination from the suggestions.");
    if (!departure) return setError("Choose a departure date and time.");
    if (!Number.isFinite(loadLb) || loadLb < 0) return setError("Enter a valid load weight in pounds.");
    setError(null);
    onSubmit({
      origin,
      destination,
      departure: new Date(departure).toISOString(),
      load_lb: loadLb,
      interval_miles: interval,
    });
  };

  return (
    <form className="plan-form" onSubmit={submit}>
      <PlaceInput label="Origin" value={origin} onChange={setOrigin} />
      <PlaceInput label="Destination" value={destination} onChange={setDestination} />
      <div className="row">
        <label className="field">
          <span>Departure</span>
          <input type="datetime-local" value={departure} onChange={(e) => setDeparture(e.target.value)} />
        </label>
        <label className="field">
          <span>Load (lb)</span>
          <input type="number" min={0} step={500} value={load} onChange={(e) => setLoad(e.target.value)} />
        </label>
      </div>
      <fieldset className="field">
        <legend>Weather checkpoint every</legend>
        <div className="segmented">
          {INTERVALS.map((miles) => (
            <button
              type="button"
              key={miles}
              className={miles === interval ? "active" : ""}
              onClick={() => setInterval(miles)}
            >
              {miles} mi
            </button>
          ))}
        </div>
      </fieldset>
      {error && <p className="error">{error}</p>}
      <button className="primary" type="submit" disabled={loading}>
        {loading ? "Analysing routes…" : "Find safest route"}
      </button>
    </form>
  );
}
