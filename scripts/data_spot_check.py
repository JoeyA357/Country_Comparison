# Development tool — not part of the production pipeline; may be outdated.

"""
Quick sanity check on the cleaned country data.
Looks at:
  - Which countries are missing key fields (so we know what we're dealing with)
  - A few well-known examples to verify values look right
  - The full list of country names (to spot anything weird in inclusion/exclusion)
"""

import pandas as pd

df = pd.read_csv("data/countries_clean.csv")

print(f"Total countries: {len(df)}\n")

# 1. Countries missing GDP — likely micro-states or recently-recognized
print("=== Countries missing GDP ===")
missing_gdp = df[df["gdp_nominal"].isna()]["countryLabel"].tolist()
print(f"  Count: {len(missing_gdp)}")
print(f"  {missing_gdp}\n")

# 2. Countries missing HDI
print("=== Countries missing HDI ===")
missing_hdi = df[df["hdi"].isna()]["countryLabel"].tolist()
print(f"  Count: {len(missing_hdi)}")
print(f"  {missing_hdi}\n")

# 3. Spot-check a few well-known countries
print("=== Spot-check on well-known countries ===")
spot_check = ["United States of America", "China", "India", "Russia",
              "Germany", "United Kingdom", "Saudi Arabia", "Nigeria"]
for name in spot_check:
    matches = df[df["countryLabel"].str.contains(name, case=False, na=False)]
    if matches.empty:
        print(f"  {name}: NOT FOUND")
    else:
        for _, row in matches.iterrows():
            print(f"  {row['countryLabel']:30s} pop={row['population']:>15,.0f}  "
                  f"gdp={row['gdp_nominal']:>16,.0f}  cont={row['continents']}")

# 4. Full list of country names (in chunks so it's readable)
print("\n=== Full country list ===")
names = sorted(df["countryLabel"].dropna().tolist())
for i in range(0, len(names), 4):
    print("  " + "  ".join(f"{n:30s}" for n in names[i:i+4]))
