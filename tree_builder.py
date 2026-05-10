"""
Build country trees from the cleaned country dataset.

v3 changes (vs v2):
  - Adds new leaves: GDPperCapita (derived), DrivingSide, LandBorders,
    Memberships, InceptionYear.
  - Adds a third leaf_type: 'single_categorical' for binary fields like
    driving side (a Jaccard set of one element would be silly).
  - Reorganizes tree into 5 branches: Geography, Demographics, Economy,
    Politics, History.

Tree schema:

    Country (root, has iso3 attribute)
    ├── Geography
    │   ├── Area              (numerical)
    │   ├── Continents        (set)
    │   └── LandBorders       (numerical)
    ├── Demographics
    │   ├── Population        (numerical)
    │   ├── LifeExpectancy    (numerical)
    │   └── Languages         (set)
    ├── Economy
    │   ├── GDPNominal        (numerical)
    │   ├── GDPperCapita      (numerical, derived)
    │   ├── HDI               (numerical)
    │   └── Currencies        (set)
    ├── Politics
    │   ├── Governments       (set)
    │   ├── DrivingSide       (single_categorical)
    │   └── Memberships       (set)
    └── History
        └── InceptionYear     (numerical)

Each leaf carries:
  - leaf_type: 'numerical' | 'set' | 'single_categorical'
  - value: float | list[str] | str | None
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union, Any
import json
import math
import re

import pandas as pd

DATA_DIR = Path("data")
CLEAN_CSV = DATA_DIR / "countries_clean.csv"
TREES_JSON = DATA_DIR / "country_trees.json"

SET_SEPARATOR = " | "


# ─────────────────────────────────────────────────────────────────────
# Tree data structure
# ─────────────────────────────────────────────────────────────────────
@dataclass
class TreeNode:
    name: str
    children: list["TreeNode"] = field(default_factory=list)
    value: Optional[Union[float, list, str]] = None
    leaf_type: Optional[str] = None       # 'numerical' | 'set' | 'single_categorical'
    iso3: Optional[str] = None

    @property
    def is_leaf(self) -> bool:
        return self.leaf_type is not None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name}
        if self.iso3 is not None:
            d["iso3"] = self.iso3
        if self.is_leaf:
            d["leaf_type"] = self.leaf_type
            d["value"] = self.value
        else:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TreeNode":
        node = cls(name=d["name"])
        node.iso3 = d.get("iso3")
        if "leaf_type" in d:
            node.leaf_type = d["leaf_type"]
            node.value = d.get("value")
        else:
            node.children = [cls.from_dict(c) for c in d.get("children", [])]
        return node


# ─────────────────────────────────────────────────────────────────────
# Parsers
# ─────────────────────────────────────────────────────────────────────
def parse_set(raw: object) -> Optional[list[str]]:
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    s = str(raw).strip()
    if not s:
        return None
    items = sorted({part.strip() for part in s.split(SET_SEPARATOR) if part.strip()})
    return items if items else None


def parse_number(raw: object) -> Optional[float]:
    if raw is None:
        return None
    try:
        v = float(raw)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def parse_categorical(raw: object) -> Optional[str]:
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    s = str(raw).strip().lower()
    return s if s else None


def parse_year(raw: object) -> Optional[float]:
    """Extract a year from a Wikidata ISO datetime string like '1789-07-14T00:00:00Z'.
    Returns it as a float so it lives alongside other numerical values."""
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    s = str(raw).strip()
    if not s:
        return None
    # Handle BCE dates (start with '-') by capturing the leading sign
    m = re.match(r"^(-?)(\d{1,4})", s)
    if not m:
        return None
    sign, year = m.groups()
    return -float(year) if sign == "-" else float(year)


# ─────────────────────────────────────────────────────────────────────
# Leaf factories
# ─────────────────────────────────────────────────────────────────────
def num_leaf(name: str, raw: object) -> TreeNode:
    return TreeNode(name=name, leaf_type="numerical", value=parse_number(raw))


def set_leaf(name: str, raw: object) -> TreeNode:
    return TreeNode(name=name, leaf_type="set", value=parse_set(raw))


def cat_leaf(name: str, raw: object) -> TreeNode:
    return TreeNode(name=name, leaf_type="single_categorical", value=parse_categorical(raw))


def year_leaf(name: str, raw: object) -> TreeNode:
    return TreeNode(name=name, leaf_type="numerical", value=parse_year(raw))


def derived_gdp_per_capita(row: pd.Series) -> Optional[float]:
    gdp = parse_number(row.get("gdp_nominal"))
    pop = parse_number(row.get("population"))
    if gdp is None or pop is None or pop <= 0:
        return None
    return gdp / pop


# ─────────────────────────────────────────────────────────────────────
# Tree construction
# ─────────────────────────────────────────────────────────────────────
def build_country_tree(row: pd.Series) -> TreeNode:
    geography = TreeNode("Geography", children=[
        num_leaf("Area", row.get("area")),
        set_leaf("Continents", row.get("continents")),
        num_leaf("LandBorders", row.get("border_count")),
    ])

    demographics = TreeNode("Demographics", children=[
        num_leaf("Population", row.get("population")),
        num_leaf("LifeExpectancy", row.get("life_expectancy")),
        set_leaf("Languages", row.get("languages")),
    ])

    economy = TreeNode("Economy", children=[
        num_leaf("GDPNominal", row.get("gdp_nominal")),
        TreeNode(name="GDPperCapita", leaf_type="numerical",
                 value=derived_gdp_per_capita(row)),
        num_leaf("HDI", row.get("hdi")),
        set_leaf("Currencies", row.get("currencies")),
    ])

    politics = TreeNode("Politics", children=[
        set_leaf("Governments", row.get("governments")),
        cat_leaf("DrivingSide", row.get("driving_side_label")),
        set_leaf("Memberships", row.get("memberships")),
    ])

    history = TreeNode("History", children=[
        year_leaf("InceptionYear", row.get("inception")),
    ])

    iso3 = str(row["iso3"]) if pd.notna(row.get("iso3")) else None
    return TreeNode(
        name=str(row["countryLabel"]),
        children=[geography, demographics, economy, politics, history],
        iso3=iso3,
    )


def build_all_trees(df: pd.DataFrame) -> dict[str, TreeNode]:
    trees: dict[str, TreeNode] = {}
    for _, row in df.iterrows():
        key = str(row["iso3"]) if pd.notna(row.get("iso3")) else str(row["countryLabel"])
        trees[key] = build_country_tree(row)
    return trees


# ─────────────────────────────────────────────────────────────────────
# Save / load
# ─────────────────────────────────────────────────────────────────────
def save_trees_json(trees: dict[str, TreeNode], path: Path = TREES_JSON) -> None:
    payload = {iso3: tree.to_dict() for iso3, tree in trees.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(trees)} trees to {path} ({path.stat().st_size:,} bytes)")


def load_trees_json(path: Path = TREES_JSON) -> dict[str, TreeNode]:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return {iso3: TreeNode.from_dict(d) for iso3, d in payload.items()}


# ─────────────────────────────────────────────────────────────────────
# Pretty-print
# ─────────────────────────────────────────────────────────────────────
def print_tree(node: TreeNode, indent: int = 0) -> None:
    pad = "  " * indent
    if node.is_leaf:
        v = node.value
        if v is None:
            print(f"{pad}- {node.name} [{node.leaf_type}]: <missing>")
        elif node.leaf_type == "set":
            preview = ", ".join(v[:5]) + (f"... +{len(v)-5} more" if len(v) > 5 else "")
            print(f"{pad}- {node.name} [set, n={len(v)}]: {{{preview}}}")
        elif node.leaf_type == "numerical":
            print(f"{pad}- {node.name} [num]: {v:,.4g}")
        else:  # single_categorical
            print(f"{pad}- {node.name} [cat]: {v}")
    else:
        suffix = f"  (iso3={node.iso3})" if node.iso3 else ""
        print(f"{pad}+ {node.name}{suffix}")
        for child in node.children:
            print_tree(child, indent + 1)


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────
def main() -> None:
    if not CLEAN_CSV.exists():
        raise FileNotFoundError(
            f"{CLEAN_CSV} not found. Run fetch_all_countries.py first.")

    df = pd.read_csv(CLEAN_CSV)
    print(f"Loaded {len(df)} countries from {CLEAN_CSV}")

    trees = build_all_trees(df)
    print(f"Built {len(trees)} trees\n")

    DATA_DIR.mkdir(exist_ok=True)
    save_trees_json(trees)

    reloaded = load_trees_json()
    assert len(reloaded) == len(trees)
    assert reloaded["FRA"].name == "France"
    print("Round-trip JSON load: OK\n")

    for code in ("FRA", "JPN", "USA", "VAT"):
        if code in trees:
            print("=" * 60)
            print(f"Sample tree: {trees[code].name}")
            print("=" * 60)
            print_tree(trees[code])
            print()

    print("=" * 60)
    print("Missing-leaf summary across all trees")
    print("=" * 60)
    field_missing: dict[str, int] = {}

    def walk(node: TreeNode):
        if node.is_leaf and node.value is None:
            field_missing[node.name] = field_missing.get(node.name, 0) + 1
        for c in node.children:
            walk(c)

    for tree in trees.values():
        walk(tree)

    if not field_missing:
        print("  Every leaf populated.")
    else:
        for k, v in sorted(field_missing.items(), key=lambda x: -x[1]):
            pct = 100 * v / len(trees)
            print(f"  {k:20s} missing in {v:3d}/{len(trees)} ({pct:5.1f}%)")


if __name__ == "__main__":
    main()