# ML Practices — the rules that win Track 2

> These are non-negotiable. Honest, leakage-safe evaluation is the literal grade. When in doubt, choose the more conservative (more honest) option.

## Splitting & validation
- **Time-based split** (train = earlier orders, test = later). Never a random shuffle for temporal data.
- **The test set keeps the natural RTO rate.** Never resample the test set.
- Cross-validate with a **time-aware** or `StratifiedKFold` scheme; report mean ± std.

## Leakage avoidance (our differentiator)
- **Out-of-fold / training-only** encoding for any history/target feature (pincode-RTO rate, buyer prior-RTO). The label must never inform its own feature.
- No feature may use information unavailable at prediction time (i.e., at checkout, pre-dispatch).
- Keep a **leakage guard test** (`tests/`) that fails if a feature correlates suspiciously perfectly with the label.
- Ship a deliberately **leaky model** in the eval to *show* how much AUC inflates — then contrast with the honest one.

## Imbalance & calibration
- Handle imbalance with **class weights / `scale_pos_weight`** first; SMOTE only inside the CV pipeline on the **training fold** (`imblearn.Pipeline`), never before the split.
- **Calibrate** probabilities (isotonic) on held-out data — the cost math requires trustworthy probabilities.

## Metrics (report in this order)
1. State plainly: **accuracy is banned here** and why (99% accuracy = catch zero RTO).
2. **PR-AUC** vs the prevalence baseline (primary). ROC-AUC secondary (note it's optimistic).
3. **precision@k**, recall@fixed-precision.
4. **Calibration curve.**
5. **BMR rupee cost model:** define `c_FN`, `c_FP` with assumptions written down; confusion matrix → ₹.
6. **Cost-vs-threshold curve** → mark **τ\***; report final cost **once** on the untouched test set.
7. **Failure-mode matrix:** where it fails + the ₹ cost. No cherry-picking.

## Models
- Primary: **LightGBM** (calibrated) + **IsolationForest** anomaly layer. XGBoost as a comparison.
- GNN/Transformer (TRUST) and DP-SGD are **stretch demos**, never the core.

## Defense-only
- The system scores/flags/verifies/protects. It never generates fraud, evades detection, or exposes anything offense-capable. Do not add features that could be repurposed offensively.
