# Contributing

Thank you for your interest in contributing to **Windows10-Env-Manager**!

## Reporting Issues

If you find a bug, have a feature request, or see a code improvement opportunity, please [open an issue](https://github.com/abduznik/Windows10-Env-Manager/issues).

### Good First Issues

We maintain a list of **super-easy issues** (1–3 line changes) that are perfect for first-time contributors. These are tagged with `good first issue` and `easy` labels. Each issue includes:

- The exact file to edit
- The current code and what it should be changed to
- A note to run `pytest -v` after making the change

## Development Setup

```bash
git clone https://github.com/abduznik/Windows10-Env-Manager.git
cd Windows10-Env-Manager
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

pip install ruff pytest
```

## Running Tests

```bash
pytest -v        # 129+ tests covering all modules
```

## Linting

We use [ruff](https://docs.astral.sh/ruff/) for fast, zero-config linting:

```bash
ruff check *.py
ruff format --check *.py
```

## Code Review

All changes must be reviewed before merging. Please:

1. Open a pull request with a clear description of the change.
2. Ensure all tests pass (`pytest -v`).
3. Ensure linting is clean (`ruff check *.py`).
4. Reference any related issues.

## Code of Conduct

Be respectful and constructive. This is a small open-source project — everyone is welcome!
