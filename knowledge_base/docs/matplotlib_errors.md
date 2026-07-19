# Matplotlib plotting errors in headless / server environments

Reference: Matplotlib usage FAQ

- Blank figures or thread errors happen with an interactive backend on a
  server with no display. This project already sets `matplotlib.use('Agg')`
  globally — generated code must never call `plt.show()`; always save the
  figure with `save_chart()` instead.
- `ValueError: x and y must have same first dimension` — mismatched-length
  arrays; check `len(x) == len(y)` after any filtering/dropna.

Safe pattern:
```python
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(x, y)
save_chart(fig, name="my_chart")
```