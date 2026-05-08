# SWHID Verification Tool

A production-grade utility designed to map Package URLs (PURLs) to verified Software Heritage Identifiers (SWHIDs). This tool ensures cryptographic and structural provenance by establishing a verifiable link between software distributions and their canonical source code archived in the Software Heritage (SWH) ecosystem.

## Key Features

*   **Multi-Ecosystem Support**: Specialized verification strategies for PyPI, Crates.io (Cargo), and Maven Central.
*   **High-Confidence Provenance**:
    *   **PyPI**: Extraction of commit SHAs from Sigstore/PEP 740 attestations via Fulcio certificates.
    *   **Cargo**: Deterministic normalization and restoration of original project state for byte-for-byte matching.
    *   **Maven**: SCM metadata resolution and verification of cleaned source artifacts.
*   **SPDX 3.0 Compliance**: Generation of RDF-compatible JSON-LD manifests using official SPDX models, ensuring compatibility with the broader SBOM ecosystem.
*   **Automated Archival Integration**: Proactive use of the Software Heritage "Save Code Now" API for unarchived or newly identified repositories.
*   **Installation Verification**: Local filesystem scanner to audit installed packages against verified SWHID ground truth.

## Installation

### Prerequisites
- Python 3.9+
- A Software Heritage API Token (optional, but recommended for batch processing)

### Setup
```bash
git clone https://github.com/OdysseasKalaitsidis/SWHID_POC
cd SWHID_POC
python -m venv venv
source venv/bin/activate  # Use .\venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Usage

### Command Line Interface

**Map a single PURL to a verified SWHID:**
```bash
python -m shwid_tool.cli swhid-map pkg:pypi/six@1.17.0
```

**Generate an SPDX 3.0 dataset for multiple PURLs:**
```bash
python -m shwid_tool.cli batch-process input_purls.txt output_report.jsonld
```

**Verify local file integrity:**
```bash
python -m shwid_tool.cli verify-path /path/to/installed/library manifest.jsonld
```

### REST API
The tool exposes a FastAPI-based endpoint for automated integration:
```bash
python -m uvicorn shwid_tool.api:app --host 0.0.0.0 --port 8000
```

## Architecture

The system utilizes a strategy-based pattern to decouple ecosystem-specific logic from the core resolution engine.
*   `VerificationStrategy`: Abstract base class for all ecosystem implementations.
*   `SWHIDManager`: Orchestrator responsible for PURL routing and strategy execution.
*   `BatchProcessor`: Manages large-scale validation datasets with built-in exponential backoff and persistent caching.

## Validation and Standards

Verification findings are exported as SPDX 3.0 documents. Compliance with RDF standards is ensured through SHACL shape validation using the integrated `test_validation.py` suite.

## Documentation

Comprehensive documentation is available for different stakeholders:
- [User Guide](user_guide.md): Detailed CLI and API specifications.
- [Developer Guide](developer_guide.md): Framework for extending the tool to new ecosystems.
- [Maintainer Guide](maintainer_guide.md): Guidance for package authors on enabling high-confidence verifiability.

## Acknowledgments

This project was developed as part of the Google Summer of Code (GSoC) 2026 program, under the mentorship of Software Heritage.
