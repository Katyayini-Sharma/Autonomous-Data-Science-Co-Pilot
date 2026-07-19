# ValueError / TypeError from dtype mismatches

Reference: pandas.to_numeric, pandas.to_datetime docs

- `TypeError: unsupported operand type(s) for +: 'str' and 'int'` — a column
  meant to be numeric is still stored as text. Fix:
  `df['col'] = pd.to_numeric(df['col'], errors='coerce')`.
- `ValueError: could not convert string to float` — same root cause; use
  `errors='coerce'` to turn unparseable values into NaN instead of crashing.
- Date columns stored as strings breaking `.dt` accessor calls. Fix:
  `df['date_col'] = pd.to_datetime(df['date_col'], errors='coerce')`
  before using `.dt.year`, `.dt.month`, etc.

Safe pattern:
```python
df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
df['date'] = pd.to_datetime(df['date'], errors='coerce')
```