# Evaluation — Honest Metrics (the crown jewel)

> This is the writeup that wins Track 2. It mirrors `notebooks/03_evaluation.ipynb`. Stub for now; filled once the model exists. Method rules: [conventions/ml-practices.md](conventions/ml-practices.md).

## What this doc will contain
1. Why accuracy is banned here (with the numbers).
2. PR-AUC vs prevalence baseline (primary); ROC-AUC (secondary, noted optimistic).
3. precision@k / recall@fixed-precision.
4. Calibration (reliability) curve.
5. **BMR cost model:** `c_FN`, `c_FP` definitions + assumptions; confusion matrix in ₹.
6. **Cost-vs-threshold curve** with **τ\*** marked; final cost reported once on the held-out test set.
7. **Leakage-avoidance statement** + a deliberately-leaky model contrast + a naïve "block-all-COD" baseline.
8. **Failure-mode transparency matrix** (where it fails + the ₹ cost).

## Headline numbers (fill in after training)
- PR-AUC: _TBD_ (baseline prevalence: _TBD_)
- Chosen τ\*: _TBD_ · Precision @ τ\*: _TBD_ · Recall @ τ\*: _TBD_
- ₹ saved per 1,000 orders vs block-all-COD baseline: _TBD_
