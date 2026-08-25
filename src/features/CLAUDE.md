# Features — leakage is the enemy here

This subsystem is where our whole "honest metrics" thesis is won or lost. Before writing any feature:

- **No future information.** A feature may only use data available at checkout / pre-dispatch.
- **History features are out-of-fold.** `pincode_rto_rate`, `buyer_prior_rto_rate`, etc. must be computed from **training-fold / strictly-earlier rows only** — never from the row's own label or the full dataset.
- **Transforms are pure functions** of a single order (+ precomputed lookup tables). Same code path offline and online.
- **Every feature has a docstring** stating: what it is, its unit, and that it's available at prediction time.
- If a feature makes the model suddenly "too good," suspect leakage first. Add/extend the leakage-guard test in `tests/`.

See [../../docs/conventions/ml-practices.md](../../docs/conventions/ml-practices.md).
