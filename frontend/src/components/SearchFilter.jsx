/**
 * Text search filter. Filters countries by name or ISO code.
 * Result count and clear button shown inline.
 */
export default function SearchFilter({ filters, totalCount }) {
  const { search, setSearch, matchedIso3s } = filters;
  const matchCount = matchedIso3s ? matchedIso3s.size : totalCount;

  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-1">
        <div className="text-hud-textDim text-xs">FILTER</div>
        <div className="text-hud-textDim text-xs">
          {search.trim()
            ? `${matchCount}/${totalCount} match`
            : `${totalCount} total`}
        </div>
      </div>

      <div className="relative">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="search countries..."
          className="w-full bg-transparent border border-hud-panelEdge
                     focus:border-hud-accent outline-none px-2 py-1 pr-7
                     text-hud-text text-sm placeholder-hud-textDim font-mono"
        />
        {search && (
          <button
            onClick={() => setSearch("")}
            className="absolute right-1 top-1/2 -translate-y-1/2
                       text-hud-textDim hover:text-hud-accent text-xs px-1"
            title="Clear"
          >×</button>
        )}
      </div>
    </div>
  );
}