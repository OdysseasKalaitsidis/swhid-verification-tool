# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import os
import json
import sys
from swhid_tool.manager import SWHIDManager
from swhid_tool.batch_processor import BatchProcessor
from swhid_tool.spdx_exporter import export_to_spdx3

# Top popular packages across the 5 supported ecosystems
SHOWCASE_PURLS = [
    # PyPI
    "pkg:pypi/six@1.17.0",
    "pkg:pypi/requests@2.31.0",
    "pkg:pypi/urllib3@2.0.7",
    "pkg:pypi/certifi@2024.2.2",
    "pkg:pypi/idna@3.6",
    
    # npm
    "pkg:npm/lodash@4.17.21",
    "pkg:npm/react@18.2.0",
    "pkg:npm/express@4.18.2",
    "pkg:npm/uuid@9.0.1",
    "pkg:npm/chalk@4.1.2",
    
    # Cargo
    "pkg:cargo/serde@1.0.203",
    "pkg:cargo/libc@0.2.155",
    "pkg:cargo/tokio@1.38.0",
    "pkg:cargo/rand@0.8.5",
    "pkg:cargo/regex@1.10.5",
    
    # Go
    "pkg:golang/github.com/gin-gonic/gin@v1.9.0",
    "pkg:golang/github.com/sirupsen/logrus@v1.9.3",
    "pkg:golang/golang.org/x/text@v0.14.0",
    "pkg:golang/github.com/spf13/cobra@v1.8.0",
    "pkg:golang/github.com/stretchr/testify@v1.9.0",
    
    # Maven
    "pkg:maven/junit/junit@4.13.2",
    "pkg:maven/org.slf4j/slf4j-api@2.0.13",
    "pkg:maven/org.apache.commons/commons-lang3@3.14.0",
    "pkg:maven/com.fasterxml.jackson.core/jackson-databind@2.17.0",
    "pkg:maven/org.mockito/mockito-core@5.11.0"
]

def main():
    print("🚀 Starting SWHID Showcase Dataset Generation...")
    print(f"Targeting {len(SHOWCASE_PURLS)} popular packages across 5 ecosystems.")
    
    # Set up manager and batch processor
    manager = SWHIDManager()
    processor = BatchProcessor(manager)
    
    # Process PURLs
    findings = processor.process_purls(SHOWCASE_PURLS)
    
    # Export to SPDX 3.0 JSON-LD
    output_dir = "dataset"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "showcase_manifest.jsonld")
    
    export_to_spdx3(findings, output_file)
    print(f"\n✅ SPDX 3.0 Manifest successfully saved to: {output_file}")
    
    # Compute Statistics
    total = len(findings)
    verified = 0
    inferred = 0
    partial = 0
    errors = 0
    save_code_now_triggered = 0
    
    for f in findings:
        status = f.get("status")
        if status == "Verified":
            verified += 1
        elif status == "Inferred":
            inferred += 1
        elif status == "Partial":
            partial += 1
        else:
            errors += 1
            
        # Check if Save Code Now was triggered
        for strat in f.get("strategies_tried", []):
            res = strat.get("result", {})
            if "triggered Save Code Now" in res.get("reason", "") or "save_code_now" in res:
                save_code_now_triggered += 1
                break
                
    print("\n📊 Verification Statistics:")
    print(f"  - Total Packages Processed: {total}")
    print(f"  - Verified (High Confidence): {verified} ({verified/total*100:.1f}%)")
    print(f"  - Inferred (Medium Confidence): {inferred} ({inferred/total*100:.1f}%)")
    print(f"  - Partial (Low Confidence): {partial} ({partial/total*100:.1f}%)")
    print(f"  - Errors/Failed: {errors} ({errors/total*100:.1f}%)")
    print(f"  - Software Heritage 'Save Code Now' Triggers: {save_code_now_triggered}")
    
    # Write stats to a markdown file in the dataset folder for easy presentation
    stats_file = os.path.join(output_dir, "README.md")
    with open(stats_file, "w") as f:
        f.write(f"""# SWHID Showcase Dataset

This directory contains a pre-generated SPDX 3.0 verification dataset mapping popular packages to their Software Heritage Identifiers (SWHIDs).

## Dataset Statistics

| Metric | Count | Percentage |
| :--- | :--- | :--- |
| **Total Packages** | {total} | 100% |
| **Verified (High Confidence)** | {verified} | {verified/total*100:.1f}% |
| **Inferred (Medium Confidence)** | {inferred} | {inferred/total*100:.1f}% |
| **Partial (Low Confidence)** | {partial} | {partial/total*100:.1f}% |
| **Errors/Failed** | {errors} | {errors/total*100:.1f}% |
| **SWH 'Save Code Now' Triggers** | {save_code_now_triggered} | - |

*Generated automatically by `scripts/generate_showcase_dataset.py`.*
""")
    print(f"✅ Dataset report saved to: {stats_file}")

if __name__ == "__main__":
    main()
