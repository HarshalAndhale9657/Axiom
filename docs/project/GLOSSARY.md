# Glossary

Domain + methodology terms used across the project. Keep answers one line.

## Domain
- **RTO (Return to Origin)** — a dispatched order that fails to reach the buyer (refused/undeliverable/cancelled) and ships back to the merchant; the loss we predict.
- **COD (Cash on Delivery)** — pay-on-delivery; ~60–65% of Indian e-com orders; RTO ~20–40% on COD vs ~2–8% prepaid.
- **Thirdwatch / RTO Shield** — Razorpay's acquired product that scores COD orders pre-dispatch on 200–300+ signals → red/green flag.
- **Bumblebee** — Razorpay's multi-agent merchant-risk system (Planner → parallel Fetchers → Analyzer that runs deterministic rules before the LLM). Our architecture mirrors it.
- **Dynamic Friction** — scaling verification friction to risk (verify/step-up/part-pay) instead of an outright block, to manage false-positive cost.
- **Part-Pay COD** — require a small upfront deposit on risky COD orders ("skin in the game").

## Metrics & methodology
- **Precision** — of the orders we flag, the fraction that truly are RTO/fraud.
- **Recall** — of all true RTO/fraud, the fraction we catch.
- **PR-AUC (AUPRC)** — area under the precision–recall curve; our primary metric (honest under imbalance). Baseline = the positive prevalence, not 0.5.
- **ROC-AUC** — secondary only; optimistic under heavy imbalance.
- **precision@k** — precision within the top-k highest-risk orders (mirrors a fixed-capacity review queue).
- **Calibration** — making predicted probabilities match real frequencies (isotonic); required for the cost math.
- **BMR (Bayes Minimum Risk)** — pick the decision that minimizes expected cost `L(x,i)=Σ_j P(j|x)·C(i,j)` (Elkan). Yields the cost-optimal threshold τ\*.
- **τ\* (tau-star)** — the cost-optimal decision threshold; for fraud it sits far below 0.5 (≈ c_FP/(c_FP+c_FN)).
- **c_FP / c_FN** — cost of a false positive (blocked good order = lost sale + CX) / false negative (missed RTO = logistics loss + tied-up inventory).
- **Leakage** — when information unavailable at prediction time (or the label itself) sneaks into a feature, inflating scores. Our #1 thing to avoid.
- **OOF (out-of-fold) encoding** — computing history/target features using only other folds' data, so the label can't leak into its own feature.
- **SHAP** — per-prediction feature attributions; feeds the grounded LLM reason code.

## Techniques (stretch)
- **HGNN (Heterogeneous Graph Neural Network)** — models users↔devices↔addresses as a graph to catch fraud rings / "guilt by association" (TRUST framework).
- **DP-SGD (Opacus)** — differentially-private training (per-sample gradient clipping + noise); reports privacy budget ε. Privacy-preserving variant, not our core model.
