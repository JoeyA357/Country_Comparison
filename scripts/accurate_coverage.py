# Development tool — not part of the production pipeline; may be outdated.

"""
Accurate coverage report for the cleaned country dataset.
Treats both NaN and empty strings as missing, since SPARQL's GROUP_CONCAT
returns empty strings (not NULL) when no values match.
"""

import pandas as pd
from pathlib import Path

CLEAN = Path("data/countries_clean.csv")
df = pd.read_csv(CLEAN)

print(f"Total countries: {len(df)}\n")
print("=== TRUE field coverage (NaN AND empty strings count as missing) ===")
total = len(df)
for col in df.columns:
    if col in ("country", "countryLabel", "iso2", "iso3", "gdp_nominal_year"):
        continue
    series = df[col]
    if series.dtype == object:
        present = series.notna() & (series.astype(str).str.strip() != "")
    else:
        present = series.notna()
    n_present = present.sum()
    pct = 100 * n_present / total
    print(f"  {col:20s} {n_present:4d}/{total} ({pct:5.1f}%)")
