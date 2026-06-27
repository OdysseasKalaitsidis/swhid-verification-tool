# Maintainer Guide

This guide is for package maintainers who want to ensure their packages are easily verifiable using SWHIDs.

## Why SWHIDs?
SWHIDs provide a persistent, cryptographic link to the exact source code of a package version. By ensuring your package is SWHID-verifiable, you provide users with high-confidence provenance.

## Best Practices for Verifiability

### 1. Use Sigstore Attestations (PyPI)
For Python packages, use [Sigstore](https://www.sigstore.dev/) to sign your releases. This tool extracts the git commit SHA from the Sigstore certificate to verify that the sdist matches the source repository.

### 2. Include SCM Metadata (Maven/Cargo)
Ensure your package metadata includes a valid `scm` (Maven) or `repository` (Cargo) URL. The tool uses this to locate the source code for comparison.

### 3. Clean Releases
Avoid including generated files (like `.pyc`, compiled binaries, or `.egg-info`) in your source distributions (sdists) unless they are absolutely necessary. The closer the sdist matches the git tree, the higher the verification confidence.

## Verifying Your Own Package
You can verify your package's archival status by running:
```bash
python -m swhid_tool.cli swhid-map pkg:<ecosystem>/<name>@<version>
```
If the tool reports a low confidence score, check if your source distribution contains extra files not present in the git repository.
