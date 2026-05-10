# COUNTRY-COMPARE

A country comparison and clustering web app that uses [Wikidata](https://www.wikidata.org/) as its data source, the Nierman & Jagadish tree edit distance (TED) algorithm for pairwise similarity, agglomerative hierarchical clustering for grouping, and a 3D HUD-styled globe interface for exploration. Users can click any two countries on the globe to get a per-leaf similarity breakdown, spotlight a cluster to highlight its members, and browse a force-directed graph of cluster relationships.

---

## Pipeline overview

The data pipeline runs in four sequential stages, each producing files consumed by the next.

```
Wikidata SPARQL
    │
    ▼
1. fetch_all_countries.py
   reads:   Wikidata SPARQL endpoint
   writes:  data/countries_clean.csv
    │
    ▼
2. tree_builder.py
   reads:   data/countries_clean.csv
   writes:  data/country_trees.json   (194 hierarchical country trees)
    │
    ▼
3. cluster.py
   reads:   data/country_trees.json
   writes:  data/similarity_matrix.npz  (194×194 pairwise TED similarities)
            data/clusters.json          (cluster assignments + probabilities)
    │
    ▼
4. build_frontend_data.py
   reads:   data/country_trees.json
            data/clusters.json
            data/similarity_matrix.npz
   writes:  frontend/public/data/countries.json
            frontend/public/data/clusters.json
            frontend/public/data/pairs.json
```

The React app loads the three JSON files from `frontend/public/data/` at runtime — no backend server is needed in production.

---

## Methodology

### Why tree edit distance?

Country profiles are naturally hierarchical (Geography → Area, Continents; Economy → GDP, HDI, Currencies; etc.) with heterogeneous leaf types: some leaves are continuous numerical values (population, GDP), some are unordered sets (languages, memberships), and some are single categorical values (driving side). Standard feature-vector distances collapse all of this into a flat representation and lose the structural groupings.

TED respects the tree structure and dispatches to a per-leaf cost function based on the node's `leaf_type`, letting each kind of data be compared on its own terms.

### Cost functions per leaf type

| Leaf type            | Cost function                                     | Range    |
|----------------------|---------------------------------------------------|----------|
| `numerical`          | Absolute percentile-rank difference               | [0, 1]   |
| `set`                | Jaccard distance (1 − Jaccard similarity)         | [0, 1]   |
| `single_categorical` | 0 if equal, 1 if different                        | {0, 1}   |
| Missing value (any)  | Fixed penalty of 0.5                              | —        |

Numerical values are normalized via **percentile rank** rather than min-max or log-scale normalization. This is robust to outliers (e.g., the US GDP vs. Tuvalu), stretches the dynamic range uniformly, and produces a near-uniform cost distribution.

### Leaf weights

Each leaf has a configurable weight that scales its contribution to the total TED. The weights are defined in `leaf_costs.py:LEAF_WEIGHTS` (see the Schema table below).

### Clustering

The pairwise TED similarity matrix is converted to a distance matrix (`distance = 1 − similarity`) and fed to **scipy's agglomerative clustering** with average linkage and a fixed `k = 14`. Every country is assigned to exactly one cluster — there are no "noise" points.

A post-hoc membership probability is computed per country as the inverse of its mean intra-cluster distance, normalized within the cluster to [0.5, 1.0].

---

## Schema

The 14 leaves used in the country trees, their types, branches, and weights:

| Leaf           | Branch       | Type                | Weight |
|----------------|--------------|---------------------|--------|
| Area           | Geography    | numerical           | 0.7    |
| LandBorders    | Geography    | numerical           | 0.5    |
| Continents     | Geography    | set                 | 0.4    |
| Population     | Demographics | numerical           | 0.7    |
| LifeExpectancy | Demographics | numerical           | 0.6    |
| Languages      | Demographics | set                 | 1.0    |
| GDPNominal     | Economy      | numerical           | 0.7    |
| GDPperCapita   | Economy      | numerical (derived) | 1.0    |
| HDI            | Economy      | numerical           | 1.0    |
| Currencies     | Economy      | set                 | 0.5    |
| Governments    | Politics     | set                 | 1.0    |
| DrivingSide    | Politics     | single_categorical  | 1.0    |
| Memberships    | Politics     | set                 | 1.0    |
| InceptionYear  | History      | numerical           | 0.6    |

`GDPperCapita` is derived at tree-build time as `GDPNominal / Population`.

---

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm

### Backend setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run the pipeline

```bash
python run_pipeline.py
```

This fetches data from Wikidata (stage 1 is slow — ~30–90 s depending on endpoint load), builds trees, computes the similarity matrix (194×194 = ~18 721 pairs, a few minutes the first time), clusters, and writes the frontend JSON bundle.

Subsequent runs skip stages whose outputs are already present. To force a full rebuild:

```bash
python run_pipeline.py --refresh
```

The four pipeline scripts can also be run individually for targeted rebuilds or debugging:

```bash
python fetch_all_countries.py   # re-fetch from Wikidata
python tree_builder.py          # rebuild trees from cached CSV
python cluster.py               # recompute similarity + clustering
python build_frontend_data.py   # rebuild frontend bundle only
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The dev server starts on `http://localhost:5173` by default.

---

## Tunable knobs

| Parameter            | File                    | Default   | Effect                                                      |
|----------------------|-------------------------|-----------|-------------------------------------------------------------|
| `LEAF_WEIGHTS`       | `leaf_costs.py`         | see above | Per-leaf contribution to TED; higher weight = more influence |
| `N_CLUSTERS`         | `cluster.py`            | `14`      | Number of clusters extracted from the agglomerative hierarchy |
| `LINKAGE_METHOD`     | `cluster.py`            | `"average"` | scipy linkage method: `"average"` / `"complete"` / `"single"` |
| `MISSING_PENALTY`    | `leaf_costs.py`         | `0.5`     | Cost applied when one or both values are missing            |
| `HUD_PALETTE`        | `build_frontend_data.py`| 16 colors | Cluster dot/legend colors in the UI                         |

After changing `LEAF_WEIGHTS` or `N_CLUSTERS`, rerun from stage 3:

```bash
python cluster.py && python build_frontend_data.py
```

---

## Project structure

```
Country_Comparison/
├── fetch_all_countries.py   # Stage 1: Wikidata SPARQL → data/countries_clean.csv
├── tree_builder.py          # Stage 2: CSV → data/country_trees.json
├── cluster.py               # Stage 3: trees → similarity matrix + cluster assignments
├── build_frontend_data.py   # Stage 4: all data → frontend/public/data/*.json
├── run_pipeline.py          # Orchestrator — runs all 4 stages in order
├── similarity.py            # High-level TED similarity API (used by stages 3+4)
├── ted.py                   # Core tree edit distance implementation
├── leaf_costs.py            # Per-leaf cost functions and LEAF_WEIGHTS config
├── test_ted.py              # Unit tests for the TED implementation
├── requirements.txt         # Python dependencies
├── data/                    # Pipeline intermediate outputs (CSV + JSON + .npz)
├── scripts/                 # Development/diagnostic tools (not part of pipeline)
│   ├── query_test.py
│   ├── query_test_v2.py
│   ├── data_spot_check.py
│   ├── accurate_coverage.py
│   ├── least_similar.py
│   ├── distribution_diagnostic.py
│   └── diagnose_missing.py
└── frontend/
    ├── public/data/         # Final JSON consumed by the React app
    ├── src/
    │   ├── App.jsx          # Root component: state, routing, layout
    │   ├── components/      # Globe, panels, legend, graph, tooltips
    │   └── hooks/           # useAppData — loads and indexes the JSON files
    └── package.json
```

---

## Limitations

- **Narrow similarity distribution.** All pairwise similarities cluster in roughly [0.60, 0.94] with a standard deviation of ~0.04. This is a structural consequence of TED with weighted leaves and many partially-overlapping values — not a bug. The clustering and percentile display account for it, but absolute similarity scores should be interpreted relative to the dataset, not as fractions of a theoretical maximum.

- **Sparse Wikidata fields.** Some fields had too little coverage to include: `religions` (~13%), `capital` (used for geo only). `Governments` has ~80% coverage, which is good enough but means ~20% of countries use a missing-value penalty for that leaf.

- **Hardcoded country centroids.** The globe maps ISO-3 codes to lat/lng centroids baked into the frontend data. If the Wikidata query pulls a country not in that centroid table, its dot will be omitted from the globe (the data is still used for comparison).

- **Cluster sensitivity.** Cluster boundaries — especially between developed vs. developing groupings, or Anglosphere vs. non-Anglosphere — can shift noticeably with small changes to `LEAF_WEIGHTS` or `N_CLUSTERS`. The current weights reflect a deliberate design choice, but there is no single "correct" clustering.

- **Static snapshot.** Wikidata values change over time. The cached `data/` files represent the state at the time the pipeline last ran. Re-running `fetch_all_countries.py --refresh` pulls the current state.

---

## Tech stack

### Backend (Python)

| Package        | Purpose                                      |
|----------------|----------------------------------------------|
| SPARQLWrapper  | Wikidata SPARQL queries                      |
| pandas         | CSV parsing and data cleaning                |
| numpy          | Similarity matrix storage and arithmetic     |
| scipy          | Agglomerative clustering + linkage           |

### Frontend (JavaScript)

| Package               | Purpose                                      |
|-----------------------|----------------------------------------------|
| React 19              | UI framework                                 |
| Vite                  | Build tool and dev server                    |
| Tailwind CSS 3        | Utility-first styling                        |
| react-three-fiber     | React renderer for Three.js (3D globe)       |
| @react-three/drei     | Three.js helpers (OrbitControls, Html, etc.) |
| three                 | WebGL 3D engine                              |
| d3                    | Force-directed cluster graph                 |
