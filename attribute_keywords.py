#!/usr/bin/env python3
"""
Forensic attribution of the 2026-03-18 harvest to individual keywords.

Phase 1 matched CONTAINS(LCASE(title), kw). So if a keyword's query had
succeeded on 2026-03-18, records whose title contains that keyword should be
present in raw_harvest.csv.

A record can enter the corpus via any matching keyword, so a nonzero match
count does NOT prove that particular query succeeded. But a record matching
EXACTLY ONE keyword could only have come from that keyword's query. Those are
"uniquely attributable" and a nonzero count is proof the query completed.

Conversely a keyword with zero matches in the corpus contributed nothing:
it either failed or returned an empty set.

Run from the repo root:  python3 attribute_keywords.py
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from harvest_sparql import DOMAIN_QUERIES  # noqa: E402

CSV = "data/harvested/raw_harvest.csv"

df = pd.read_csv(CSV)
titles = df["title"].fillna("").str.lower()

all_kws = [(dom, kw) for dom, kws in DOMAIN_QUERIES.items() for kw in kws]
masks = {kw: titles.str.contains(kw.lower(), regex=False) for _, kw in all_kws}

n_matches = pd.DataFrame(masks).sum(axis=1)   # how many keywords each record matches

print(f"Corpus: {len(df)} records from {CSV}\n")
print(f"{'domain':<22}{'keyword':<28}{'matches':>9}{'unique':>9}  verdict")
print("-" * 84)

domain_totals = {}
for dom, kw in all_kws:
    m = masks[kw]
    total = int(m.sum())
    uniq = int((m & (n_matches == 1)).sum())
    if uniq > 0:
        verdict = "QUERY COMPLETED (proof)"
    elif total > 0:
        verdict = "matched, but subsumed by another keyword"
    else:
        verdict = "contributed nothing (failed or empty)"
    print(f"{dom:<22}{kw:<28}{total:>9}{uniq:>9}  {verdict}")
    d = domain_totals.setdefault(dom, [0, 0])
    d[1] += uniq
print()

print("Records matching NO keyword at all:", int((n_matches == 0).sum()))
print("(should be 0; anything else means titles changed after harvest,")
print(" or records entered by a route other than title matching)\n")

print("Per-domain: keywords with proof of completion")
for dom in DOMAIN_QUERIES:
    proven = [kw for kw in DOMAIN_QUERIES[dom]
              if (masks[kw] & (n_matches == 1)).sum() > 0]
    print(f"  {dom:<22} {len(proven)}/{len(DOMAIN_QUERIES[dom])}  {proven}")
