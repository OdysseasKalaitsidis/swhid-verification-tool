# Developer Guide

This guide is intended for developers who wish to contribute to the SWHID Verification Tool or extend its functionality.

## Core Architecture

The tool follows a **Strategy Pattern** to handle different package ecosystems.

### `SWHIDManager`
The central orchestrator that routes PURLs to the appropriate `VerificationStrategy`.

### `VerificationStrategy`
An abstract base class defined in `shwid_tool/strategies/base.py`. Every ecosystem (PyPI, Cargo, etc.) implements this class to provide:
1. **Source Discovery**: Finding the canonical source repository or sdist.
2. **Normalization**: Cleaning the source to match SWH's archival format.
3. **Verification**: Comparing computed SWHIDs with archived ones.

## Extending the Tool

To add support for a new ecosystem (e.g., `npm`):

1. Create a new strategy class in `shwid_tool/strategies/npm_strategy.py`.
2. Inherit from `VerificationStrategy`.
3. Register the new strategy in `SWHIDManager.__init__` within `shwid_tool/manager.py`.

## Testing

Run the test suite using `pytest`:

```bash
pytest tests/
```

Individual test modules:
- `test_shwid.py`: Core SWHID computation logic.
- `test_spdx3_model.py`: SPDX 3.0 serialization.
- `test_validation.py`: SHACL validation of generated manifests.

## Development Environment Setup

1. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov
   ```
2. Set up a local cache directory to speed up repeated resolutions.
