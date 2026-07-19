# General Python runtime errors

Reference: Python official docs — built-in exceptions

- `IndexError: list index out of range` — check length before indexing.
- `ZeroDivisionError` — guard divisions: `rate = (num / den) if den else 0`.
- `NameError` — a variable was used before assignment.
- `ImportError` / `ModuleNotFoundError` — only `pd`, `np`, and `plt` are
  available in this sandbox; no other imports will work.
- `ImportError: __import__ not found` specifically means the code tried to
  use an import statement inside this sandbox. Never write import
  statements here — pd, np, and plt are already available as pre-defined
  variables; just use them directly without importing.