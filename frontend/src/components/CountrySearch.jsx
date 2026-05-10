import { useEffect, useMemo, useRef, useState } from "react";

const MAX_RESULTS = 8;

/**
 * Compact country picker for the pairwise slots.
 * Renders an input that opens a floating dropdown of matches.
 *
 * `slotLabel`  — "A" or "B" (used in placeholder)
 * `slotColor`  — cyan or amber (used for focus/border accent)
 * `countries`  — array of country objects (must have iso3 + name)
 * `lookup`     — { byIso3, clusterById, ... } for resolving cluster colors
 * `excludeIso3` — iso3 to hide from results (so you can't pick the same country in both slots)
 * `onPick`     — (iso3) => void  called when user selects a result
 */
export default function CountrySearch({
  slotLabel, slotColor, countries, lookup, excludeIso3, onPick,
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const wrapperRef = useRef();

  // Compute matches (memoized per query)
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const prefix = [];
    const sub = [];
    for (const c of countries) {
      if (c.iso3 === excludeIso3) continue;
      const name = c.name.toLowerCase();
      const iso = c.iso3.toLowerCase();
      if (name.startsWith(q) || iso === q) prefix.push(c);
      else if (name.includes(q) || iso.startsWith(q)) sub.push(c);
    }
    return [...prefix, ...sub].slice(0, MAX_RESULTS);
  }, [query, countries, excludeIso3]);

  // Keep activeIdx in range whenever matches change
  useEffect(() => {
    setActiveIdx(0);
  }, [matches]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const handleKeyDown = (e) => {
    if (e.key === "Escape") { setOpen(false); return; }
    if (!matches.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx(i => Math.min(i + 1, matches.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx(i => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const pick = matches[activeIdx];
      if (pick) {
        onPick(pick.iso3);
        setQuery("");
        setOpen(false);
      }
    }
  };

  const handlePick = (iso3) => {
    onPick(iso3);
    setQuery("");
    setOpen(false);
  };

  return (
    <div
      ref={wrapperRef}
      className="border p-2 relative"
      style={{ borderColor: "#1a2430" }}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="text-xs font-bold tracking-widest" style={{ color: "#5a6878" }}>
          COUNTRY {slotLabel}
        </div>
      </div>

      <input
        type="text"
        value={query}
        onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={`search or click globe...`}
        className="w-full bg-transparent border-none outline-none text-hud-text text-sm
                   placeholder-hud-textDim font-mono"
        style={{ caretColor: slotColor }}
      />

      {open && matches.length > 0 && (
        <div
          className="absolute left-0 right-0 top-full mt-1 z-30 hud-panel"
          style={{ borderColor: slotColor }}
        >
          {matches.map((c, idx) => {
            const cluster = lookup.clusterById[c.cluster];
            const isActive = idx === activeIdx;
            return (
              <div
                key={c.iso3}
                onMouseEnter={() => setActiveIdx(idx)}
                onMouseDown={(e) => { e.preventDefault(); handlePick(c.iso3); }}
                className={`flex items-center gap-2 px-2 py-1 cursor-pointer text-xs
                            ${isActive ? "bg-hud-accent/15" : ""}`}
              >
                {cluster && (
                  <div
                    className="w-2 h-2 flex-shrink-0"
                    style={{
                      background: cluster.color,
                      boxShadow: `0 0 3px ${cluster.color}`,
                    }}
                  />
                )}
                <div className="flex-1 truncate text-hud-text">{c.name}</div>
                <div className="text-hud-textDim">{c.iso3}</div>
              </div>
            );
          })}
        </div>
      )}

      {open && query.trim() && matches.length === 0 && (
        <div
          className="absolute left-0 right-0 top-full mt-1 z-30 hud-panel px-2 py-1
                     text-hud-textDim text-xs italic"
        >
          no matches
        </div>
      )}
    </div>
  );
}