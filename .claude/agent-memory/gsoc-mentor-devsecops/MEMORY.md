# GSoC Mentor Memory - SWHID POC Project

## Student Project State (as of 2026-02-27)

**POC is MORE complete than CLAUDE.md suggests.** The pipeline IS fully wired in main.py:
- fetch_package -> unpack_file -> find_source -> swhid_generator -> verify_swhid
- CLI via argparse (package + version args)
- SWH archive verification via softwareheritage.org API
- Tested working on `six 1.17.0`

**Known limitation documented in README**: Packages with generated files (.egg-info, compiled C)
compute valid SWHIDs that won't be found in SWH archive because sdist != git tree.
This is actually the core research problem - not a bug, but the central design challenge.

## Key Technical Facts

- swh.model version: 8.4.1 (from dist-info)
- Only sdist (.tar.gz) supported, not wheels
- tmp/ is cleaned on each run (shutil.rmtree at start of unpack_file)
- No tests yet (hypothesis installed but no test files exist)
- No SBOM output, no batch processing, no multi-ecosystem support

## Scope Decision (session 1)

Recommended: LONG (350 hours). Justification documented in scope analysis response.
The sdist-vs-git-tree mismatch problem alone is a 175-hour research problem.
Multi-ecosystem (Crates.io + Maven) adds another 100+ hours of genuine work.

## Ecosystem Priority Order

1. PyPI (already started) - largest Python ecosystem
2. Crates.io (Rust) - strong SWHID culture in Rust community, simpler tarball format)
3. Maven Central (Java) - highest enterprise impact, complex POM structure

## Student Skill Indicators

- Knows Python, requests, tarfile, argparse
- Using swh.model correctly (from_disk.Directory)
- Git-literate (clean commit history)
- Windows development environment (bash via Git Bash)

## Proposal Sections Status

- Not yet drafted (first conversation)

## Critical Design Problem to Highlight in Proposal

The sdist-vs-git-tree gap: PyPI sdists contain generated artifacts
(.egg-info, MANIFEST.in-derived files) that don't exist in the git repo
SWH archives. This means SWHID(sdist) != SWHID(git-tag). The proposal
should frame solving this mapping problem as the core scientific contribution.
See: README.md notes section.
