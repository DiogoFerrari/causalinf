---
globs: causalinf/**/*.py
---

# Python rules

## Package structure
- `causalinf/` — main package source
- `causalinf/data` — folder with the data used by the package
- `tests/` — pytest tests (mirror the package structure)

## Conventions
- Do not use hints on function signatures
- Docstrings on all public functions and classes using NumPy style
- No wildcard imports; If you find any, correct it with the explicit import

## Testing
- pytest for all tests
- Each module in the package should have a corresponding test file
- Run tests with `pytest` from project root only when asked

## Dependencies
- Runtime deps in `pyproject.toml`
- Do not add new dependencies without asking first
