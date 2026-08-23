#!/usr/bin/env python3
"""
Phase 1 diagnostic — v2.

Records, per keyword, whether the SPARQL query COMPLETED (and with how many
rows) or FAILED (and how). This is the distinction the original run could not
record: harvest_sparql.py line 71 returns None on a Virtuoso execution-limit
rejection without printing, and the caller then prints "+0 new URIs" — the same
output a genuinely empty result produces.

v2 changes: reads DOMAIN_QUERIES, SPARQL_ENDPOINT and HEADERS directly from
src/harvest_sparql.py (config/keywords.json is NOT used by the harvester and
contains a different, later set of domains).

Row counts are RAW — no cross-domain deduplication — so comparing them against
the original per-domain counts also tests whether first-seen dedup in
uri_to_domain suppressed a domain that did in fact return records.

BEFORE RUNNING, confirm harvest_sparql.py guards its entry point:
    tail -3 src/harvest_sparql.py
It must end with something like `if __name__ == "__main__": main()`.
If it calls main() unguarded, importing it would re-run the whole harvest and
overwrite raw_harvest.csv. In that case stop and say so.

Run:
    python3 diagnose_phase1_v2.py 2>&1 | tee logs/phase1_diag_$(date +%FT%H%M%S).log

This is a NEW run against a live catalogue. It documents the endpoint today,
NOT the state on 2026-03-18. Report it with its own date.
"""

import csv
import os
import sys
import time
from datetime import datetime

import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

try:
    from harvest_sparql import DOMAIN_QUERIES, HEADERS, SPARQL_ENDPOINT
except ImportError as exc:
    print(f"ERROR: could not import from src/harvest_sparql.py -> {exc}")
    sys.exit(1)

CLIENT_TIMEOUT_S = 120   # deliberately > the 60s server limit, so a server-side
                         # rejection arrives as a catchable HTTP 500 rather than
                         # being masked by a client-side timeout
LIMIT = 500
SLEEP_BETWEEN = 1.0

QUERY_TEMPLATE = """PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct:  <http://purl.org/dc/terms/>
SELECT DISTINCT ?dataset
WHERE {{
    ?dataset a dcat:Dataset ;
             dct:title ?t .
    FILTER(CONTAINS(LCASE(STR(?t)), "{kw}"))
}}
LIMIT {limit}
"""


def probe(keyword: str) -> dict:
    kw = keyword.lower().replace('"', '\\"')
    q = QUERY_TEMPLATE.format(kw=kw, limit=LIMIT)

    t0 = time.monotonic()
    try:
        r = requests.get(SPARQL_ENDPOINT, params={"query": q},
                         headers=HEADERS, timeout=CLIENT_TIMEOUT_S)
        elapsed = time.monotonic() - t0

        if r.status_code == 200:
            try:
                rows = len(r.json()["results"]["bindings"])
            except Exception as exc:
                return dict(outcome="MALFORMED_200", http_status=200,
                            elapsed_s=round(elapsed, 2), n_rows="",
                            detail=f"{type(exc).__name__}: {exc}")
            return dict(outcome="COMPLETED_EMPTY" if rows == 0 else "COMPLETED",
                        http_status=200, elapsed_s=round(elapsed, 2),
                        n_rows=rows, detail="")

        body = r.text[:300].replace("\n", " ").replace("\r", " ")
        if r.status_code == 500 and "exceeds the limit" in r.text:
            return dict(outcome="EXEC_LIMIT_REJECTED", http_status=500,
                        elapsed_s=round(elapsed, 2), n_rows="", detail=body)
        return dict(outcome="HTTP_ERROR", http_status=r.status_code,
                    elapsed_s=round(elapsed, 2), n_rows="", detail=body)

    except requests.exceptions.Timeout:
        return dict(outcome="CLIENT_TIMEOUT", http_status="",
                    elapsed_s=round(time.monotonic() - t0, 2), n_rows="",
                    detail=f"no response within {CLIENT_TIMEOUT_S}s")
    except Exception as exc:
        return dict(outcome="EXCEPTION", http_status="",
                    elapsed_s=round(time.monotonic() - t0, 2), n_rows="",
                    detail=f"{type(exc).__name__}: {exc}")


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    out_path = f"phase1_diagnostic_{stamp}.csv"
    started = datetime.now().isoformat()
    total_kws = sum(len(v) for v in DOMAIN_QUERIES.values())

    print(f"Phase 1 diagnostic v2 — {started}")
    print(f"Endpoint: {SPARQL_ENDPOINT}")
    print(f"Domains: {len(DOMAIN_QUERIES)}   Keywords: {total_kws}")
    print(f"Client timeout {CLIENT_TIMEOUT_S}s vs server execution limit 60s\n")

    rows_out = []
    for domain, keywords in DOMAIN_QUERIES.items():
        print(f"[{domain}]")
        for kw in keywords:
            res = probe(kw)
            res.update(run_started=started, domain=domain, keyword=kw)
            rows_out.append(res)
            print(f"  {kw!r:<32} {res['outcome']:<20} "
                  f"http={str(res['http_status']) or '-':<5} "
                  f"{res['elapsed_s']:>7.2f}s  rows={res['n_rows']}")
            if res["detail"]:
                print(f"      detail: {res['detail'][:160]}")
            time.sleep(SLEEP_BETWEEN)
        print()

    fields = ["run_started", "domain", "keyword", "outcome",
              "http_status", "elapsed_s", "n_rows", "detail"]
    with open(out_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows_out:
            w.writerow({k: r.get(k, "") for k in fields})

    print("=" * 70)
    print("PER-DOMAIN ROLL-UP (raw counts, no cross-domain deduplication)")
    print("=" * 70)
    for domain in DOMAIN_QUERIES:
        sub = [r for r in rows_out if r["domain"] == domain]
        tally = {}
        for r in sub:
            tally[r["outcome"]] = tally.get(r["outcome"], 0) + 1
        raw = sum(r["n_rows"] for r in sub if isinstance(r["n_rows"], int))
        print(f"  {domain:<22} raw_rows={raw:<6} "
              + " ".join(f"{k}={v}" for k, v in sorted(tally.items())))

    print(f"\nWritten: {out_path}")
    print("\nHOW TO READ THIS:")
    print("  COMPLETED_EMPTY on every keyword of a domain")
    print("      -> 'returned no records' is supportable for THIS run, on")
    print("         this date. It says nothing about 2026-03-18.")
    print("  EXEC_LIMIT_REJECTED on any keyword")
    print("      -> that domain's null cannot be read as absence; add query")
    print("         execution failure as a fourth cause in Section 3.1.")
    print("  COMPLETED with raw_rows > 0 in a domain originally reported empty")
    print("      -> the original zero came from first-seen dedup in")
    print("         uri_to_domain, not from the endpoint. This would also make")
    print("         the 1,477 / 699 split an artefact of iteration order.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
