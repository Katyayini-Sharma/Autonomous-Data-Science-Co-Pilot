# KeyError: column not found

Reference: pandas.DataFrame indexing docs (pandas.pydata.org/docs/user_guide/indexing.html)

A `KeyError` when accessing `df['col']` or `df.col` means the column name does
not exist exactly as written. Common causes and fixes:

- Case mismatch: `df['Name']` vs actual column `'name'`. Fix by checking
  `df.columns.tolist()` first, or normalize with `df.columns = df.columns.str.strip().str.lower()`.
- Leading/trailing whitespace in column names from messy CSV headers.
  Fix: `df.columns = df.columns.str.strip()`.
- Using a column name that was dropped during cleaning. Re-check the
  available columns with `df.columns`.

Safe pattern:
```python
if 'target_col' in df.columns:
    value = df['target_col']
else:
    raise KeyError(f"'target_col' not in columns: {df.columns.tolist()}")
```