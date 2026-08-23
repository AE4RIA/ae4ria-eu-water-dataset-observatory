#!/usr/bin/env python3
"""
Reproduce Table 8 — Spearman rank correlations between country-level composite
sufficiency and socioeconomic indicators, for countries contributing at least
10 datasets.

Input:  data/outputs_real/equity_merged_data.csv  (20 countries, deposited)
Output: data/outputs_real/table8_country_correlations.csv
        console table matching Table 8 of the manuscript

The manuscript restricts the country-level analysis to countries with n >= 10
datasets, which yields 9 countries covering 1,400 of the 1,430 records for which
a country could be identified (97.9%). Countries below that threshold are
excluded because their means rest on too few records to be informative; the
full 20-country correlations, computed per task rather than on the composite,
are in equity_analysis_results.json.

Spearman rather than Pearson: with 9 countries, distributional assumptions
cannot be verified.

    python3 equity_table8.py
"""

from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / "data/outputs_real/equity_merged_data.csv"
OUT = ROOT / "data/outputs_real/table8_country_correlations.csv"

MIN_DATASETS = 10
OUTCOME = "composite_score_mean"
INDICATORS = [
    ("gdp_per_capita_pps", "GDP per capita (PPS)"),
    ("desi_score", "DESI Score"),
    ("water_exploitation_index", "Water Exploitation Index"),
    ("open_data_maturity", "Open Data Maturity"),
    ("egovernment_usage_pct", "E-Government Usage (%)"),
]


def main() -> int:
    m = pd.read_csv(MERGED)
    sub = m[m["n_datasets"] >= MIN_DATASETS].copy()

    print(f"Source: {MERGED.relative_to(ROOT)}  ({len(m)} countries)")
    print(f"Restricted to n_datasets >= {MIN_DATASETS}: {len(sub)} countries, "
          f"{int(sub['n_datasets'].sum())} datasets\n")

    print(sub[["country_code", "n_datasets", OUTCOME]]
          .sort_values("n_datasets", ascending=False)
          .to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    s = sub[OUTCOME]
    print(f"\nComposite sufficiency: mean {s.mean():.3f}, SD {s.std():.3f}, "
          f"range {s.min():.3f} ({sub.loc[s.idxmin(), 'country_code']}) "
          f"to {s.max():.3f} ({sub.loc[s.idxmax(), 'country_code']})")

    rows = []
    print(f"\nTable 8 — Spearman correlations (n = {len(sub)})")
    print(f"{'Indicator':<30}{'rho':>9}{'p-value':>10}")
    print("-" * 49)
    for col, label in INDICATORS:
        rho, p = spearmanr(sub[col], s)
        rows.append({"indicator": label, "column": col,
                     "spearman_rho": round(rho, 3), "p_value": round(p, 3),
                     "n_countries": len(sub)})
        print(f"{label:<30}{rho:+9.3f}{p:10.3f}")

    sig = [r for r in rows if r["p_value"] < 0.05]
    print("-" * 49)
    print(f"Significant at p < 0.05: {len(sig)}")

    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\nWritten: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
