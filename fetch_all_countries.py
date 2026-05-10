"""
Fetch all sovereign countries from Wikidata.

v6 changes (vs v5):
  - Splits categorical query into TWO queries to avoid timeouts:
      Categorical-A: continents, governments, languages, currencies, border_count
      Categorical-B: memberships (isolated because P463 is very heavy)
  - Merges all three queries into the final clean CSV.
"""

from pathlib import Path
import time
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "CountryComparison/0.2 (educational project)"

CACHE_DIR = Path("data")
RAW_NUMERIC = CACHE_DIR / "countries_numeric.csv"
RAW_CATEGORICAL_A = CACHE_DIR / "countries_categorical_a.csv"
RAW_CATEGORICAL_B = CACHE_DIR / "countries_categorical_b.csv"
CLEAN_CACHE = CACHE_DIR / "countries_clean.csv"


# ─────────────────────────────────────────────────────────────────────
# Query 1: numerical and single-valued fields
# ─────────────────────────────────────────────────────────────────────
QUERY_NUMERIC = """
SELECT
  ?country ?countryLabel ?iso2 ?iso3
  ?area ?population ?life_expectancy ?hdi
  ?gdp_nominal ?gdp_nominal_year
  ?inception ?driving_side_label
WHERE {
  ?country wdt:P31 wd:Q3624078.
  ?country wdt:P297 ?iso2.
  OPTIONAL { ?country wdt:P298 ?iso3. }
  FILTER NOT EXISTS { ?country wdt:P576 ?dissolved. }

  OPTIONAL { ?country wdt:P2046 ?area. }
  OPTIONAL { ?country wdt:P1082 ?population. }
  OPTIONAL { ?country wdt:P2250 ?life_expectancy. }
  OPTIONAL { ?country wdt:P1081 ?hdi. }
  OPTIONAL { ?country wdt:P571  ?inception. }

  OPTIONAL {
    ?country p:P2131 ?gdp_stmt.
    ?gdp_stmt ps:P2131 ?gdp_nominal.
    OPTIONAL { ?gdp_stmt pq:P585 ?gdp_nominal_year. }
  }

  OPTIONAL {
    ?country wdt:P1622 ?driving_side.
    ?driving_side rdfs:label ?driving_side_label.
    FILTER(LANG(?driving_side_label) = "en")
  }

  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
ORDER BY ?countryLabel
"""

NUMERIC_COLS = [
    "country", "countryLabel", "iso2", "iso3",
    "area", "population", "life_expectancy", "hdi",
    "gdp_nominal", "gdp_nominal_year",
    "inception", "driving_side_label",
]


# ─────────────────────────────────────────────────────────────────────
# Query 2: light categorical fields (the original set)
# ─────────────────────────────────────────────────────────────────────
QUERY_CATEGORICAL_A = """
SELECT
  ?country
  (GROUP_CONCAT(DISTINCT ?continentLabel; separator=" | ") AS ?continents)
  (GROUP_CONCAT(DISTINCT ?governmentLabel; separator=" | ") AS ?governments)
  (GROUP_CONCAT(DISTINCT ?languageLabel;   separator=" | ") AS ?languages)
  (GROUP_CONCAT(DISTINCT ?currencyLabel;   separator=" | ") AS ?currencies)
  (COUNT(DISTINCT ?neighbour) AS ?border_count)
WHERE {
  ?country wdt:P31 wd:Q3624078.
  ?country wdt:P297 ?iso2.
  FILTER NOT EXISTS { ?country wdt:P576 ?dissolved. }

  OPTIONAL { ?country wdt:P30  ?continent. }
  OPTIONAL { ?country wdt:P122 ?government. }
  OPTIONAL { ?country wdt:P37  ?language. }
  OPTIONAL { ?country wdt:P38  ?currency. }
  OPTIONAL { ?country wdt:P47  ?neighbour. }

  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en".
    ?continent  rdfs:label ?continentLabel.
    ?government rdfs:label ?governmentLabel.
    ?language   rdfs:label ?languageLabel.
    ?currency   rdfs:label ?currencyLabel.
  }
}
GROUP BY ?country
"""

CATEGORICAL_A_COLS = [
    "country", "continents", "governments", "languages",
    "currencies", "border_count",
]


# ─────────────────────────────────────────────────────────────────────
# Query 3: memberships only (heavy — isolated)
# ─────────────────────────────────────────────────────────────────────
QUERY_CATEGORICAL_B = """
SELECT
  ?country
  (GROUP_CONCAT(DISTINCT ?membershipLabel; separator=" | ") AS ?memberships)
WHERE {
  ?country wdt:P31 wd:Q3624078.
  ?country wdt:P297 ?iso2.
  FILTER NOT EXISTS { ?country wdt:P576 ?dissolved. }

  OPTIONAL { ?country wdt:P463 ?membership. }

  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en".
    ?membership rdfs:label ?membershipLabel.
  }
}
GROUP BY ?country
"""

CATEGORICAL_B_COLS = ["country", "memberships"]


def run_sparql(query: str, columns: list[str], label: str, max_retries: int = 3) -> pd.DataFrame:
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[{label}] attempt {attempt}/{max_retries}...")
            sparql = SPARQLWrapper(ENDPOINT, agent=USER_AGENT)
            sparql.setQuery(query)
            sparql.setReturnFormat(JSON)
            sparql.setTimeout(180)
            results = sparql.query().convert()

            rows = [
                {col: b[col]["value"] if col in b else None for col in columns}
                for b in results["results"]["bindings"]
            ]
            df = pd.DataFrame(rows)
            print(f"  [{label}] returned {len(df)} rows")
            return df
        except Exception as e:
            last_err = e
            print(f"  [{label}] attempt {attempt} failed: {type(e).__name__}: {e}")
            if attempt < max_retries:
                wait = 5 * attempt
                print(f"  Waiting {wait}s before retry...")
                time.sleep(wait)
    raise RuntimeError(f"[{label}] all attempts failed. Last error: {last_err}")


def keep_most_recent_gdp(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["gdp_nominal_year"] = pd.to_datetime(df["gdp_nominal_year"], errors="coerce", utc=True)
    df = df.sort_values("gdp_nominal_year", ascending=False)
    df = df.drop_duplicates(subset=["country"], keep="first")
    return df.sort_values("countryLabel").reset_index(drop=True)


def fetch_one(query: str, columns: list[str], path: Path, label: str,
              force_refresh: bool = False) -> pd.DataFrame:
    if path.exists() and not force_refresh:
        print(f"Loading cached {label} from {path}")
        return pd.read_csv(path)
    df = run_sparql(query, columns, label)
    df.to_csv(path, index=False)
    return df


def coverage_report(df: pd.DataFrame) -> None:
    print("\n=== Field coverage ===")
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
        print(f"  {col:22s} {n_present:4d}/{total} ({pct:5.1f}%)")


if __name__ == "__main__":
    import sys

    force = "--refresh" in sys.argv
    CACHE_DIR.mkdir(exist_ok=True)

    numeric_df       = fetch_one(QUERY_NUMERIC,       NUMERIC_COLS,       RAW_NUMERIC,       "numeric",        force)
    categorical_a_df = fetch_one(QUERY_CATEGORICAL_A, CATEGORICAL_A_COLS, RAW_CATEGORICAL_A, "categorical-A",  force)
    categorical_b_df = fetch_one(QUERY_CATEGORICAL_B, CATEGORICAL_B_COLS, RAW_CATEGORICAL_B, "memberships",    force)

    numeric_clean = keep_most_recent_gdp(numeric_df)
    merged = numeric_clean.merge(categorical_a_df, on="country", how="left") \
                          .merge(categorical_b_df, on="country", how="left")
    merged.to_csv(CLEAN_CACHE, index=False)

    print(f"\n=== Cleaned data ===")
    print(f"  Total countries: {len(merged)}")
    print(f"  Saved to: {CLEAN_CACHE}")

    coverage_report(merged)

    print("\n=== Sample (first 10) ===")
    print(merged[["countryLabel", "iso3", "driving_side_label",
                  "border_count", "memberships"]]
          .head(10).to_string(index=False))