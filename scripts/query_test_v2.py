# Development tool — not part of the production pipeline; may be outdated.

"""
Second SPARQL query to Wikidata.
Improvements over v1:
  - Collapses multi-valued fields (government, continent) into a single row per country
    using GROUP_CONCAT, so we get exactly one row per country.
  - Picks the MOST RECENT GDP value using the point-in-time qualifier (P585).
  - Adds a few more comparison-relevant fields: HDI, life expectancy,
    official language, currency.
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "CountryComparison/0.1 (educational project)"

COUNTRY_IDS = ["Q142", "Q17", "Q155", "Q79", "Q664"]
values_clause = " ".join(f"wd:{qid}" for qid in COUNTRY_IDS)

QUERY = f"""
SELECT
  ?country ?countryLabel
  ?area ?population ?life_expectancy ?hdi
  ?gdp_nominal ?gdp_nominal_year
  (GROUP_CONCAT(DISTINCT ?continentLabel; separator=", ") AS ?continents)
  (GROUP_CONCAT(DISTINCT ?governmentLabel; separator=", ") AS ?governments)
  (GROUP_CONCAT(DISTINCT ?languageLabel;   separator=", ") AS ?languages)
  (GROUP_CONCAT(DISTINCT ?currencyLabel;   separator=", ") AS ?currencies)
WHERE {{
  VALUES ?country {{ {values_clause} }}

  # Single-valued fields
  OPTIONAL {{ ?country wdt:P2046 ?area. }}            # area km²
  OPTIONAL {{ ?country wdt:P1082 ?population. }}      # population
  OPTIONAL {{ ?country wdt:P2250 ?life_expectancy. }} # life expectancy
  OPTIONAL {{ ?country wdt:P1081 ?hdi. }}             # HDI

  # Most-recent GDP nominal (using statement node + P585 qualifier)
  OPTIONAL {{
    ?country p:P2131 ?gdp_stmt.
    ?gdp_stmt ps:P2131 ?gdp_nominal.
    OPTIONAL {{ ?gdp_stmt pq:P585 ?gdp_nominal_year. }}
  }}

  # Multi-valued fields (will be collapsed by GROUP_CONCAT)
  OPTIONAL {{
    ?country wdt:P30 ?continent.
    ?continent rdfs:label ?continentLabel.
    FILTER(LANG(?continentLabel) = "en")
  }}
  OPTIONAL {{
    ?country wdt:P122 ?government.
    ?government rdfs:label ?governmentLabel.
    FILTER(LANG(?governmentLabel) = "en")
  }}
  OPTIONAL {{
    ?country wdt:P37 ?language.
    ?language rdfs:label ?languageLabel.
    FILTER(LANG(?languageLabel) = "en")
  }}
  OPTIONAL {{
    ?country wdt:P38 ?currency.
    ?currency rdfs:label ?currencyLabel.
    FILTER(LANG(?currencyLabel) = "en")
  }}

  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?country ?countryLabel ?area ?population ?life_expectancy ?hdi ?gdp_nominal ?gdp_nominal_year
ORDER BY ?countryLabel
"""


def run_query():
    sparql = SPARQLWrapper(ENDPOINT, agent=USER_AGENT)
    sparql.setQuery(QUERY)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    columns = ["countryLabel", "area", "population", "life_expectancy", "hdi",
               "gdp_nominal", "gdp_nominal_year",
               "continents", "governments", "languages", "currencies"]

    rows = []
    for binding in results["results"]["bindings"]:
        row = {col: binding[col]["value"] if col in binding else None for col in columns}
        rows.append(row)

    return pd.DataFrame(rows)


def keep_most_recent_gdp(df: pd.DataFrame) -> pd.DataFrame:
    """For each country, keep only the row with the most recent GDP year."""
    df = df.copy()
    df["gdp_nominal_year"] = pd.to_datetime(df["gdp_nominal_year"], errors="coerce")
    df = df.sort_values("gdp_nominal_year", ascending=False)
    df = df.drop_duplicates(subset=["countryLabel"], keep="first")
    return df.sort_values("countryLabel").reset_index(drop=True)


if __name__ == "__main__":
    raw_df = run_query()
    print("\n=== Raw results (multiple GDP years per country) ===")
    print(raw_df.to_string(index=False))
    print(f"\nRaw rows: {len(raw_df)}")

    clean_df = keep_most_recent_gdp(raw_df)
    print("\n=== Cleaned results (one row per country, most recent GDP) ===")
    print(clean_df.to_string(index=False))
    print(f"\nClean rows: {len(clean_df)}")
