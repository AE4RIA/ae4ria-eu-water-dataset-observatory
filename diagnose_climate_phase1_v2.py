#!/usr/bin/env python3
"""
Climate harvest Phase 1 diagnostic — v2.

Replicates the exact three-strategy cascade of phase1_get_uris_combined() in
src/harvest_climate.py, but records the outcome of EVERY query instead of
treating a None return as "nothing found".

WHY THIS IS NEEDED
------------------
phase1_get_uris_combined() cannot distinguish failure from emptiness at any of
its three levels:

  Strategy 1  combined OR query over all keywords      (timeout=50)
              -> on None, falls through to Strategy 2
  Strategy 2  OR queries over batches of 5 keywords    (timeout=50)
              -> on None, falls through to Strategy 3 for that batch
  Strategy 3  one OR query per individual keyword      (timeout=45)
              -> on None, prints "timed out / skipped" and continues

If every strategy fails the function returns an empty list, which main() then
records as `new == 0` and appends the domain to zero_result_domains — the same
state a genuinely empty catalogue would produce. The harvester then prints
"This is a scientific finding, not a pipeline failure", a claim its own
instrumentation cannot support.

Both timeouts (50 s, 45 s) sit BELOW the endpoint's 60 s server-side limit, so
the client aborts before the server can return a catchable status. An OR query
combining five or more CONTAINS conditions is substantially heavier than the
single-substring queries used by the water harvest, which were themselves
measured at 24-42 s when they succeeded.

This script uses a 120 s client timeout throughout, so server-side rejections
arrive as HTTP statuses rather than as client timeouts.

USAGE
  python3 diagnose_climate_phase1_v2.py                       # all domains
  python3 diagnose_climate_phase1_v2.py --domain nature_based_solutions
  python3 diagnose_climate_phase1_v2.py --domain nature_based_solutions --fallback

  Log the console:
  python3 diagnose_climate_phase1_v2.py 2>&1 | tee logs/climate_diag_$(date +%FT%H%M%S).log

This is a NEW run against a live catalogue. It documents the endpoint today, not
the state on 25 March 2026. Report it with its own date.
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

import requests

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from harvest_climate import HEADERS, SPARQL_ENDPOINT, _build_or_filter_query
except ImportError as exc:
    print(f"ERROR: cannot import from src/harvest_climate.py -> {exc}")
    sys.exit(1)

KEYWORDS_PATH = os.path.join(REPO, "config", "climate_keywords.json")
CLIENT_TIMEOUT_S = 120
LIMIT = 500
SLEEP = 0.4

# Copied verbatim from the FALLBACK_KEYWORDS dict inside main().
FALLBACK_KEYWORDS = {
    "drought_early_warning": [
        "drought monitoring", "hydrological drought", "water shortage",
        "dry spell", "drought risk", "droughts", "streamflow drought",
    ],
    "climate_infrastructure": [
        "climate adaptation", "future climate", "climate change",
        "climate projections", "climate impacts", "infrastructure climate",
    ],
    "nature_based_solutions": [
        "wetland", "natural flood", "ecosystem restoration",
        "riparian", "floodplain", "ecological restoration",
    ],
}


def probe(keywords, label):
    """Issue one OR-FILTER query and classify the outcome explicitly."""
    q = _build_or_filter_query(keywords, limit=LIMIT)
    t0 = time.monotonic()
    try:
        r = requests.get(SPARQL_ENDPOINT, params={"query": q},
                         headers=HEADERS, timeout=CLIENT_TIMEOUT_S)
        el = time.monotonic() - t0
        if r.status_code == 200:
            try:
                rows = len(r.json()["results"]["bindings"])
            except Exception as exc:
                return dict(outcome="MALFORMED_200", http_status=200,
                            elapsed_s=round(el, 2), n_rows="",
                            detail=f"{type(exc).__name__}: {exc}")
            return dict(outcome="COMPLETED_EMPTY" if rows == 0 else "COMPLETED",
                        http_status=200, elapsed_s=round(el, 2),
                        n_rows=rows, detail="")
        body = r.text[:300].replace("\n", " ").replace("\r", " ")
        if r.status_code == 500 and "exceeds the limit" in r.text:
            return dict(outcome="EXEC_LIMIT_REJECTED", http_status=500,
                        elapsed_s=round(el, 2), n_rows="", detail=body)
        return dict(outcome="HTTP_ERROR", http_status=r.status_code,
                    elapsed_s=round(el, 2), n_rows="", detail=body)
    except requests.exceptions.Timeout:
        return dict(outcome="CLIENT_TIMEOUT", http_status="",
                    elapsed_s=round(time.monotonic() - t0, 2), n_rows="",
                    detail=f"no response within {CLIENT_TIMEOUT_S}s")
    except Exception as exc:
        return dict(outcome="EXCEPTION", http_status="",
                    elapsed_s=round(time.monotonic() - t0, 2), n_rows="",
                    detail=f"{type(exc).__name__}: {exc}")


def cascade(domain, keywords, kind, rows_out, started):
    """Run all three strategies, recording every query — no early return."""
    def record(strategy, label, kws):
        res = probe(kws, label)
        res.update(run_started=started, domain=domain, keyword_set=kind,
                   strategy=strategy, label=label, n_keywords=len(kws))
        rows_out.append(res)
        print(f"    {strategy:<12} {label:<34} {res['outcome']:<20} "
              f"http={str(res['http_status']) or '-':<5} "
              f"{res['elapsed_s']:>7.2f}s  rows={res['n_rows']}")
        if res["detail"]:
            print(f"        detail: {res['detail'][:150]}")
        time.sleep(SLEEP)
        return res

    print(f"  [{domain}] {kind}: {len(keywords)} keywords")
    record("combined", f"all {len(keywords)} keywords", keywords)

    for i in range(0, len(keywords), 5):
        batch = keywords[i:i + 5]
        record("batch", f"[{i}:{i+5}] {len(batch)} kws", batch)

    for kw in keywords:
        record("individual", repr(kw), [kw])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default=None)
    ap.add_argument("--fallback", action="store_true",
                    help="also probe the FALLBACK_KEYWORDS for each domain")
    args = ap.parse_args()

    with open(KEYWORDS_PATH) as fh:
        domain_queries = json.load(fh)

    domains = [args.domain] if args.domain else list(domain_queries)
    for d in domains:
        if d not in domain_queries:
            print(f"ERROR: '{d}' not in {KEYWORDS_PATH}. "
                  f"Available: {list(domain_queries)}")
            return 1

    started = datetime.now().isoformat()
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    out_path = os.path.join(REPO, f"climate_phase1_diagnostic_{stamp}.csv")

    print(f"Climate Phase 1 diagnostic v2 — {started}")
    print(f"Endpoint: {SPARQL_ENDPOINT}")
    print(f"Client timeout {CLIENT_TIMEOUT_S}s "
          f"(harvest_climate.py used 50s / 45s, both below the 60s server limit)")
    print(f"Domains: {domains}\n")

    rows_out = []
    for d in domains:
        cascade(d, domain_queries[d], "primary", rows_out, started)
        if args.fallback and d in FALLBACK_KEYWORDS:
            cascade(d, FALLBACK_KEYWORDS[d], "fallback", rows_out, started)
        print()

    fields = ["run_started", "domain", "keyword_set", "strategy", "label",
              "n_keywords", "outcome", "http_status", "elapsed_s",
              "n_rows", "detail"]
    with open(out_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows_out:
            w.writerow({k: r.get(k, "") for k in fields})

    print("=" * 78)
    print("ROLL-UP BY DOMAIN AND KEYWORD SET")
    print("=" * 78)
    for d in domains:
        for kind in ("primary", "fallback"):
            sub = [r for r in rows_out
                   if r["domain"] == d and r["keyword_set"] == kind]
            if not sub:
                continue
            tally = {}
            for r in sub:
                tally[r["outcome"]] = tally.get(r["outcome"], 0) + 1
            completed = [r for r in sub if r["outcome"] == "COMPLETED"]
            empty = [r for r in sub if r["outcome"] == "COMPLETED_EMPTY"]
            print(f"  {d} / {kind}: {len(sub)} queries")
            print(f"    " + "  ".join(f"{k}={v}" for k, v in sorted(tally.items())))
            print(f"    queries returning rows: {len(completed)}   "
                  f"confirmed empty: {len(empty)}   "
                  f"max rows seen: {max([r['n_rows'] for r in completed], default=0)}")

    print(f"\nWritten: {out_path}")
    print("\nHOW TO READ THIS")
    print("  Every query COMPLETED_EMPTY across primary and fallback")
    print("     -> the domain genuinely returns nothing for these terms, on this")
    print("        date. The CLIMATE_ADAPTATION_REPORT.md wording can stand, but")
    print("        must be scoped to this run rather than stated as structural.")
    print("  Any HTTP_ERROR / CLIENT_TIMEOUT / EXEC_LIMIT_REJECTED")
    print("     -> the null is a query-execution outcome, not an absence. The")
    print("        'structural invisibility' claim must be withdrawn, exactly as")
    print("        the five water domains' 'returned zero results' was.")
    print("  Any COMPLETED with rows > 0")
    print("     -> the datasets exist and were retrievable; the March run simply")
    print("        failed to reach them within its 50s/45s timeouts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
