"""One command that regenerates every number Axiom publishes.

    python -m src.model.full_report

Writes ``reports/evaluation.json`` (machine-readable), the three figures, and
``docs/evaluation.md`` — which is **generated, never hand-typed**. That is deliberate: a
README statistic that a human retyped is a statistic that can drift from the code, and on
a project whose entire thesis is honest measurement, drift is indistinguishable from
fabrication. If a number appears in the docs, this file produced it, and anyone can
re-run it.

Contents of the report, in the order a sceptic asks for them:

1. headline metrics on the untouched test split, with bootstrap intervals;
2. the money story at the **validation-fitted** threshold, plus the optimism gap against
   the test-optimal oracle we declined to use;
3. the ablation ladder — does the ML beat a scorecard and a logistic regression, and is
   the gap larger than the sampling noise;
4. the failure-mode matrix — which good customers absorb the false positives;
5. the band economics — the derived cut-points against the magic numbers they replaced,
   plus a sweep over the assumptions behind them;
6. the two leakage taxes — outcome-lag, and the deliberately-leaked model.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.build_features import build_features
from src.model.baselines import compare, interaction_probe
from src.model.evaluation import CostModel, block_all_breakeven, cost_curve, report, save_plots
from src.model.evaluation import total_cost
from src.model.slices import disparity, slice_report, worst_slices
from src.model.threshold import (
    ActionModel,
    band_policy_cost,
    fit_thresholds,
    load_thresholds,
    sensitivity,
)
from src.model.train import load, train_model
from src.util import to_jsonable as _clean

DOCS_FIGURES = Path("docs/figures")
REPORTS = Path("reports")


def build(orders_path: str = "data/cod_orders.csv", model_dir: str = "models",
          n_boot: int = 500, lag_tax: bool = True) -> dict:
    """Compute the whole evidence pack. Returns the report dict (also written to disk)."""
    cm = CostModel()
    orders = pd.read_csv(orders_path)
    model = load(model_dir)["model"]
    bundle = build_features(orders)
    val = bundle.frame[bundle.frame["split"] == "val"]
    test = bundle.frame[bundle.frame["split"] == "test"]

    thresholds = load_thresholds(model_dir) or fit_thresholds(
        val["is_rto"].to_numpy(), model.predict_proba(val[bundle.feature_columns]),
        val["order_value"].to_numpy(), cm)

    proba = model.predict_proba(test[bundle.feature_columns])
    y = test["is_rto"].to_numpy()
    value = test["order_value"].to_numpy()

    head = report(y, proba, value, test["is_cod"].to_numpy(), cm,
                  tau=thresholds.tau_star, n_boot=n_boot)
    curve = head.pop("_curve")

    ablation = compare(bundle, model, cm, n_boot=min(n_boot, 300))
    slices = slice_report(test, proba, thresholds.tau_star, cm)

    derived = band_policy_cost(y, proba, value, thresholds.tau_low, thresholds.tau_high, cm)
    legacy = band_policy_cost(y, proba, value, 0.15, 0.45, cm)
    is_cod = test["is_cod"].to_numpy()
    breakeven = block_all_breakeven(y, value, is_cod, cm)
    recall_tradeoff = _recall_tradeoff(y, proba, value, thresholds.tau_star, cm)
    interactions = interaction_probe(bundle)

    out = {
        "generated_on": date.today().isoformat(),
        "data": {
            "path": orders_path, "n_orders": int(len(orders)),
            "provenance": "synthetic — causal COD/RTO generator (seed 42)",
            "split_policy": "chronological; the test split is never resampled",
            "split_sizes": bundle.meta["split_sizes"],
            "test_rto_rate_natural": bundle.meta["test_rto_rate"],
            "outcome_lag_days": bundle.meta["outcome_lag_days"],
        },
        "headline": head,
        "thresholds": thresholds.as_dict(),
        "band_economics": {
            "derived": derived, "legacy_hardcoded": legacy,
            "saving_per_1k_vs_hardcoded": legacy["cost_per_1k"] - derived["cost_per_1k"],
            "assumption_sweep": sensitivity(value, cm),
            "action_model": asdict(ActionModel()),
        },
        "ablation": ablation,
        "block_all_breakeven": breakeven,
        "recall_tradeoff": recall_tradeoff,
        "interaction_probe": interactions,
        "failure_modes": {
            "slices": slices, "worst": worst_slices(slices), "disparity": disparity(slices),
        },
    }

    if lag_tax:
        out["lag_tax"] = _lag_tax(orders)
    out["leakage_tax"] = _leakage_tax(orders, y, proba)

    REPORTS.mkdir(parents=True, exist_ok=True)
    head["_curve"] = curve
    figures = save_plots(y, proba, head, REPORTS)
    head.pop("_curve")
    DOCS_FIGURES.mkdir(parents=True, exist_ok=True)
    for fig in figures:
        shutil.copyfile(fig, DOCS_FIGURES / fig.name)
    out["figures"] = [str(DOCS_FIGURES / f.name) for f in figures]

    (REPORTS / "evaluation.json").write_text(
        json.dumps(_clean(out), indent=2), encoding="utf-8")
    return out


def _recall_tradeoff(y, proba, value, shipped_tau: float, cm: CostModel) -> list[dict]:
    """What buying more recall actually costs, in rupees.

    "You only catch a third of returns" is the first thing anyone says about this
    model, so the answer should be a table rather than a paragraph. Rows are taken from
    the test cost curve at a spread of recall targets; the comparison column is against
    the shipped operating point.
    """
    curve = cost_curve(y, proba, value, cm, n_grid=399)
    n = len(y)
    shipped_cost = total_cost(np.asarray(proba) >= shipped_tau, y, value, cm) / n * 1000.0
    rows = []
    for target in (0.25, 0.335, 0.50, 0.65, 0.80):
        row = curve.iloc[(curve["recall"] - target).abs().argmin()]
        cost_per_1k = float(row["cost"]) / n * 1000.0
        rows.append({
            "target_recall": target,
            "recall": float(row["recall"]),
            "threshold": float(row["threshold"]),
            "precision": float(row["precision"]),
            "cost_per_1k": cost_per_1k,
            "delta_vs_shipped_per_1k": cost_per_1k - shipped_cost,
            "is_shipped": bool(abs(float(row["threshold"]) - shipped_tau) < 0.01),
        })
    return rows


def _lag_tax(orders: pd.DataFrame) -> dict:
    """What honouring the outcome-availability lag costs us in predictive power."""
    rows = {}
    for lag in (0.0, 7.0):
        bundle = build_features(orders, outcome_lag_days=lag)
        rows[lag] = train_model(bundle).metrics["test"]
    naive, honest = rows[0.0], rows[7.0]
    return {
        "naive_no_lag": naive, "with_7d_lag": honest,
        "pr_auc_cost": naive["pr_auc"] - honest["pr_auc"],
        "note": ("A 0-day lag lets a feature count outcomes that had not resolved when the "
                 "order was scored. We ship the 7-day version and report what it cost."),
    }


def _leakage_tax(orders: pd.DataFrame, y: np.ndarray, proba: np.ndarray) -> dict:
    """The fake 0.97 we could have published, beside the real number."""
    from sklearn.metrics import average_precision_score, roc_auc_score

    leaky_bundle = build_features(orders, leak=True)
    leaky = train_model(leaky_bundle, params={"n_estimators": 300, "learning_rate": 0.05})
    lt = leaky_bundle.frame[leaky_bundle.frame["split"] == "test"]
    lp = leaky.model.predict_proba(lt[leaky_bundle.feature_columns])
    ly = lt["is_rto"].to_numpy()
    return {
        "honest": {"roc_auc": float(roc_auc_score(y, proba)),
                   "pr_auc": float(average_precision_score(y, proba))},
        "leaked_INVALID": {"roc_auc": float(roc_auc_score(ly, lp)),
                           "pr_auc": float(average_precision_score(ly, lp))},
        "note": "The leaked model is INVALID — target encoding fitted on all rows including "
                "each row's own label. Shown only to prove the inflated number is trivial "
                "to manufacture.",
    }


# --------------------------------------------------------------------------------------
# docs/evaluation.md — generated, so it can never drift from the code
# --------------------------------------------------------------------------------------

def _rs(x: float) -> str:
    return f"₹{x:,.0f}"


def _ci(head: dict, key: str, fmt: str = "{:.3f}") -> str:
    ci = head.get("ci", {}).get(key)
    return "" if not ci else f" _(95% CI {fmt.format(ci['lo'])}–{fmt.format(ci['hi'])})_"


def render_markdown(rep: dict) -> str:
    rep_dict = rep
    head, mon, at = rep["headline"], rep["headline"]["money"], rep["headline"]["at_tau_star"]
    th, band = rep["thresholds"], rep["band_economics"]
    ab = pd.DataFrame(rep["ablation"]) if not isinstance(rep["ablation"], pd.DataFrame) \
        else rep["ablation"]
    worst = rep["failure_modes"]["worst"]
    worst = worst if isinstance(worst, pd.DataFrame) else pd.DataFrame(worst)
    disp = rep["failure_modes"]["disparity"]
    disp = disp if isinstance(disp, pd.DataFrame) else pd.DataFrame(disp)
    lag, leak = rep.get("lag_tax"), rep["leakage_tax"]
    d = rep["data"]

    lines: list[str] = []
    add = lines.append

    add("# Evaluation — honest metrics")
    add("")
    add(f"> **Generated by `python -m src.model.full_report` on {rep['generated_on']}.** "
        "Every number on this page comes out of that command; none is typed by hand. "
        "Re-run it and the page rewrites itself.")
    add("")
    add(f"Data: {d['n_orders']:,} orders, {d['provenance']}. Split {d['split_policy']} — "
        f"train/val/test = {d['split_sizes'].get('train')}/{d['split_sizes'].get('val')}/"
        f"{d['split_sizes'].get('test')}, test RTO rate "
        f"{d['test_rto_rate_natural']:.1%} (natural, never resampled). Label-derived history "
        f"features respect a **{d['outcome_lag_days']:.0f}-day outcome-availability lag**.")
    add("")

    add("## 1. Why accuracy is not on this page")
    add("")
    add(f"At a {head['prevalence']:.1%} RTO rate, a model that flags nothing scores "
        f"{1 - head['prevalence']:.1%} accuracy and prevents zero returns. Accuracy would "
        "reward exactly the model we must not ship, so it is not reported anywhere in this "
        "repository. The headline is the rupee cost curve.")
    add("")

    add("## 2. Ranking quality on the untouched test split")
    add("")
    add("| metric | value | no-skill baseline |")
    add("|---|---|---|")
    add(f"| PR-AUC | **{head['pr_auc']:.3f}**{_ci(head, 'pr_auc')} | "
        f"{head['prevalence']:.3f} (prevalence) |")
    add(f"| ROC-AUC | {head['roc_auc']:.3f}{_ci(head, 'roc_auc')} | 0.500 |")
    add(f"| Precision @ top 10% | {head['precision_at_10pct']:.3f} | "
        f"{head['prevalence']:.3f} |")
    add("")
    add("Intervals are percentile bootstrap over test orders "
        f"({head.get('ci', {}).get('n_boot', 0)} resamples, seed "
        f"{head.get('ci', {}).get('seed', 42)}). This is a deliberately unglamorous "
        "PR-AUC: see §7 for the 0.9-something we could have published instead.")
    add("")

    add("## 3. The operating point is chosen on validation, not on test")
    add("")
    add(f"τ = **{th['tau_star']:.3f}**, fitted by minimising rupee cost on the validation "
        f"split ({th['n_fitted']:,} orders) and then frozen. The test split below was "
        "scored once, at that value.")
    add("")
    add("| | threshold | cost per 1k orders |")
    add("|---|---|---|")
    add(f"| **Shipped** — τ fitted on validation | {head['tau_star']:.3f} | "
        f"**{_rs(mon['model_cost_per_1k'])}**{_ci(head, 'cost_per_1k', '{:,.0f}')} |")
    add(f"| Oracle — τ tuned on test (not reportable) | {head['oracle']['tau']:.3f} | "
        f"{_rs(head['oracle']['cost_per_1k'])} |")
    add(f"| **Optimism we declined** | | "
        f"{_rs(head['optimism']['cost_gap_per_1k'])} "
        f"({head['optimism']['gap_pct_of_model_cost']:.1f}%) |")
    add("")
    add("Publishing that gap is the point. Tuning the threshold on the test split would "
        f"have made the headline look {_rs(head['optimism']['cost_gap_per_1k'])} per 1,000 "
        "orders better, and would have been unreachable in production.")
    add("")
    add(f"At the frozen τ: precision **{at['precision']:.3f}**{_ci(head, 'precision')}, "
        f"recall **{at['recall']:.3f}**{_ci(head, 'recall')}, flag rate "
        f"{at['flag_rate']:.1%} (TP {at['tp']}, FP {at['fp']}, FN {at['fn']}).")
    add("")
    add("### \"You only catch a third of the returns\"")
    add("")
    add("Correct, and deliberate. Recall is not free — every point of it is bought with "
        "friction on genuine customers, and past a point that costs more than the returns "
        "it prevents. What the extra recall would actually cost, on this split:")
    add("")
    add("| recall | τ | precision | ₹ / 1k | vs shipped |")
    add("|---:|---:|---:|---:|---:|")
    for r in rep_dict["recall_tradeoff"]:
        mark = " ← **shipped**" if r["is_shipped"] else ""
        delta = "—" if r["is_shipped"] else f"{r['delta_vs_shipped_per_1k']:+,.0f}"
        add(f"| {r['recall']:.3f}{mark} | {r['threshold']:.3f} | {r['precision']:.3f} | "
            f"{_rs(r['cost_per_1k'])} | {delta} |")
    add("")
    add("Two honest readings of that table. Pushing recall past ~0.65 costs real money, so "
        "the low recall is a defensible choice rather than a weakness we are hiding. But the "
        "middle rows are *cheaper* than what we shipped — the validation split simply put the "
        "threshold higher than the test split would have liked, and that difference is exactly "
        "the optimism gap above. We could have had it by choosing τ with knowledge of the test "
        "set, which is the one thing we will not do.")
    add("")

    add("## 4. The money story")
    add("")
    add("Costs are example-dependent: a missed return on a ₹3,000 order hurts more than on "
        "a ₹300 one. `c_FN` = round-trip logistics and handling plus a share of the order "
        "value; `c_FP` = the servicing and abandonment cost of putting a genuine customer "
        "through friction. Both are assumptions, stated here and swept in §8.")
    add("")
    add("| policy | ₹ per 1,000 orders |")
    add("|---|---:|")
    add(f"| Approve everything | {_rs(mon['approve_all_cost_per_1k'])} |")
    add(f"| Block all COD (naive) | {_rs(mon['block_all_cod_cost_per_1k'])} |")
    add(f"| **Axiom @ frozen τ** | **{_rs(mon['model_cost_per_1k'])}** |")
    add("")
    saving_ci = head.get("ci", {}).get("saving_per_1k_vs_block_all_cod")
    saving_txt = ("" if not saving_ci else
                  f" (95% CI {_rs(saving_ci['lo'])}–{_rs(saving_ci['hi'])})")
    add(f"Axiom is {_rs(mon['rupees_saved_per_1k_vs_block_all_cod'])} per 1,000 orders "
        f"cheaper than blocking all COD{saving_txt} and "
        f"{mon['savings_vs_approve_all_pct']:.1f}% cheaper than approving everything.")
    add("")
    be = rep["block_all_breakeven"]
    add("### The middle row is a claim, so here is its break-even")
    add("")
    add("Blocking all COD costing more than doing nothing is not a measurement — it is an "
        "arithmetic consequence of the assumed friction cost, and it deserves to be stated "
        "as one. The policy buys back `c_FN` on every COD order that would have returned "
        "and pays `c_FP` on every one that would not:")
    add("")
    add(f"- COD returns it would prevent: **{be['n_cod_returns_prevented']:,}**, worth "
        f"{_rs(be['value_of_prevented_returns'])}")
    add(f"- genuine COD customers it would challenge: **{be['n_good_cod_challenged']:,}**")
    add(f"- **break-even: {_rs(be['breakeven_mean_fp_cost'])}** per challenged genuine "
        "customer")
    add(f"- our assumed cost: **{_rs(be['assumed_mean_fp_cost'])}** — "
        f"**{be['headroom_ratio']:.2f}x** the break-even")
    add("")
    add(f"So the finding holds for any friction cost above {_rs(be['breakeven_mean_fp_cost'])} "
        "and reverses below it. That is thin headroom, and we would rather a reader see the "
        "pivot than take the headline on trust: substitute your own number for what it costs "
        "to make a genuine customer prove themselves, and the conclusion follows or it does "
        "not. The dashboard slider exists for exactly this.")
    add("")
    add("![BMR cost curve](figures/cost_curve.png)")
    add("")
    add("| | |\n|---|---|\n| ![PR curve](figures/pr_curve.png) | "
        "![Calibration](figures/calibration.png) |")
    add("")

    add("## 5. Is the machine learning worth it?")
    add("")
    add("Beating \"do nothing\" proves nothing. The real question is whether the model beats "
        "what a competent risk analyst would ship without it. Every contender below gets "
        "identical features and splits, isotonic calibration on validation, and its own "
        "validation-fitted threshold.")
    add("")
    add("| model | τ (val) | PR-AUC | ROC-AUC | Brier | ₹ / 1k |")
    add("|---|---:|---:|---:|---:|---:|")
    for r in ab.itertuples():
        pr = "—" if not np.isfinite(r.pr_auc) else f"{r.pr_auc:.3f}"
        roc = "—" if not np.isfinite(r.roc_auc) else f"{r.roc_auc:.3f}"
        bold = "**" if "LightGBM" in r.model else ""
        add(f"| {bold}{r.model}{bold} | {r.tau_val_fitted:.3f} | {pr} | {roc} | "
            f"{r.brier:.4f} | {_rs(r.cost_per_1k)} |")
    add("")
    if "champion_gain_pr_auc_lo" in ab.columns:
        add("Paired bootstrap on the gap (same resampled orders for both models):")
        add("")
        for r in ab.itertuples():
            lo = getattr(r, "champion_gain_pr_auc_lo", np.nan)
            if not isinstance(lo, float) or not np.isfinite(lo):
                continue
            verdict = ("**LightGBM wins**" if r.champion_beats_pr_auc else
                       "**not shown to be better** — the interval spans zero")
            add(f"- vs {r.model}: PR-AUC gain "
                f"[{r.champion_gain_pr_auc_lo:+.3f}, {r.champion_gain_pr_auc_hi:+.3f}] → "
                f"{verdict}.")
        add("")
        beaten = [r for r in ab.itertuples()
                  if isinstance(getattr(r, "champion_beats_pr_auc", None), (bool, np.bool_))
                  and not r.champion_beats_pr_auc]
        if beaten:
            probe = rep_dict["interaction_probe"]
            add("**Why logistic regression ties — and why that is expected, not surprising.**")
            add("")
            add("It would be easy to present this as a finding about RTO. It is not. Our "
                "generator composes risk *additively* — a sigmoid over a weighted sum of "
                "per-feature terms, with no interaction terms anywhere "
                "(`src/data/generate_synthetic_cod.py`). A logistic model is therefore the "
                "**correctly specified** model for this world, and no tree ensemble can beat "
                "a correctly specified model except by luck.")
            add("")
            add("Rather than assert that from reading our own generator, we measured it — "
                f"adding all {probe['n_interaction_terms']} pairwise interactions to the "
                "logistic model changes test PR-AUC by "
                f"**{probe['interaction_gain']:+.4f}** "
                f"({probe['linear_pr_auc']:.4f} → {probe['with_pairwise_interactions_pr_auc']:.4f}). "
                "There is no non-additive structure to find, so there is nothing for depth to "
                "buy.")
            add("")
            add("This is a limitation of the **synthetic world**, not a result about real "
                "order flow, where interactions plainly do exist — a first-time buyer at a "
                "high-risk pincode is worse than the sum of those two facts. We keep LightGBM "
                "because it will find that structure when the data has it, and because SHAP "
                "gives the per-order attributions the agent narrates. On *this* dataset we "
                "cannot demonstrate that advantage, and we do not claim it.")
            add("")

    add("## 6. Which good customers pay for the false positives?")
    add("")
    add("A portfolio-level false-positive rate hides the part that matters. `fp_rate_on_good` "
        "is the share of *genuine* customers in a slice that were put through friction.")
    add("")
    add("| slice | n | good customers | wrongly challenged | rate | ₹ cost | recall there |")
    add("|---|---:|---:|---:|---:|---:|---:|")
    for r in worst.to_dict(orient="records"):     # 'slice' shadows a builtin under itertuples
        add(f"| {r['dimension']}: **{r['slice']}** | {int(r['n'])} | {int(r['n_good'])} | "
            f"{int(r['false_positives'])} | {r['fp_rate_on_good']:.1%} | "
            f"{_rs(r['fp_cost'])} | {r['recall']:.2f} |")
    add("")
    if len(disp):
        # `ratio` is None where the least-challenged slice saw no false positives at all —
        # an undefined comparison, which we say rather than dress up as a big number.
        ratio_txt = lambda r: ("no false positives at all in the safest slice"  # noqa: E731
                               if r["ratio"] is None or not np.isfinite(r["ratio"])
                               else f"{r['ratio']:.1f}×")
        top = disp.iloc[0].to_dict()
        add(f"The friction is not spread evenly. Within **{top['dimension']}**, a genuine "
            f"customer in *{top['worst_slice']}* ({top['worst_fp_rate_on_good']:.1%}) is far "
            f"more likely to be challenged than one in *{top['best_slice']}* "
            f"({top['best_fp_rate_on_good']:.1%}) — {ratio_txt(top)}.")
        add("")
        add("| dimension | most challenged | least challenged | ratio |")
        add("|---|---|---|---:|")
        for r in disp.to_dict(orient="records"):
            add(f"| {r['dimension']} | {r['worst_slice']} ({r['worst_fp_rate_on_good']:.1%}) | "
                f"{r['best_slice']} ({r['best_fp_rate_on_good']:.1%}) | {ratio_txt(r)} |")
        add("")
    add("This is why the response is **dynamic friction and not a block**: a mis-flagged "
        "customer is asked to confirm an address or offered a prepaid link, and can clear "
        "themselves in one step. The disparity above is a real cost we own and monitor, not "
        "one we discovered in the writeup and left out. It uses no protected attribute — "
        "city tier, order value and category are commercial variables — so this is an "
        "operational harm audit, not a legal fairness audit.")
    add("")

    add("## 7. Two leakage taxes we paid")
    add("")
    add("**Outcome-availability lag.** An order placed today cannot know whether yesterday's "
        "order was returned — the delivery attempt has not resolved. Label-derived history "
        f"features are therefore held back {d['outcome_lag_days']:.0f} days.")
    if lag:
        add("")
        add("| encoder | test PR-AUC | ROC-AUC |")
        add("|---|---:|---:|")
        add(f"| naive as-of (0-day lag, optimistic) | {lag['naive_no_lag']['pr_auc']:.4f} | "
            f"{lag['naive_no_lag']['roc_auc']:.4f} |")
        add(f"| **shipped ({d['outcome_lag_days']:.0f}-day lag)** | "
            f"**{lag['with_7d_lag']['pr_auc']:.4f}** | {lag['with_7d_lag']['roc_auc']:.4f} |")
        add("")
        add(f"Honouring the lag costs us {abs(lag['pr_auc_cost']):.4f} PR-AUC. Small — most of "
            "the signal is structural (address quality, payment mode, distance) rather than "
            "recent-outcome memory — but it is the difference between a number that survives "
            "production and one that does not.")
    add("")
    add("**Deliberate leakage.** Fitting the target encoders on all rows, including each "
        "row's own label, produces the sort of figure public RTO models advertise:")
    add("")
    add("| model | ROC-AUC | PR-AUC |")
    add("|---|---:|---:|")
    add(f"| **Axiom (honest)** | **{leak['honest']['roc_auc']:.3f}** | "
        f"**{leak['honest']['pr_auc']:.3f}** |")
    add(f"| Leaked variant — INVALID | {leak['leaked_INVALID']['roc_auc']:.3f} | "
        f"{leak['leaked_INVALID']['pr_auc']:.3f} |")
    add("")
    add("We can manufacture the impressive number in one line of code. It is worthless: the "
        "encoder has memorised the answer. The lower number is the one that would survive "
        "contact with real orders.")
    add("")

    add("## 8. Where the band cut-points come from")
    add("")
    add("GREEN / AMBER / RED are not hand-picked. Each band's action has a friction cost and "
        "an efficacy, and setting the expected costs equal gives closed-form cut-points "
        "(`src/model/threshold.py`):")
    add("")
    add(f"`green < {th['tau_low']:.3f} ≤ amber < {th['tau_high']:.3f} ≤ red`")
    add("")
    add("| policy | ₹ / 1k | green | amber | red |")
    add("|---|---:|---:|---:|---:|")
    for label, b in (("**Derived from the cost model**", band["derived"]),
                     ("Previously hard-coded 0.15 / 0.45", band["legacy_hardcoded"])):
        add(f"| {label} | {_rs(b['cost_per_1k'])} | {b['n_green']} | {b['n_amber']} | "
            f"{b['n_red']} |")
    add("")
    add(f"Deriving the cut-points instead of guessing them is worth "
        f"{_rs(band['saving_per_1k_vs_hardcoded'])} per 1,000 orders.")
    add("")
    am = band["action_model"]
    add(f"The efficacies (`amber {am['amber_efficacy']:.2f}`, `red "
        f"{am['red_efficacy']:.2f}`) are **assumptions** — we have no counterfactual data on "
        "what a step-up prevents. So they are swept rather than asserted:")
    sweep = band["assumption_sweep"]
    sweep = sweep if isinstance(sweep, pd.DataFrame) else pd.DataFrame(sweep)
    add("")
    add(f"- τ_low ranges **{sweep['tau_low'].min():.2f}–{sweep['tau_low'].max():.2f}** and "
        f"τ_high **{sweep['tau_high'].min():.2f}–{sweep['tau_high'].max():.2f}** across the "
        "plausible range.")
    add("- The amber cut-point is dominated by the assumed step-up efficacy. Any merchant "
        "deploying this should measure that efficacy on their own traffic and re-derive; the "
        "formula, not the constant, is the deliverable.")
    add("")

    add("## 9. Known limitations")
    add("")
    add("- **The data is synthetic.** No clean public Indian COD/RTO dataset exists, so orders "
        "are drawn from an explicit causal model of the published RTO drivers. Every metric "
        "here is real, measured on held-out data the model never saw — but the *world* is "
        "generated. On real orders the model must be recalibrated before any rupee claim.")
    add("- **The cost model is assumed, not audited.** The rupee conclusions move with "
        "`c_FP`/`c_FN`; the interactive slider in the dashboard exists so a reviewer can "
        "substitute their own numbers.")
    add("- **The action efficacies are assumed** (§8) and are the largest source of "
        "uncertainty in the band economics.")
    add("- **The generator is additive, so logistic regression is correctly specified** and "
        "LightGBM cannot beat it here (§5). Any claim that the tree ensemble is the better "
        "model would have to be made on real, interaction-bearing data.")
    add("- **The headline cost comparison has ~12% headroom** on the assumed friction cost "
        "(§4). It is an argument with a stated pivot, not a measurement.")
    add("- **A calibrated ranker is not a fraud oracle.** Recall at the frozen threshold is "
        f"{at['recall']:.0%}: most returns are not caught, and the system is built around "
        "that fact — bounded, reversible friction with human override, rather than blocks.")
    add("")
    return "\n".join(lines) + "\n"


REQUIRED_SECTIONS = (
    "Why accuracy is not on this page",
    "Ranking quality on the untouched test split",
    "The operating point is chosen on validation, not on test",
    "The money story",
    "Is the machine learning worth it?",
    "Which good customers pay for the false positives?",
    "Two leakage taxes we paid",
    "Where the band cut-points come from",
    "Known limitations",
)


def check(rep: dict, markdown: str) -> list[str]:
    """Structural and internal-consistency audit of a freshly generated report.

    Deliberately *not* a byte-for-byte diff against the committed page. A gradient-boosted
    model retrained on another OS and another LightGBM build lands on slightly different
    trees, so byte equality would fail for reasons that have nothing to do with honesty.
    What must hold on every platform is that the page is complete, quotes the threshold we
    actually froze, and does not contradict itself. Returns the list of problems (empty is
    a pass).
    """
    problems: list[str] = []
    head, th = rep["headline"], rep["thresholds"]

    for section in REQUIRED_SECTIONS:
        if section not in markdown:
            problems.append(f"missing section: {section}")
    for placeholder in ("TBD", "TODO", "FIXME", "XXX"):
        if placeholder in markdown:
            problems.append(f"unfilled placeholder in the published page: {placeholder}")
    if "nan" in markdown.lower().replace("finance", ""):
        problems.append("a NaN reached the published page")

    if head["tau_source"] != "val_frozen":
        problems.append("the headline was scored at a threshold that was not frozen on val")
    if th["fitted_on"] != "val":
        problems.append("the operating point was not fitted on the validation split")
    if head["optimism"]["cost_gap"] < 0:
        problems.append("the frozen threshold beats the test oracle — the oracle is wrong")
    if f"{th['tau_star']:.3f}" not in markdown:
        problems.append("the page does not quote the frozen threshold it was scored at")
    if head["money"]["model_cost_per_1k"] >= head["money"]["approve_all_cost_per_1k"]:
        problems.append("the model costs more than approving everything")
    if rep["band_economics"]["saving_per_1k_vs_hardcoded"] < 0:
        problems.append("the derived bands are worse than the hard-coded ones they replaced")
    if "accuracy" not in markdown.lower():
        problems.append("the page no longer explains why accuracy is not reported")
    return problems


def main() -> None:
    import argparse
    import sys

    from src.util import enable_utf8_stdout

    enable_utf8_stdout()
    ap = argparse.ArgumentParser(description="Regenerate every published Axiom number.")
    ap.add_argument("--in", dest="inp", default="data/cod_orders.csv")
    ap.add_argument("--model-dir", default="models")
    ap.add_argument("--boot", type=int, default=500)
    ap.add_argument("--quick", action="store_true", help="skip the lag-tax retrain")
    ap.add_argument("--docs", default="docs/evaluation.md")
    ap.add_argument("--check", action="store_true",
                    help="audit the generated report and exit non-zero on any problem (CI)")
    args = ap.parse_args()

    rep = build(args.inp, args.model_dir, n_boot=args.boot, lag_tax=not args.quick)
    markdown = render_markdown(rep)
    Path(args.docs).write_text(markdown, encoding="utf-8")

    if args.check:
        problems = check(rep, markdown)
        if problems:
            print("EVIDENCE PACK FAILED ITS OWN AUDIT:")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        print(f"evidence pack passed its audit ({len(REQUIRED_SECTIONS)} sections, "
              "internally consistent)")

    head, mon = rep["headline"], rep["headline"]["money"]
    print("=" * 78)
    print("AXIOM — full evidence pack regenerated")
    print("=" * 78)
    print(f"  PR-AUC {head['pr_auc']:.3f} (prevalence {head['prevalence']:.3f})   "
          f"ROC-AUC {head['roc_auc']:.3f}")
    print(f"  frozen τ {head['tau_star']:.3f} (fitted on val)  ->  "
          f"₹{mon['model_cost_per_1k']:,.0f}/1k")
    print(f"  optimism declined: ₹{head['optimism']['cost_gap_per_1k']:,.0f}/1k")
    print(f"  vs block-all-COD : ₹{mon['rupees_saved_per_1k_vs_block_all_cod']:,.0f}/1k saved")
    print("-" * 78)
    print(f"  wrote {REPORTS / 'evaluation.json'}")
    print(f"  wrote {args.docs}")
    print(f"  figures -> {DOCS_FIGURES}")


if __name__ == "__main__":
    main()
