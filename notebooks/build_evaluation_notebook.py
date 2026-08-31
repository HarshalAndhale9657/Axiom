"""Generate ``notebooks/03_evaluation.ipynb`` — the runnable version of the evidence pack.

The notebook is generated rather than hand-edited for the same reason
``docs/evaluation.md`` is: a notebook that has been executed, tweaked and re-saved by hand
accumulates stale outputs that disagree with the code. This script emits a clean notebook
whose every cell calls the same modules the API and the tests use, so running it top to
bottom reproduces the published numbers or fails loudly.

    python notebooks/build_evaluation_notebook.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "03_evaluation.ipynb"


def md(*lines: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _src(lines)}


def code(*lines: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": _src(lines)}


def _src(lines: tuple[str, ...]) -> list[str]:
    text = "\n".join(lines)
    return [f"{line}\n" for line in text.split("\n")[:-1]] + [text.split("\n")[-1]]


CELLS = [
    md(
        "# Axiom — honest evaluation",
        "",
        "The crown jewel of a Track-2 submission is not a model, it is the evidence that the",
        "model's numbers survive scrutiny. This notebook runs that evidence end to end, using",
        "the exact modules the API serves from — nothing here is re-implemented for the",
        "notebook, so it cannot quietly disagree with the product.",
        "",
        "Run order assumed: `python -m src.data.generate_synthetic_cod --n 20000 --seed 42`",
        "then `python -m src.model.train`.",
        "",
        "**The commitments this notebook demonstrates**",
        "",
        "1. Split by time; the test split keeps its natural RTO rate and is never resampled.",
        "2. History features use only the past — *and* only outcomes that had already resolved.",
        "3. The operating threshold is fitted on validation and frozen before test is scored.",
        "4. Headline metrics carry bootstrap intervals.",
        "5. The model is compared against a scorecard and a logistic regression, and we report",
        "   the comparison we lose.",
        "6. The false-positive burden is broken out by customer slice.",
    ),
    code(
        "import sys, warnings",
        "from pathlib import Path",
        "",
        "sys.path.insert(0, str(Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()))",
        "warnings.filterwarnings('ignore')",
        "",
        "import numpy as np",
        "import pandas as pd",
        "import matplotlib.pyplot as plt",
        "",
        "from src.features.build_features import build_features",
        "from src.model.train import load",
        "from src.model.threshold import load_thresholds, band_policy_cost, sensitivity",
        "from src.model.evaluation import CostModel, report, cost_curve, calibration_table",
        "from src.model.baselines import compare",
        "from src.model.slices import slice_report, worst_slices, disparity",
        "",
        "pd.set_option('display.width', 140)",
        "cm = CostModel()",
        "cm",
    ),
    md(
        "## 1. Data and the split",
        "",
        "Synthetic, and labelled as such everywhere. No clean public Indian COD/RTO dataset",
        "exists, so orders come from an explicit causal model of the published RTO drivers.",
        "The true latent drivers are written to a *separate* file and never reach the features:",
        "the model has to estimate them from observable history, exactly as it would live.",
    ),
    code(
        "orders = pd.read_csv('../data/cod_orders.csv')",
        "bundle = build_features(orders)",
        "frame = bundle.frame",
        "",
        "print(f\"orders            : {len(orders):,}\")",
        "print(f\"split sizes       : {bundle.meta['split_sizes']}\")",
        "print(f\"train prior (RTO) : {bundle.meta['train_prior']:.4f}\")",
        "print(f\"test RTO rate     : {bundle.meta['test_rto_rate']:.4f}  (natural, never resampled)\")",
        "print(f\"outcome lag       : {bundle.meta['outcome_lag_days']:.0f} days\")",
        "",
        "# The split is chronological, not shuffled — prove it rather than assert it.",
        "bounds = frame.groupby('split')['order_ts'].agg(['min', 'max']).loc[['train', 'val', 'test']]",
        "bounds",
    ),
    md(
        "## 2. The leakage guards, executed",
        "",
        "Two independent checks. The first is the classic one: the first time a pincode is ever",
        "seen it has no history, so its target encoding must equal the training prior exactly —",
        "if a row's own label leaked in, this would not hold. The second is the one almost",
        "nobody runs: an order placed today cannot know whether *yesterday's* order was",
        "returned, because the delivery attempt has not resolved. Both are enforced in code and",
        "in `tests/`; here we watch them hold.",
    ),
    code(
        "prior = bundle.meta['train_prior']",
        "first_sighting = frame.groupby('pincode', sort=False).head(1)",
        "deviation = (first_sighting['pincode_rto_enc'] - prior).abs().max()",
        "print(f'first-sighting encoding == train prior, max deviation: {deviation:.2e}')",
        "",
        "# No feature may be a near-perfect predictor of its own label.",
        "corr = (frame[bundle.feature_columns].select_dtypes('number')",
        "        .corrwith(frame['is_rto']).abs().sort_values(ascending=False))",
        "print('\\ntop |correlation| with the label (none should approach 1.0):')",
        "corr.head(6).round(3)",
    ),
    code(
        "# The outcome-availability lag, priced.",
        "from src.model.train import train_model",
        "",
        "lag_rows = []",
        "for lag in (0.0, 7.0):",
        "    b = build_features(orders, outcome_lag_days=lag)",
        "    m = train_model(b).metrics['test']",
        "    lag_rows.append({'outcome_lag_days': lag, **{k: m[k] for k in ('pr_auc', 'roc_auc', 'brier')}})",
        "",
        "lag_tax = pd.DataFrame(lag_rows)",
        "print('A 0-day lag counts outcomes that had not resolved when the order was scored.')",
        "print('We ship the 7-day row and pay the difference.')",
        "lag_tax",
    ),
    md(
        "## 3. The model, and the operating point we froze",
        "",
        "The threshold is a hyper-parameter. Fitting it on the test split and then reporting the",
        "cost at its minimum is threshold-selection leakage — the resulting number is an oracle",
        "that no production system can reach. Ours comes from validation and is frozen in",
        "`models/thresholds.json` at train time.",
    ),
    code(
        "model = load('../models')['model']",
        "thresholds = load_thresholds('../models')",
        "",
        "test = frame[frame['split'] == 'test']",
        "proba = model.predict_proba(test[bundle.feature_columns])",
        "y = test['is_rto'].to_numpy()",
        "value = test['order_value'].to_numpy()",
        "",
        "print(f'frozen on : {thresholds.fitted_on} ({thresholds.n_fitted:,} orders)')",
        "print(f'binary tau: {thresholds.tau_star:.3f}')",
        "print(f'bands     : green < {thresholds.tau_low:.3f} <= amber < {thresholds.tau_high:.3f} <= red')",
        "thresholds.as_dict()",
    ),
    code(
        "rep = report(y, proba, value, test['is_cod'].to_numpy(), cm,",
        "             tau=thresholds.tau_star, n_boot=500)",
        "ci = rep['ci']",
        "",
        "print(f\"PR-AUC   {rep['pr_auc']:.3f}  [95% CI {ci['pr_auc']['lo']:.3f}-{ci['pr_auc']['hi']:.3f}]\"",
        "      f\"   vs prevalence {rep['prevalence']:.3f}\")",
        "print(f\"ROC-AUC  {rep['roc_auc']:.3f}  [95% CI {ci['roc_auc']['lo']:.3f}-{ci['roc_auc']['hi']:.3f}]\")",
        "print(f\"P@10%    {rep['precision_at_10pct']:.3f}\")",
        "print()",
        "print(f\"shipped  tau={rep['tau_star']:.3f} -> Rs {rep['money']['model_cost_per_1k']:,.0f}/1k\")",
        "print(f\"oracle   tau={rep['oracle']['tau']:.3f} -> Rs {rep['oracle']['cost_per_1k']:,.0f}/1k  (NOT reportable)\")",
        "print(f\"optimism declined: Rs {rep['optimism']['cost_gap_per_1k']:,.0f}/1k \"",
        "      f\"({rep['optimism']['gap_pct_of_model_cost']:.1f}%)\")",
    ),
    md(
        "### Accuracy, for the one and only time",
        "",
        "Computed here purely to show why it is banned from every other page.",
    ),
    code(
        "flag = proba >= thresholds.tau_star",
        "print(f'model accuracy       : {(flag == y).mean():.3f}')",
        "print(f'accuracy of flagging nothing at all : {(y == 0).mean():.3f}')",
        "print()",
        "print('The do-nothing model wins on accuracy and prevents zero returns.')",
        "print('That is the entire argument for the rupee cost curve below.')",
    ),
    md("## 4. The money story"),
    code(
        "money = rep['money']",
        "summary = pd.DataFrame([",
        "    {'policy': 'approve everything', 'cost_per_1k': money['approve_all_cost_per_1k']},",
        "    {'policy': 'block ALL COD (naive)', 'cost_per_1k': money['block_all_cod_cost_per_1k']},",
        "    {'policy': 'Axiom @ frozen tau', 'cost_per_1k': money['model_cost_per_1k']},",
        "]).set_index('policy')",
        "print(f\"saving vs block-all-COD: Rs {money['rupees_saved_per_1k_vs_block_all_cod']:,.0f}/1k \"",
        "      f\"[95% CI {ci['saving_per_1k_vs_block_all_cod']['lo']:,.0f}-\"",
        "      f\"{ci['saving_per_1k_vs_block_all_cod']['hi']:,.0f}]\")",
        "summary.round(0)",
    ),
    code(
        "curve = cost_curve(y, proba, value, cm)",
        "n = len(y)",
        "",
        "fig, ax = plt.subplots(figsize=(9, 4.5))",
        "ax.plot(curve['threshold'], curve['cost'] / n * 1000, lw=2.2, color='#2563eb', label='Axiom')",
        "ax.axhline(rep['baselines']['block_all_cod_cost'] / n * 1000, ls=':', color='#e11d48',",
        "           label='block all COD')",
        "ax.axhline(rep['baselines']['approve_all_cost'] / n * 1000, ls=':', color='#64748b',",
        "           label='approve everything')",
        "ax.axvline(thresholds.tau_star, ls='--', color='#2563eb', label=f'shipped tau (val) = {thresholds.tau_star:.3f}')",
        "ax.axvline(rep['oracle']['tau'], ls='-.', lw=1.2, color='#fca5a5',",
        "           label=f\"test-oracle tau = {rep['oracle']['tau']:.3f} (unused)\")",
        "ax.axvline(0.5, lw=0.9, color='#cbd5e1', label='naive 0.5')",
        "ax.set(xlabel='decision threshold', ylabel='cost per 1,000 orders (Rs)',",
        "       title='Blocking all COD costs more than doing nothing')",
        "ax.legend(fontsize=8)",
        "fig.tight_layout()",
    ),
    md(
        "### Calibration",
        "",
        "Every rupee conclusion above is a threshold on a probability, so the probabilities have",
        "to mean what they say. This is why the model is isotonically calibrated on validation",
        "and why no resampling is used anywhere in the pipeline.",
    ),
    code(
        "ct = calibration_table(y, proba)",
        "fig, ax = plt.subplots(figsize=(5, 4.5))",
        "ax.plot([0, 1], [0, 1], ls='--', color='#cbd5e1', label='perfect')",
        "ax.plot(ct['mean_pred'], ct['obs_rate'], 'o-', color='#7c3aed', label='Axiom')",
        "ax.set(xlabel='mean predicted P(RTO)', ylabel='observed RTO rate', title='Reliability')",
        "ax.legend(fontsize=9)",
        "fig.tight_layout()",
        "ct.round(3)",
    ),
    md(
        "## 5. Is the machine learning worth it?",
        "",
        "The comparison that matters is not against \"do nothing\" — it is against what a competent",
        "risk analyst ships without any ML. Identical features, identical splits, isotonic",
        "calibration on validation for every contender, and each gets its own validation-fitted",
        "threshold. The gaps carry **paired** bootstrap intervals.",
    ),
    code(
        "ablation = compare(bundle, model, cm, n_boot=300)",
        "ablation[['model', 'tau_val_fitted', 'pr_auc', 'roc_auc', 'brier', 'cost_per_1k']].round(4)",
    ),
    code(
        "for r in ablation.itertuples():",
        "    lo = getattr(r, 'champion_gain_pr_auc_lo', np.nan)",
        "    if not isinstance(lo, float) or not np.isfinite(lo):",
        "        continue",
        "    verdict = 'LightGBM wins' if r.champion_beats_pr_auc else 'NOT SHOWN to be better (interval spans 0)'",
        "    print(f'vs {r.model:<24} PR-AUC gain [{lo:+.4f}, {r.champion_gain_pr_auc_hi:+.4f}] -> {verdict}')",
    ),
    md(
        "Where the interval spans zero we have **not** demonstrated an advantage, and we say so",
        "rather than quoting the point estimate. LightGBM stays in the pipeline for the",
        "categorical and interaction structure the ring/velocity features carry, and because SHAP",
        "gives the per-order attributions the agent narrates — not on a claim of superior",
        "accuracy on this dataset.",
    ),
    md(
        "## 6. Who pays for the false positives?",
        "",
        "Track 2 is graded on false-positive cost, and a portfolio-level rate hides the part that",
        "matters: friction does not land evenly on customers.",
    ),
    code(
        "slices = slice_report(test, proba, thresholds.tau_star, cm)",
        "slices[['dimension', 'slice', 'n', 'rto_rate', 'recall', 'precision',",
        "        'fp_rate_on_good', 'fp_cost']].round(3)",
    ),
    code(
        "print('Good customers most likely to be challenged:')",
        "display(worst_slices(slices).round(3))",
        "print('\\nUnevenness of the false-positive burden (max/min within each dimension):')",
        "disparity(slices).round(2)",
    ),
    md(
        "The response to a flag is **dynamic friction, never a block** — precisely because of the",
        "table above. A mis-flagged customer is asked to confirm an address or offered a prepaid",
        "link and clears themselves in one step. The disparity is a real cost we own and monitor.",
        "No protected attribute is used: city tier, order value and category are commercial",
        "variables, so this is an operational harm audit rather than a legal fairness audit.",
    ),
    md(
        "## 7. Band economics",
        "",
        "GREEN / AMBER / RED are not taste. Each band's action has a friction cost and an",
        "efficacy; setting the expected costs equal gives the cut-points in closed form. The",
        "efficacies are assumptions, so they are swept rather than asserted.",
    ),
    code(
        "derived = band_policy_cost(y, proba, value, thresholds.tau_low, thresholds.tau_high, cm)",
        "legacy = band_policy_cost(y, proba, value, 0.15, 0.45, cm)",
        "",
        "bands = pd.DataFrame([{'policy': 'derived from the cost model', **derived},",
        "                      {'policy': 'previously hard-coded 0.15/0.45', **legacy}]).set_index('policy')",
        "print(f\"deriving the cut-points is worth Rs {legacy['cost_per_1k'] - derived['cost_per_1k']:,.0f} per 1,000 orders\")",
        "bands[['cost_per_1k', 'n_green', 'n_amber', 'n_red',",
        "       'green_rto_rate', 'amber_rto_rate', 'red_rto_rate']].round(3)",
    ),
    code(
        "sweep = sensitivity(value, cm)",
        "print(f\"tau_low  spans {sweep['tau_low'].min():.2f}-{sweep['tau_low'].max():.2f}\")",
        "print(f\"tau_high spans {sweep['tau_high'].min():.2f}-{sweep['tau_high'].max():.2f}\")",
        "print('The amber cut-point is dominated by the assumed step-up efficacy — a merchant')",
        "print('should measure that on their own traffic and re-derive. The formula ships, not the constant.')",
        "sweep.round(3)",
    ),
    md(
        "## 8. What this is not",
        "",
        "- The world is **synthetic**. The metrics are real and measured on held-out data, but the",
        "  data-generating process is ours. On real orders the model must be retrained and",
        "  recalibrated before any rupee claim is repeated.",
        "- The cost model and the action efficacies are **assumptions**, stated and swept, not audited.",
        "- LightGBM is **not shown** to beat logistic regression here.",
        "- Recall at the frozen threshold is roughly a third. This is a ranker that routes",
        "  attention under a bounded, reversible, human-overridable action set — not an oracle",
        "  that stops fraud.",
        "",
        "Every number above is regenerated by `python -m src.model.full_report`, which also",
        "rewrites `docs/evaluation.md`.",
    ),
]

NOTEBOOK = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(NOTEBOOK, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({len(CELLS)} cells)")
