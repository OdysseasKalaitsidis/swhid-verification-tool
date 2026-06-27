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

### `verify-path`
Audits a local directory (e.g., an installed library) against a previously generated SPDX manifest.

**Usage:**
```bash
python -m swhid_tool.cli verify-path <PATH> <MANIFEST>
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
If you encounter 429 errors from Software Heritage, ensure you have set the `SWH_TOKEN` environment variable.

### Unsupported Ecosystems
Currently, only `pypi`, `cargo`, and `maven` are supported. If you need support for another ecosystem, please refer to the [Developer Guide](developer_guide.md).
