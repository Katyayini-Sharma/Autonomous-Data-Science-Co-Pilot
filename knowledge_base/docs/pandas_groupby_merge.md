# groupby / merge pitfalls

Reference: pandas GroupBy and Merge/Join docs

- `groupby` on a column with NaN values silently drops those rows by default.
- Applying `.mean()` across mixed dtype columns raises `TypeError: agg function
  failed`. Fix by selecting numeric columns first:
  `df.groupby('cat')[numeric_cols].mean()` where
  `numeric_cols = df.select_dtypes(include='number').columns`.
- `merge` producing far more rows than expected means the join key isn't
  unique on one side — check with `df['key'].duplicated().sum()`.

Safe pattern:
```python
numeric_cols = df.select_dtypes(include='number').columns
grouped = df.groupby('category')[numeric_cols].mean()
```