# Development tool — not part of the production pipeline; may be outdated.

"""
Diagnose why categorical fields are showing as missing in the trees
when SPARQL reported 100% coverage.

Checks:
  1. Compare row counts: numeric vs categorical vs merged.
  2. Show raw values for fields that are coming through as "missing".
  3. Inspect a few specific countries (France, Japan, USA) and see
     what's actually in each CSV.
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")

numeric = pd.read_csv(DATA_DIR / "countries_numeric.csv")
categorical = pd.read_csv(DATA_DIR / "countries_categorical.csv")
clean = pd.read_csv(DATA_DIR / "countries_clean.csv")

print("=" * 60)
print("ROW COUNTS")
print("=" * 60)
print(f"  numeric.csv:     {len(numeric)} rows")
print(f"  categorical.csv: {len(categorical)} rows")
print(f"  clean.csv:       {len(clean)} rows")

# Are there any rows in clean.csv that didn't get categorical data?
print("\n" + "=" * 60)
print("MERGE INTEGRITY: rows where categorical fields are all empty/NaN")
print("=" * 60)
cat_cols = ["continents", "governments", "languages", "currencies", "religions"]
empty_mask = clean[cat_cols].isna().all(axis=1) | (
    clean[cat_cols].fillna("").apply(lambda c: c.str.strip()).eq("").all(axis=1)
)
print(f"  Rows with ALL categorical fields empty: {empty_mask.sum()}")
if empty_mask.sum() > 0:
    print(clean.loc[empty_mask, ["countryLabel", "iso3"]].to_string(index=False))

# Now look at religions specifically — it claims 87% missing
print("\n" + "=" * 60)
print("RELIGIONS column inspection")
print("=" * 60)
print(f"  Total rows: {len(clean)}")
print(f"  is NaN:                 {clean['religions'].isna().sum()}")
print(f"  is empty string:        {(clean['religions'].fillna('').str.strip() == '').sum()}")
print(f"  has at least one char:  {(clean['religions'].fillna('').str.strip() != '').sum()}")

# Show some actual values from clean.csv (the merged file)
print("\n  First 15 non-null religion values from clean.csv:")
non_null = clean[clean["religions"].notna() & (clean["religions"].astype(str).str.strip() != "")]
for _, r in non_null.head(15).iterrows():
    print(f"    {r['countryLabel']:30s} → {r['religions']!r}")

# And the same column directly from categorical.csv (pre-merge)
print("\n  First 15 non-null religion values from categorical.csv (pre-merge):")
non_null_cat = categorical[categorical["religions"].notna() &
                            (categorical["religions"].astype(str).str.strip() != "")]
for _, r in non_null_cat.head(15).iterrows():
    print(f"    {r['country']:60s} → {r['religions']!r}")

# Spot-check: France, Japan, USA in each file
print("\n" + "=" * 60)
print("SPOT CHECK: France, Japan, United States — religions value in each file")
print("=" * 60)
spot_q = ["Q142", "Q17", "Q30"]  # France, Japan, USA
for q in spot_q:
    uri = f"http://www.wikidata.org/entity/{q}"
    cat_row = categorical[categorical["country"] == uri]
    cln_row = clean[clean["country"] == uri]
    name = cln_row["countryLabel"].iloc[0] if not cln_row.empty else "(not found)"
    cat_val = cat_row["religions"].iloc[0] if not cat_row.empty else "(missing)"
    cln_val = cln_row["religions"].iloc[0] if not cln_row.empty else "(missing)"
    print(f"\n  {name} ({q}):")
    print(f"    in categorical.csv: {cat_val!r}")
    print(f"    in clean.csv:       {cln_val!r}")
