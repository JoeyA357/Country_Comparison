import CountrySlot from "./CountrySlot";
import BreakdownBar from "./BreakdownBar";
import { similarityPercentile } from "../lib/stats";

const COLOR_A = "#00ffd1";
const COLOR_B = "#ff8c42";

export default function RightPanel({ data, mode, selection }) {
  const { selectedA, selectedB, onPickA, onPickB, onClearA, onClearB } = selection;

  const countryA = selectedA ? data.lookup.byIso3[selectedA] : null;
  const countryB = selectedB ? data.lookup.byIso3[selectedB] : null;
  const clusterA = countryA ? data.lookup.clusterById[countryA.cluster] : null;
  const clusterB = countryB ? data.lookup.clusterById[countryB.cluster] : null;

  const result = (selectedA && selectedB)
    ? data.lookup.pair(selectedA, selectedB)
    : null;

  const breakdown = result
    ? [...result.breakdown].sort((a, b) => b.cost - a.cost)
    : null;

  const maxCost = breakdown ? Math.max(...breakdown.map(b => b.cost), 0.001) : 1;
  const pctile = result ? similarityPercentile(result.similarity, data.pairs) : null;

  return (
    <div className="hud-panel hud-panel-corner h-full flex flex-col p-3">
      <div className="hud-header mb-2">PAIRWISE ANALYSIS</div>

      {/* Country slots */}
      <div className="space-y-2 mb-3">
        <CountrySlot
          slotLabel="A" slotColor={COLOR_A}
          country={countryA} cluster={clusterA}
          countries={data.countries} lookup={data.lookup}
          otherSelectedIso3={selectedB}
          onPick={onPickA} onClear={onClearA}
        />
        <CountrySlot
          slotLabel="B" slotColor={COLOR_B}
          country={countryB} cluster={clusterB}
          countries={data.countries} lookup={data.lookup}
          otherSelectedIso3={selectedA}
          onPick={onPickB} onClear={onClearB}
        />
      </div>

      {/* Similarity score */}
      <div className="border-y border-hud-panelEdge py-3 mb-3">
        <div className="text-hud-textDim text-xs mb-1">SIMILARITY</div>
        {result ? (
          <>
            <div className="text-hud-accent text-3xl font-bold">
              {(result.similarity * 100).toFixed(1)}%
            </div>
            {pctile !== null && (
              <div className="text-hud-textDim text-xs mt-1">
                {pctile === 0
                  ? "least similar pair in dataset"
                  : pctile === 1
                  ? "most similar pair in dataset"
                  : `more similar than ${(pctile * 100).toFixed(0)}% of all pairs`
                }
              </div>
            )}
          </>
        ) : (
          <div className="text-hud-textDim text-2xl">--.-%</div>
        )}
      </div>

      {/* Per-leaf breakdown */}
      <div className="flex-1 overflow-auto pr-1">
        <div className="text-hud-textDim text-xs mb-2">PER-LEAF BREAKDOWN</div>
        {breakdown ? (
          <div>
            {breakdown.map(b => (
              <BreakdownBar
                key={b.path}
                path={b.path}
                cost={b.cost}
                maxCost={maxCost}
              />
            ))}
          </div>
        ) : (
          <div className="text-hud-textDim text-xs italic">
            select two countries to view breakdown
          </div>
        )}
      </div>
    </div>
  );
}