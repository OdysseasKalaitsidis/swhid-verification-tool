# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-27

### Added
- **Multi-Ecosystem Support**: Verification strategies for PyPI (via PEP 740 and project URLs), Cargo/Crates.io (with deterministic normalization), and Maven Central (with SCM metadata validation and source inspections).
- **Provenance Mapping**: Resolution rules from Package URLs (PURLs) to verified Software Heritage Identifiers (SWHIDs).
- **Attestation Parsing**: PyPI strategy extracts commit SHAs from Sigstore/PEP 740 attestations via Fulcio certificates.
- **VCS Normalization**: Restoring Cargo packages to match the original VCS source states by undoing registry modifications.
- **SPDX 3.0 Compliance**: JSON-LD export compliant with official SPDX 3.0 RDF-based models, and test suites with SHACL shape validation.
- **Archival Integration**: Automation for Software Heritage "Save Code Now" trigger functionality.
- **Local Scanner**: Utility to check local installation paths against verified SPDX manifests containing SWHID targets.
- **FastAPI Endpoint**: HTTP API interface for remote resolution in `swhid_tool/api.py`.
- **Command Line Interface**: Rich-powered CLI console interface for single PURL resolution, batch processing, path scanning, and status checking.

### Changed
- Refactored project modules from independent scripts into the structured Python package `swhid_tool`.
- Consolidated tests under the `tests/` directory with multi-strategy mock suites.
