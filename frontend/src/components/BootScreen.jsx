import { useState, useEffect } from "react";

const LINES = [
  "ESTABLISHING UPLINK...",
  "FETCHING WIKIDATA TELEMETRY...",
  "PARSING COUNTRY RECORDS...",
  "BUILDING SIMILARITY GRAPH...",
  "LOADING CLUSTER ASSIGNMENTS...",
  "MOUNTING FRONTEND PAYLOAD...",
];

const LINE_MS = 280;

export default function BootScreen() {
  const [count, setCount] = useState(1);
  const [blink, setBlink] = useState(true);

  useEffect(() => {
    if (count >= LINES.length) return;
    const t = setTimeout(() => setCount(c => c + 1), LINE_MS);
    return () => clearTimeout(t);
  }, [count]);

  useEffect(() => {
    const t = setInterval(() => setBlink(b => !b), 530);
    return () => clearInterval(t);
  }, []);

  const done = count >= LINES.length;

  return (
    <div className="h-screen w-screen hud-grid flex flex-col items-center justify-center">
      <div className="hud-panel p-8 min-w-[400px]">
        <div className="text-hud-accent font-bold tracking-widest text-sm mb-5">
          ◆ COUNTRY-COMPARE — SYSTEM BOOT
        </div>

        <div className="space-y-1 font-mono text-xs">
          {LINES.slice(0, count).map((line, i) => {
            const isCurrent = i === count - 1;
            const isComplete = i < count - 1 || done;
            return (
              <div key={i} className="flex items-center justify-between gap-6">
                <span className="flex items-center gap-2">
                  <span className="text-hud-accent">›</span>
                  <span className="text-hud-text">{line}</span>
                  {isCurrent && !done && (
                    <span className="text-hud-accent" style={{ opacity: blink ? 1 : 0 }}>▌</span>
                  )}
                </span>
                {isComplete && (
                  <span className="text-green-400 tracking-widest">OK</span>
                )}
              </div>
            );
          })}

          {done && (
            <div className="flex items-center gap-2 mt-3 border-t border-hud-panelEdge pt-3">
              <span className="text-hud-accent">›</span>
              <span className="text-hud-accent font-bold tracking-widest">SYSTEM READY</span>
              <span className="text-hud-accent" style={{ opacity: blink ? 1 : 0 }}>▌</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
