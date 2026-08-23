# EU Water Dataset Observatory

A reproducible framework for assessing metadata quality across EU water data portals for policy-relevant management tasks.

## Overview

This repository contains tools for:
1. **SPARQL Harvesting** - Automated collection of water dataset metadata from data.europa.eu
2. **Task-Specific Scoring** - Assessment against Early Warning, Compliance Reporting, and Cross-Border coordination requirements
3. **Priority Ranking** - Identification of high-impact metadata improvements

## Quick Start

```bash
# Install dependencies
pip install pandas requests SPARQLWrapper

# Run full pipeline
python run_full_analysis.py
```

## Repository Structure

```
├── src/
│   ├── harvest_sparql.py      # SPARQL harvester for data.europa.eu
│   ├── score_real_data.py     # Score harvested datasets
│   ├── sufficiency_scoring.py # Task-specific sufficiency calculations
│   ├── sensitivity_analysis.py # Weight perturbation analysis
│   ├── impact_proxy.py        # Dataset importance proxy
│   └── validation_analysis.py # Manual validation analysis
├── config/
│   ├── weights.json           # Task-specific dimension weights
│   └── keywords.json          # Domain-specific search keywords
├── data/
│   ├── harvested/             # Raw SPARQL harvest results
│   │   ├── raw_harvest.csv    # 2,176 real EU water datasets
│   │   └── harvest_summary.json
│   └── outputs_real/          # Scoring outputs
│       ├── sufficiency_scores.csv
│       ├── sensitivity_summary.csv
│       ├── priority_fixes.csv
│       └── analysis_summary_real.json
├── visualizations/
│   └── create_visualizations.py
├── run_full_analysis.py       # Main pipeline orchestrator
└── Validation_Checklist.xlsx  # Manual validation of 25 datasets
```

## Data

The analysis is based on **2,176 real EU water datasets** harvested via SPARQL from data.europa.eu, covering:
- Floods (1,477 datasets, 67.9%)
- Groundwater (699 datasets, 32.1%)

## Key Findings

- **0% operational readiness** across all three management tasks
- **99.95%** of datasets lack explicit license metadata (2,175 of 2,176)
- **100%** lack machine-readable format declarations
- **52%** of unique curated dataset URLs are broken (48% on the nominal count of 25 records)

## Citation

[Paper citation to be added after publication]

## License

[License to be specified]

## License

Code in this repository is licensed under the Apache License 2.0 (see `LICENSE`).
Data files under `data/`, together with `Validation_Checklist.xlsx`, are licensed
under Creative Commons Attribution 4.0 International (CC BY 4.0).

Harvested metadata originates from data.europa.eu and remains subject to the terms
of the original publishers.
