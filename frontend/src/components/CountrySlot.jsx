import CountrySearch from "./CountrySearch";

/**
 * One of the two country slots in the Pairwise Analysis panel.
 *
 * Two states:
 *   - Empty   → renders <CountrySearch>, accepting clicks from the globe OR
 *               text-search picks
 *   - Filled  → renders the country card with a clear (×) button
 */
export default function CountrySlot({
  slotLabel, slotColor, country, cluster,
  countries, lookup, otherSelectedIso3, onPick, onClear,
}) {
  // Empty state: render the search
  if (!country) {
    return (
      <CountrySearch
        slotLabel={slotLabel}
        slotColor={slotColor}
        countries={countries}
        lookup={lookup}
        excludeIso3={otherSelectedIso3}
        onPick={onPick}
      />
    );
  }

  // Filled state: card with clear button
  return (
    <div
      className="border p-2 transition-colors relative"
      style={{ borderColor: slotColor }}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="text-xs font-bold tracking-widest" style={{ color: slotColor }}>
          COUNTRY {slotLabel}
        </div>
        <div className="flex items-center gap-2">
          <div className="text-hud-textDim text-xs">[{country.iso3}]</div>
          <button
            onClick={onClear}
            className="text-hud-textDim hover:text-hud-danger text-base leading-none"
            title="Clear"
          >×</button>
        </div>
      </div>

      <div className="text-hud-text text-sm font-bold mb-1">{country.name}</div>
      {cluster && (
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 flex-shrink-0"
            style={{ background: cluster.color, boxShadow: `0 0 4px ${cluster.color}` }}
          />
          <div className="text-hud-textDim text-xs truncate">
            CL{cluster.id} · {cluster.label}
          </div>
        </div>
      )}
    </div>
  );
}