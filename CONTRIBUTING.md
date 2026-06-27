# Contributing to SWHID Verification Tool

Thank you for your interest in contributing to the SWHID Verification Tool! We welcome all contributions, including bug reports, documentation updates, feature requests, and code contributions.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs or Feature Requests

Before opening a new issue, please search the existing issues to see if it has already been reported. When reporting a bug, please include:
- A clear description of the issue.
- Steps to reproduce the bug.
- The expected behavior vs. actual behavior.
- Relevant log output (with log level set to DEBUG).
- Your Python version and operating system.

### Developing and Submitting Changes

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/swhid-verification-tool.git
   cd swhid-verification-tool
   ```
3. **Set up a development environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -e ".[dev]"
   ```
4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
5. **Implement your changes** and add unit tests under `tests/` for any new logic.
6. **Ensure all tests pass and code is clean**:
   ```bash
   # Run linters and type checkers
   ruff check .
   mypy swhid_tool/
   
   # Run tests
   pytest tests/
   ```
7. **Commit your changes**. Please write clear, concise commit messages.
8. **Push to your fork** and **open a Pull Request** against the `main` branch.

## Code Style and Standards

- We use [Ruff](https://github.com/astral-sh/ruff) for linting and code formatting.
- We use [Mypy](https://github.com/python/mypy) for strict static type checking. All public APIs should include type annotations.
- Keep documentation up-to-date. If you add a new strategy or change CLI options, update the user guides and developer guides.
- We follow SPDX and REUSE standards for license headers in source files:
  ```python
  # SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
  # SPDX-License-Identifier: MIT
  ```
