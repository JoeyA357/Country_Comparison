# Development tool — not part of the production pipeline; may be outdated.

"""
First SPARQL query to Wikidata.
Goal: fetch a small set of properties for 5 diverse countries
to validate the data pipeline before scaling up.
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd

# Wikidata SPARQL endpoint
ENDPOINT = "https://query.wikidata.org/sparql"

# A user-agent is required by Wikidata's policy
USER_AGENT = "CountryComparison/0.1 (educational project)"

# 5 countries chosen for their diversity:
# France (Q142), Japan (Q17), Brazil (Q155), Egypt (Q79), New Zealand (Q664)
COUNTRY_IDS = ["Q142", "Q17", "Q155", "Q79", "Q664"]

# Build a VALUES clause for the query
values_clause = " ".join(f"wd:{qid}" for qid in COUNTRY_IDS)

QUERY = f"""
SELECT ?country ?countryLabel ?area ?population ?gdp_nominal ?gdp_ppp ?continentLabel ?governmentLabel
WHERE {{
  VALUES ?country {{ {values_clause} }}

  OPTIONAL {{ ?country wdt:P2046 ?area. }}            # area in km²
  OPTIONAL {{ ?country wdt:P1082 ?population. }}      # population
  OPTIONAL {{ ?country wdt:P2131 ?gdp_nominal. }}     # GDP nominal (USD)
  OPTIONAL {{ ?country wdt:P2132 ?gdp_ppp. }}         # GDP PPP (USD)
  OPTIONAL {{ ?country wdt:P30   ?continent. }}       # continent
  OPTIONAL {{ ?country wdt:P122  ?government. }}      # basic form of government

  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
"""


def run_query():
    sparql = SPARQLWrapper(ENDPOINT, agent=USER_AGENT)
    sparql.setQuery(QUERY)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    # Flatten the JSON results into rows
    rows = []
    for binding in results["results"]["bindings"]:
        row = {key: binding[key]["value"] if key in binding else None
               for key in ["countryLabel", "area", "population",
                           "gdp_nominal", "gdp_ppp",
                           "continentLabel", "governmentLabel"]}
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


if __name__ == "__main__":
    df = run_query()
    print("\n=== Raw results ===")
    print(df.to_string(index=False))
    print(f"\nTotal rows: {len(df)}")
    print(f"Unique countries: {df['countryLabel'].nunique()}")
