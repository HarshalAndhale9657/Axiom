"""Does the gradient-boosted model actually earn its keep?

Every fraud deck shows a model beating "do nothing". That is not the question a risk team
asks. The question is whether the ML beats **the thing you would have shipped anyway** —
a hand-written scorecard a domain expert could write in an afternoon, or a logistic
regression on the same features. If it does not, the honest answer is to ship the simpler
thing, and saying so is worth more than a tenth of a point of PR-AUC.

So this module runs the full ladder on identical terms:

1. **prevalence** — predict the base rate for everyone (the PR-curve no-skill floor).
2. **rules-only** — a transparent points scorecard over checkout-observable fields, of
   the kind a risk analyst writes from domain knowledge alone.
3. **logistic regression** — the standard linear benchmark on the same feature matrix.
4. **LightGBM (Axiom)** — the shipped model.

Fairness rules, applied to every contender without exception:

* identical features, identical chronological splits;
* **isotonic calibration fitted on validation** (a raw scorecard is not a probability, and
  comparing rupee cost without calibrating first would rig the contest);
* the rupee operating threshold is fitted **on validation** for each contender separately,
  then frozen before the test split is touched;
* the differences are given **paired bootstrap** intervals — same resampled orders for
  both contenders — because the sampling noise is shared and an unpaired interval would
  overstate the uncertainty on the gap.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from src.features.build_features import FeatureBundle
from src.model.evaluation import CostModel, total_cost
from src.model.threshold import select_tau_star

# A domain-knowledge scorecard: (feature, weight) in log-odds, plus an intercept. Written
# from the published drivers of Indian COD RTO — payment mode dominates, then address
# quality, then buyer newness — and deliberately NOT tuned against the data.
RULE_WEIGHTS: dict[str, float] = {
    "is_cod": 1.60,
    "address_completeness": -1.40,
    "is_first_time_buyer": 0.55,
    "phone_verified": -0.45,
    "city_tier": 0.30,
    "is_serviceable": -1.20,
}
RULE_INTERCEPT = -2.20
# distance is in km and order_value in rupees; scaled so a weight stays interpretable.
RULE_DISTANCE_PER_1000KM = 0.35
RULE_VALUE_PER_1000RS = 0.10


def rules_only_raw(X: pd.DataFrame) -> np.ndarray:
    """Hand-written expert scorecard -> raw log-odds. No fitting, no label ever seen."""
    z = np.full(len(X), RULE_INTERCEPT, dtype=float)
    for col, w in RULE_WEIGHTS.items():
        if col in X.columns:
            z += w * pd.to_numeric(X[col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    if "distance_km" in X.columns:
        z += RULE_DISTANCE_PER_1000KM * X["distance_km"].to_numpy(dtype=float) / 1000.0
    if "order_value_log" in X.columns:
        z += RULE_VALUE_PER_1000RS * np.expm1(X["order_value_log"].to_numpy(dtype=float)) / 1000.0
    return z


def _numeric_matrix(X: pd.DataFrame) -> pd.DataFrame:
    """Numeric view of the feature matrix (categoricals -> integer codes) for linear models."""
    out = X.copy()
    for col in out.columns:
        if str(out[col].dtype) in ("category", "object"):
            out[col] = out[col].astype("category").cat.codes
    return out.apply(pd.to_numeric, errors="coerce").fillna(0.0)


@dataclass
class Contender:
    """One row of the ladder: a calibrated scorer plus its frozen operating threshold."""

    name: str
    proba_val: np.ndarray
    proba_test: np.ndarray
    tau: float


def _calibrate(raw_val: np.ndarray, y_val: np.ndarray,
               raw_test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Isotonic map fitted on validation, applied to both splits."""
    iso = IsotonicRegression(out_of_bounds="clip").fit(raw_val, np.asarray(y_val, dtype=float))
    return iso.predict(raw_val), iso.predict(raw_test)


def build_contenders(bundle: FeatureBundle, champion=None,
                     cm: CostModel | None = None, seed: int = 42) -> list[Contender]:
    """Fit every contender on train, calibrate + choose thresholds on val, score test once."""
    cm = cm or CostModel()
    X_tr, y_tr = bundle.split("train")
    X_val, y_val = bundle.split("val")
    X_te, _ = bundle.split("test")
    yv, vv = y_val.to_numpy(), bundle.frame.loc[X_val.index, "order_value"].to_numpy()

    contenders: list[Contender] = []

    def add(name: str, raw_val: np.ndarray, raw_test: np.ndarray) -> None:
        pv, pt = _calibrate(raw_val, yv, raw_test)
        contenders.append(Contender(name, pv, pt, select_tau_star(yv, pv, vv, cm)))

    prior = float(np.mean(y_tr))
    contenders.append(Contender("prevalence (no skill)",
                                np.full(len(X_val), prior), np.full(len(X_te), prior),
                                select_tau_star(yv, np.full(len(X_val), prior), vv, cm)))

    add("rules-only scorecard", rules_only_raw(X_val), rules_only_raw(X_te))

    logit = LogisticRegression(max_iter=2000, C=1.0, random_state=seed)
    num_tr, num_val, num_te = (_numeric_matrix(x) for x in (X_tr, X_val, X_te))
    mu, sd = num_tr.mean(), num_tr.std().replace(0.0, 1.0)
    logit.fit((num_tr - mu) / sd, y_tr)
    add("logistic regression",
        logit.decision_function((num_val - mu) / sd),
        logit.decision_function((num_te - mu) / sd))

    if champion is not None:
        # Already calibrated on val by src.model.train; do not re-calibrate.
        pv, pt = champion.predict_proba(X_val), champion.predict_proba(X_te)
        contenders.append(Contender("LightGBM (Axiom)", pv, pt,
                                    select_tau_star(yv, pv, vv, cm)))
    return contenders


def compare(bundle: FeatureBundle, champion=None, cm: CostModel | None = None,
            n_boot: int = 500, seed: int = 42) -> pd.DataFrame:
    """The ablation table: every contender scored once on the untouched test split."""
    cm = cm or CostModel()
    contenders = build_contenders(bundle, champion, cm, seed)
    test = bundle.frame[bundle.frame["split"] == "test"]
    y = test["is_rto"].to_numpy().astype(int)
    value = test["order_value"].to_numpy(dtype=float)
    is_cod = test["is_cod"].to_numpy().astype(bool)
    n = len(y)
    block_all = total_cost(is_cod, y, value, cm)

    rows = []
    for c in contenders:
        p = c.proba_test
        constant = float(np.ptp(p)) < 1e-12          # AUCs are undefined for a flat score
        cost = total_cost(p >= c.tau, y, value, cm)
        rows.append({
            "model": c.name,
            "tau_val_fitted": round(c.tau, 4),
            "pr_auc": float("nan") if constant else float(average_precision_score(y, p)),
            "roc_auc": float("nan") if constant else float(roc_auc_score(y, p)),
            "brier": float(brier_score_loss(y, np.clip(p, 0, 1))),
            "cost_per_1k": cost / n * 1000.0,
            "saving_per_1k_vs_block_all_cod": (block_all - cost) / n * 1000.0,
        })
    table = pd.DataFrame(rows)

    if n_boot and champion is not None and len(contenders) > 1:
        table = table.merge(_paired_gaps(contenders, y, value, cm, n_boot, seed),
                            on="model", how="left")
    return table


def _paired_gaps(contenders: list[Contender], y: np.ndarray, value: np.ndarray,
                 cm: CostModel, n_boot: int, seed: int) -> pd.DataFrame:
    """Paired bootstrap CI for (champion - contender) on PR-AUC and on rupee cost.

    The champion is the last contender. An interval that straddles zero means we have not
    shown the champion is better -- and we say so in the table rather than in a footnote.
    """
    rng = np.random.default_rng(seed)
    champ = contenders[-1]
    n = len(y)
    gaps: dict[str, dict[str, list[float]]] = {
        c.name: {"pr_auc": [], "cost_per_1k": []} for c in contenders[:-1]}

    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yb, vb = y[idx], value[idx]
        if yb.sum() == 0 or yb.sum() == len(yb):
            continue
        champ_p = champ.proba_test[idx]
        champ_ap = average_precision_score(yb, champ_p)
        champ_cost = total_cost(champ_p >= champ.tau, yb, vb, cm) / len(yb) * 1000.0
        for c in contenders[:-1]:
            p = c.proba_test[idx]
            ap = float("nan") if float(np.ptp(p)) < 1e-12 else average_precision_score(yb, p)
            gaps[c.name]["pr_auc"].append(champ_ap - ap)
            gaps[c.name]["cost_per_1k"].append(
                total_cost(p >= c.tau, yb, vb, cm) / len(yb) * 1000.0 - champ_cost)

    rows = []
    for name, d in gaps.items():
        row = {"model": name}
        for metric, vals in d.items():
            arr = np.asarray(vals, dtype=float)
            arr = arr[np.isfinite(arr)]
            lo, hi = ((np.percentile(arr, 2.5), np.percentile(arr, 97.5))
                      if arr.size else (np.nan, np.nan))
            row[f"champion_gain_{metric}_lo"] = float(lo)
            row[f"champion_gain_{metric}_hi"] = float(hi)
            row[f"champion_beats_{metric}"] = bool(arr.size and lo > 0)
        rows.append(row)
    rows.append({"model": contenders[-1].name})
    return pd.DataFrame(rows)


def main() -> None:
    import argparse

    from src.model.train import load
    from src.util import enable_utf8_stdout

    enable_utf8_stdout()
    ap = argparse.ArgumentParser(description="Is the ML worth it? Baseline ablation.")
    ap.add_argument("--in", dest="inp", default="data/cod_orders.csv")
    ap.add_argument("--model-dir", default="models")
    ap.add_argument("--boot", type=int, default=500)
    args = ap.parse_args()

    from src.features.build_features import build_features

    bundle = build_features(pd.read_csv(args.inp))
    table = compare(bundle, load(args.model_dir)["model"], n_boot=args.boot)

    print("=" * 100)
    print("AXIOM — baseline ablation (identical features, val-fitted thresholds, test scored once)")
    print("=" * 100)
    show = table[["model", "tau_val_fitted", "pr_auc", "roc_auc", "brier", "cost_per_1k",
                  "saving_per_1k_vs_block_all_cod"]]
    print(show.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
    if "champion_gain_pr_auc_lo" in table.columns:
        print("-" * 100)
        print("Paired bootstrap — does LightGBM beat each simpler model? (95% CI on the gap)")
        for r in table.itertuples():
            if not isinstance(getattr(r, "champion_gain_pr_auc_lo", None), float):
                continue
            if not np.isfinite(r.champion_gain_pr_auc_lo):
                continue
            verdict = "YES" if r.champion_beats_pr_auc else "NOT SHOWN (interval spans 0)"
            print(f"  vs {r.model:<24} PR-AUC gain "
                  f"[{r.champion_gain_pr_auc_lo:+.4f}, {r.champion_gain_pr_auc_hi:+.4f}]  "
                  f"-> {verdict}")
            print(f"  {'':<27} ₹/1k saved "
                  f"[{r.champion_gain_cost_per_1k_lo:+,.0f}, "
                  f"{r.champion_gain_cost_per_1k_hi:+,.0f}]")


if __name__ == "__main__":
    main()


def interaction_probe(bundle: FeatureBundle, seed: int = 42) -> dict:
    """Is there any interaction structure in this data for a tree ensemble to exploit?

    Why this exists: the ablation shows LightGBM failing to beat logistic regression, and
    it would be easy to present that as a surprising empirical finding about RTO. It is
    not. The synthetic generator builds its risk as a plain weighted sum of per-feature
    terms passed through a sigmoid — no interaction terms anywhere — so a logistic model is
    the *correctly specified* model for this world and the tie is the expected result.

    Rather than assert that from reading the generator, measure it: fit a linear logistic
    model, then the same model with every pairwise interaction added. If the interactions
    buy nothing (or cost accuracy through added variance) there is no non-additive
    structure present, and no amount of tree depth can find any.

    This matters for the reader's interpretation: it is evidence about our *dataset*, not
    about the RTO problem, and the distinction is the honest one to draw.
    """
    from sklearn.preprocessing import PolynomialFeatures, StandardScaler

    X_tr, y_tr = bundle.split("train")
    X_te, y_te = bundle.split("test")
    num_tr = _numeric_matrix(X_tr)
    num_te = _numeric_matrix(X_te)
    scaler = StandardScaler().fit(num_tr)
    Z_tr, Z_te = scaler.transform(num_tr), scaler.transform(num_te)
    y_tr, y_te = y_tr.to_numpy(), y_te.to_numpy()

    linear = LogisticRegression(max_iter=3000, random_state=seed).fit(Z_tr, y_tr)
    linear_ap = float(average_precision_score(y_te, linear.predict_proba(Z_te)[:, 1]))

    poly = PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)
    P_tr, P_te = poly.fit_transform(Z_tr), poly.transform(Z_te)
    crossed = LogisticRegression(max_iter=3000, random_state=seed).fit(P_tr, y_tr)
    crossed_ap = float(average_precision_score(y_te, crossed.predict_proba(P_te)[:, 1]))

    return {
        "linear_pr_auc": linear_ap,
        "with_pairwise_interactions_pr_auc": crossed_ap,
        "interaction_gain": crossed_ap - linear_ap,
        "n_interaction_terms": int(P_tr.shape[1] - Z_tr.shape[1]),
        "additive_dgp": bool(crossed_ap - linear_ap <= 0.0),
        "note": ("The generator composes risk additively (a sigmoid over a weighted sum), so "
                 "logistic regression is correctly specified here and adding interactions "
                 "cannot help. A tree ensemble therefore has nothing extra to find — which "
                 "explains the ablation result and is a property of this synthetic dataset, "
                 "not a claim about real RTO data."),
    }
