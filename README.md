# EU Water Dataset Observatory

A reproducible framework for assessing metadata quality across EU water data portals
for policy-relevant management tasks.

## Overview

This repository contains the code, configuration and data underlying the EU Water
Dataset Observatory:

1. **SPARQL harvesting** — automated collection of water dataset metadata from data.europa.eu
2. **Task-specific scoring** — assessment against early warning, compliance reporting and
   cross-border coordination requirements
3. **Impact proxy and priority ranking** — identification of high-return metadata improvements
4. **Country-level analysis** — exploratory comparison against socioeconomic indicators
5. **Harvest audit** — verification of which Phase 1 queries completed and which did not

## Quick start

```bash
pip install -r requirements.txt
python run_full_analysis.py
```

## Repository structure

```
├── src/
│   ├── harvest_sparql.py           # Two-phase SPARQL harvester (water domains)
│   ├── score_real_data.py          # Scoring adapter for harvested records
│   ├── sufficiency_scoring.py      # Task-specific sufficiency calculation
│   ├── sensitivity_analysis.py     # Weight perturbation analysis
│   ├── impact_proxy.py             # Composite impact proxy and priority score
│   ├── validation_analysis.py      # Manual validation analysis
│   ├── extract_country.py          # Five-strategy country attribution cascade
│   ├── fetch_eurostat.py           # Socioeconomic indicator compilation
│   ├── equity_analysis.py          # Country-level correlation analysis
│   ├── equity_analysis_enhanced.py # VIF diagnostics, weighted OLS, LaTeX tables
│   ├── country_detailed_stats.py   # Per-country descriptive statistics
│   ├── dimension_correlations.py   # Dimension-level correlation analysis
│   ├── harvest_climate.py          # SPARQL harvester (climate adaptation domains)
│   ├── score_climate_data.py       # Scoring for the climate harvest
│   ├── impact_climate.py           # Impact proxy for the climate harvest
│   └── sensitivity_climate.py      # Sensitivity analysis for the climate harvest
├── config/
│   ├── weights.json                # Task-specific dimension weights
│   └── keywords.json               # Keyword sets (see note below)
├── data/
│   ├── harvested/
│   │   ├── raw_harvest.csv         # 2,176 water datasets (harvested 18 March 2026)
│   │   ├── harvest_summary.json
│   │   ├── climate_harvest.csv     # 994 climate datasets (harvested 25 March 2026)
│   │   ├── climate_harvest_merged.csv
│   │   └── climate_harvest_summary.json
│   └── outputs_real/               # Scoring, sensitivity, priority and equity outputs
├── visualizations/                 # Plotly figure generators and rendered HTML
├── logs/                           # Per-query outcome logs (August 2026 audit)
├── attribute_keywords.py           # Keyword attribution audit (see Harvest audit)
├── diagnose_phase1_v2.py           # Phase 1 re-execution with outcome logging
├── phase1_diagnostic_*.csv         # Per-query outcomes from the audit re-run
├── run_full_analysis.py            # Pipeline orchestrator
├── package_outputs.py              # Output packaging utility
└── Validation_Checklist.xlsx       # Manual validation of 25 datasets
```

**Note on `config/keywords.json`.** This file is not read by `harvest_sparql.py`. The
keyword sets actually used by the water harvest are defined in the `DOMAIN_QUERIES`
dictionary at the top of `src/harvest_sparql.py`, and those are the definitive record of
what was queried. `config/keywords.json` holds a separate multilingual keyword compilation
retained for reference and for later development.

## Data

The primary analysis covers **2,176 water datasets** harvested via SPARQL from
data.europa.eu on 18 March 2026:

- Floods — 1,477 datasets (67.9%)
- Groundwater — 699 datasets (32.1%)

Domain labels record which keyword set first retrieved a record, not a thematic
classification. See the harvest audit below.

A separate harvest of **994 climate adaptation datasets** (25 March 2026) is included
under `data/harvested/`, together with its scoring pipeline. This extension is not
reported in the manuscript and is provided for completeness and reuse.

## Key findings

- **0% operational readiness** across all three management tasks
- **99.95%** of harvested records carry no licence metadata (2,175 of 2,176)
- **100%** carry no machine-readable format declaration
- **52%** of unique curated dataset URLs in the validation sample were unresolvable
  (48% on the nominal count of 25 records)
- No socioeconomic indicator significantly predicts country-level metadata quality

## Harvest audit

The water harvest queried seven domain keyword sets; two returned records. The original
harvester did not record per-query outcomes, so a query that failed and a query that
returned zero rows produced identical output. Two audit tools were added in August 2026 to
establish which occurred:

- **`attribute_keywords.py`** — offline attribution against the deposited corpus. Because
  Phase 1 matched a substring against the dataset title, a record matching exactly one
  keyword can only have entered through that keyword's query. Six queries are established
  as having completed on 18 March 2026: `flood`, `hochwasser`, `inondation`,
  `groundwater`, `grundwasser` and `aquifer`. No keyword belonging to the five
  non-returning domains produced a uniquely attributable record.

- **`diagnose_phase1_v2.py`** — re-executes all 43 Phase 1 queries with per-query outcome
  logging. In the run of 22 August 2026 (`phase1_diagnostic_20260822T173646.csv`,
  `logs/`), six queries completed, each returning the maximum 500 URIs; 18 returned HTTP
  504 Gateway Time-out; and 19 returned no response within a 120-second client timeout.
  No query returned an empty result set.

Outcomes were not stable between the two runs: `inundación` contributed nothing in March
but completed in August, while `aquifer` completed in March but timed out in August.
Retrieval success therefore depends on endpoint load at the time of querying. The absence
of records for a domain is evidence about query execution, not about catalogue content.

To reproduce:

```bash
python3 attribute_keywords.py        # offline, seconds
python3 diagnose_phase1_v2.py        # live queries, up to ~40 minutes
```

## Reproducibility

The scoring, sensitivity, validation and country-level analyses are fully reproducible
from the deposited snapshot, since they operate on archived data.

The harvest is reproducible in procedure but not in result. data.europa.eu is a live
federated catalogue whose contents and DCAT-AP mappings change over time, and endpoint
responsiveness varies, so re-running the harvesting queries will not return an identical
corpus. This is why the March 2026 snapshot is deposited rather than relying on the
queries alone, and why all reported figures are stated with reference to the harvest date.

## Citation

[Paper citation to be added after publication]

## License

Code in this repository is licensed under the Apache License 2.0 (see `LICENSE`).
Data files under `data/`, together with `Validation_Checklist.xlsx`, are licensed
under Creative Commons Attribution 4.0 International (CC BY 4.0).

Harvested metadata originates from data.europa.eu and remains subject to the terms
of the original publishers.
