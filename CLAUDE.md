# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Proof of Concept for computing **Software Heritage Intrinsic Identifiers (SWHIDs)** for Python packages fetched directly from PyPI. The SWHID is a content-based identifier computed from the source directory tree of a package.

## Setup

```bash
python -m venv venv
source venv/Scripts/activate  # Windows (bash)
pip install -r requirements.txt
```

## Running

```bash
python main.py              # prompts for package and version
python main.py six 1.17.0  # or pass directly as positional args
```

Output: the computed SWHID and whether it was found in the Software Heritage archive.

## Architecture

Five steps wired together in `main.py`:

1. **`parser.py:fetch_package(name, version)`** — Queries the PyPI JSON API and returns the sdist tarball download URL.

2. **`calculator.py:unpack_file(file_url)`** — Downloads the tarball in-memory, clears and re-creates `tmp/`, extracts with `tarfile`.

3. **`calculator.py:find_source(extract_path)`** — Unwraps the single top-level directory that tarballs typically contain, so SWHID computation targets actual source files.

4. **`calculator.py:swhid_generator(folder_path)`** — Uses `swh.model.from_disk.Directory` to walk the tree and compute a canonical SWHID.

5. **`main.py:verify_swhid(swhid)`** — Hits the SWH archive REST API (`/api/1/directory/{hash}/`) to check whether the computed SWHID is already known to Software Heritage.

## Reliability note

Works reliably for pure-Python packages (e.g. `six`) where the sdist matches what SWH archived from git. Packages with generated files (`.egg-info`, compiled C extensions, etc.) will produce a valid SWHID but it won't be found in the archive because the sdist tree differs from the git tree.
