# SWHID Verification Dataset
 
This directory contains the comprehensive SWHID verification dataset mapping
300 of the most popular packages across 6 ecosystems to their SWHIDs.
 
## Files
 
| File | Description |
| :--- | :--- |
| `swhid_dataset.csv` | Full dataset in CSV format for analysis |
| `full_manifest.jsonld` | SPDX 3.0 JSON-LD manifest with all verified mappings |
| `findings_report.md` | Detailed findings report with per-ecosystem analysis |
| `showcase_manifest.jsonld` | Original 25-package showcase manifest |
 
## Dataset Statistics
 
| Metric | Count | Percentage |
| :--- | ---: | ---: |
| **Total Packages** | 300 | 100% |
| **Verified (High Confidence)** | 191 | 63.7% |
| **Inferred (Medium Confidence)** | 43 | 14.3% |
| **Partial (Low Confidence)** | 51 | 17.0% |
| **Errors/Failed** | 15 | 5.0% |
 
*Generated on 2026-07-16 by `scripts/generate_full_dataset.py`.*
