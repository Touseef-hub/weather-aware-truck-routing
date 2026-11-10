import { useEffect, useRef, useState } from "react";
import { searchPlaces } from "../services/api";
import type { Place } from "../types";

interface Props {
  label: string;
  value: Place | null;
  onChange: (place: Place | null) => void;
}

const DEBOUNCE_MS = 400;

export default function PlaceInput({ label, value, onChange }: Props) {
  const [text, setText] = useState(value?.label ?? "");
  const [options, setOptions] = useState<Place[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const skipNextSearch = useRef(false);

  useEffect(() => {
    if (skipNextSearch.current) {
      skipNextSearch.current = false;
      return;
    }
    if (text.trim().length < 3) {
      setOptions([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        setOptions(await searchPlaces(text, controller.signal));
        setOpen(true);
      } catch {
        /* aborted or service hiccup: keep the previous options */
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [text]);

  const choose = (place: Place) => {
    skipNextSearch.current = true;
    setText(place.label);
    setOpen(false);
    onChange(place);
  };

  return (
    <label className="field">
      <span>{label}</span>
      <div className="place-input">
        <input
          value={text}
          placeholder="City, address or landmark"
          onChange={(e) => {
            setText(e.target.value);
            if (value) onChange(null); // typing invalidates the earlier selection
          }}
          onFocus={() => options.length > 0 && setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          aria-autocomplete="list"
        />
        {loading && <span className="spinner" aria-label="Searching" />}
        {open && options.length > 0 && (
          <ul className="suggestions" role="listbox">
            {options.map((p) => (
              <li key={`${p.lat},${p.lon}`} role="option" aria-selected={false} onMouseDown={() => choose(p)}>
                {p.label}
              </li>
            ))}
          </ul>
        )}
      </div>
    </label>
  );
}
