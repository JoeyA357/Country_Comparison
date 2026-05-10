/**
 * Tooltip rendered as HTML overlay (outside the Canvas).
 * Positioned absolutely at mouse coords passed in via props.
 */
export default function CountryTooltip({ hovered, mouse, lookup }) {
  if (!hovered || !mouse) return null;

  const country = lookup.byIso3[hovered];
  if (!country) return null;

  const cluster = lookup.clusterById[country.cluster];

  // Offset so the tooltip doesn't sit directly under the cursor
  const style = {
    left: mouse.x + 14,
    top: mouse.y + 14,
  };

  return (
    <div
      className="absolute pointer-events-none z-50 hud-panel px-2 py-1 text-xs"
      style={style}
    >
      <div className="flex items-center gap-2 mb-1">
        {cluster && (
          <div
            className="w-2 h-2 flex-shrink-0"
            style={{ background: cluster.color, boxShadow: `0 0 4px ${cluster.color}` }}
          />
        )}
        <div className="text-hud-accent font-bold tracking-wide">
          {country.name}
        </div>
        <div className="text-hud-textDim">
          [{country.iso3}]
        </div>
      </div>
      {cluster && (
        <div className="text-hud-textDim text-[10px]">
          CLUSTER {cluster.id} · {cluster.size} states
        </div>
      )}
    </div>
  );
}