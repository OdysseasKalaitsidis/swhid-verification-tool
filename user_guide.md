# User Guide

This guide provides detailed information on how to use the SWHID Verification Tool via the CLI and REST API.

## CLI Reference

### `swhid-map`
Resolves a single Package URL (PURL) to a verified SWHID.

**Usage:**
```bash
python -m swhid_tool.cli swhid-map <PURL>
```

**Example:**
```bash
python -m swhid_tool.cli swhid-map pkg:pypi/requests@2.31.0
```

### `batch-process`
Processes a list of PURLs from a text file and exports the results to an SPDX 3.0 JSON-LD manifest.

**Usage:**
```bash
python -m swhid_tool.cli batch-process <INPUT_FILE> <OUTPUT_FILE>
```

**Example:**
```bash
python -m swhid_tool.cli batch-process purls.txt results.jsonld
```

### `audit`
Automatically detects project dependencies across all supported package managers, resolves their SWHIDs from the Software Heritage archive, queries OSV.dev for known vulnerabilities associated with the exact code commits, and audits local installations.

**Usage:**
```bash
python -m swhid_tool.cli audit [PATH] [OPTIONS]
```

**Options:**
* `--trigger-save`: Trigger "Save Code Now" requests for unarchived repositories.
* `--token TEXT`: Software Heritage API Token.
* `--policy TEXT`: Path to a `swhid-policy.toml` file. If not specified, it will look for `swhid-policy.toml` in the current directory.
* `--markdown-summary TEXT`: Path to write a Markdown summary report (perfect for GitHub Actions `$GITHUB_STEP_SUMMARY`).

**Example:**
```bash
python -m swhid_tool.cli audit . --policy swhid-policy.toml --markdown-summary audit-report.md
```

---

## 🛡️ Policy Engine (CI/CD Gatekeeping)

You can define a compliance policy in a `swhid-policy.toml` file. If any dependency violates your policy, the `audit` command will exit with a non-zero code (`1`), automatically breaking your CI/CD pipeline.

### Example `swhid-policy.toml`

```toml
[policy]
# Fail the build if any local file/directory has a cryptographic mismatch against the archive
fail_on_mismatch = true

# The minimum confidence level required for dependencies
# Options: "Verified" (3), "Inferred" (2), "Partial" (1), "Any" (0)
minimum_confidence_level = "Inferred"

# Fail the build if OSV.dev finds any known vulnerability associated with the code
fail_on_vulnerability = false

# Allowlist for private, internal, or specific packages to ignore
allowlist = [
  "pkg:npm/@our-company/*",
  "pkg:pypi/six@1.17.0"
]

# Vulnerability IDs to ignore
ignored_vulnerabilities = [
  "GHSA-xxxx-xxxx-xxxx"
]
```

---

## REST API Reference

The tool includes a FastAPI-based server for integration into automated workflows.

### Start the Server
```bash
python -m uvicorn swhid_tool.api:app --port 8000
```

### Endpoints

#### `POST /resolve`
Resolves a PURL to a SWHID.

**Request:**
```json
{
  "purl": "pkg:pypi/six@1.17.0"
}
```

**Response:**
```json
{
  "purl": "pkg:pypi/six@1.17.0",
  "swhid": "swh:1:dir:...",
  "status": "Verified",
  "confidence": "High"
}
```

---

## Troubleshooting

### Rate Limiting
If you encounter 429 errors from Software Heritage, ensure you have set the `SWH_TOKEN` or `SWH_AUTH_TOKEN` environment variable.

### Supported Ecosystems
The tool supports 6 major ecosystems:
1. **PyPI** (`pkg:pypi/`)
2. **npm** (`pkg:npm/`)
3. **Cargo** (`pkg:cargo/`)
4. **Go Modules** (`pkg:golang/`)
5. **Maven Central** (`pkg:maven/`)
6. **NuGet** (`pkg:nuget/`)

