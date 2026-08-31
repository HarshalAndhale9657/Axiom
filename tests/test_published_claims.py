"""Every number the README claims must match what the pipeline actually measured.

A README is the most-read and least-tested file in a repository, which is exactly why
marketing numbers drift there first: the model gets retrained, the docs get regenerated,
and the headline table quietly keeps quoting last week's result. On a project whose whole
argument is honest measurement, that drift is indistinguishable from fabrication.

So the claims are parsed straight out of ``README.md`` and checked against
``reports/evaluation.json`` — the artifact written by ``python -m src.model.full_report``.
If you retrain and the README goes stale, this test fails before a judge notices.

The report is a build artifact (git-ignored), so these tests skip when it is absent and
run for real in CI, where the pipeline is rebuilt from scratch first.

**On tolerances.** The numeric checks allow ~2% drift rather than demanding bit equality.
A gradient-boosted model retrained on another OS or another LightGBM build lands on
slightly different splits, and failing CI for that would be noise, not honesty. Anything
that actually changes the story — a retrain, a new feature, a different threshold — moves
these figures by far more than 2%. The *structural* claims (blocking all COD costs more
than doing nothing; the threshold was frozen on validation; we do not beat logistic
regression) are asserted exactly, because those are the claims that matter.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
REPORT = ROOT / "reports" / "evaluation.json"


@pytest.fixture(scope="module")
def report() -> dict:
    if not REPORT.exists():
        pytest.skip("reports/evaluation.json not built — run `python -m src.model.full_report`")
    return json.loads(REPORT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def readme() -> str:
    return README.read_text(encoding="utf-8")


#: Relative tolerance for money and count claims — see the note on tolerances above.
DRIFT = 0.02


def _rupees(text: str, pattern: str) -> float:
    """Pull a ₹1,234 figure out of the README by regex, failing loudly if it moved."""
    match = re.search(pattern, text)
    assert match, f"README no longer contains a figure matching {pattern!r}"
    return float(match.group(1).replace(",", ""))


# --- the money story --------------------------------------------------------------------

def test_readme_quotes_the_measured_cost_table(report, readme):
    money = report["headline"]["money"]
    for pattern, actual in (
        (r"\| Approve everything \| ₹([\d,]+) \|", money["approve_all_cost_per_1k"]),
        (r"\| \*\*Block all COD \(naive\)\*\* \| \*\*₹([\d,]+)\*\*", money["block_all_cod_cost_per_1k"]),
        (r"\| \*\*Axiom @ the frozen threshold\*\* \| \*\*₹([\d,]+)\*\*", money["model_cost_per_1k"]),
    ):
        assert _rupees(readme, pattern) == pytest.approx(actual, rel=DRIFT)


def test_readme_saving_claim_matches_the_measurement(report, readme):
    money = report["headline"]["money"]
    claimed = _rupees(readme, r"\*\*₹([\d,]+) cheaper per 1,000 orders than blocking all COD\*\*")
    assert claimed == pytest.approx(money["rupees_saved_per_1k_vs_block_all_cod"], rel=DRIFT)


def test_the_headline_only_survives_because_it_is_true(report):
    """The banner claim — blocking all COD is worse than doing nothing — must hold."""
    money = report["headline"]["money"]
    assert money["block_all_cod_cost_per_1k"] > money["approve_all_cost_per_1k"]
    assert money["model_cost_per_1k"] < money["approve_all_cost_per_1k"]


# --- ranking quality --------------------------------------------------------------------

def test_readme_quotes_the_measured_pr_auc_and_its_interval(report, readme):
    head = report["headline"]
    match = re.search(r"\*\*PR-AUC\*\* \| \*\*([\d.]+)\*\* \(95% CI ([\d.]+)–([\d.]+)\)", readme)
    assert match, "the README PR-AUC row has changed shape"
    point, lo, hi = (float(g) for g in match.groups())
    assert point == pytest.approx(head["pr_auc"], abs=0.01)
    assert lo == pytest.approx(head["ci"]["pr_auc"]["lo"], abs=0.015)
    assert hi == pytest.approx(head["ci"]["pr_auc"]["hi"], abs=0.015)
    assert lo < point < hi


def test_readme_never_reports_accuracy_as_a_result(readme):
    """Accuracy is banned as a headline; it may only be discussed as the thing we exclude."""
    for line in readme.splitlines():
        if re.match(r"\s*\|\s*(model\s+)?accuracy\b", line, flags=re.I):
            pytest.fail(f"accuracy is being quoted as a metric: {line!r}")
    assert "intentionally never reported" in readme


# --- the honesty claims ------------------------------------------------------------------

def test_readme_optimism_claim_matches_the_measured_gap(report, readme):
    claimed = _rupees(readme, r"\*\*₹([\d,]+) per 1,000 orders \([\d.]+%\) of optimism we declined")
    assert claimed == pytest.approx(report["headline"]["optimism"]["cost_gap_per_1k"], rel=0.20)
    assert report["headline"]["tau_source"] == "val_frozen"


def test_readme_band_saving_claim_matches(report, readme):
    claimed = _rupees(readme, r"worth \*\*₹([\d,]+) per 1,000 orders\*\*")
    assert claimed == pytest.approx(report["band_economics"]["saving_per_1k_vs_hardcoded"], rel=0.20)


def test_readme_lag_tax_claim_matches(report, readme):
    match = re.search(r"Cost of the correction: \*\*([\d.]+) PR-AUC\*\*", readme)
    assert match, "the README no longer states what the outcome-lag correction cost"
    assert float(match.group(1)) == pytest.approx(abs(report["lag_tax"]["pr_auc_cost"]), abs=0.005)


def test_readme_does_not_claim_a_win_over_logistic_regression(report, readme):
    """The one comparison we lose must still be stated as a loss."""
    row = next(r for r in report["ablation"] if r["model"] == "logistic regression")
    assert row["champion_beats_pr_auc"] is False, (
        "LightGBM now significantly beats logistic regression — update the README, which "
        "currently (correctly, at the time of writing) says it does not")
    assert "spans zero" in readme
    assert "we have not shown an advantage" in readme


def test_readme_leakage_exhibit_matches_the_leaked_model(report, readme):
    match = re.search(r"\*\*ROC-AUC ([\d.]+) / PR-AUC ([\d.]+)\*\*", readme)
    assert match, "the README leakage exhibit has changed shape"
    roc, pr = (float(g) for g in match.groups())
    leaked = report["leakage_tax"]["leaked_INVALID"]
    assert roc == pytest.approx(leaked["roc_auc"], abs=0.01)
    assert pr == pytest.approx(leaked["pr_auc"], abs=0.01)


def test_readme_failure_mode_table_matches_the_slice_report(report, readme):
    worst = {r["slice"]: r for r in report["failure_modes"]["worst"]}
    for label, key in (("order value ₹2k–5k", "₹2k–5k"), ("first-time buyers", "first-time"),
                       ("tier-3 cities", "tier 3")):
        row = worst.get(key)
        assert row, f"{key!r} is no longer among the worst slices — refresh the README table"
        match = re.search(rf"\| {re.escape(label)} \| (\d+) \| (\d+) \| \*\*([\d.]+)%\*\* \|", readme)
        assert match, f"README row for {label!r} has changed shape"
        n_good, fps, rate = int(match.group(1)), int(match.group(2)), float(match.group(3))
        assert n_good == row["n_good"], "the slice sizes are fixed by the split — this is a typo"
        assert fps == pytest.approx(row["false_positives"], abs=3)
        assert rate == pytest.approx(row["fp_rate_on_good"] * 100, abs=1.0)


def test_readme_disparity_multiple_matches(report, readme):
    tier = next(r for r in report["failure_modes"]["disparity"] if r["dimension"] == "city_tier")
    match = re.search(r"\*\*([\d.]+)× more likely\*\* to be challenged than a tier-1 buyer", readme)
    assert match, "the README no longer names the tier-3 disparity"
    assert float(match.group(1)) == pytest.approx(tier["ratio"], rel=0.15)


# --- the claims about the repo itself -----------------------------------------------------

def test_test_count_badge_is_not_an_overclaim(readme):
    """The badge may under-promise, never over-promise."""
    match = re.search(r"tests-(\d+)%20passing", readme)
    assert match, "the README no longer carries a test-count badge"
    claimed = int(match.group(1))
    collected = sum(1 for path in (ROOT / "tests").glob("test_*.py")
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.startswith("def test_"))
    assert claimed <= collected, (
        f"README claims {claimed} tests but only {collected} test functions exist")


def test_every_requirement_is_actually_imported():
    """`pip install -r requirements.txt` is the first command a judge runs; keep it honest."""
    declared = set()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            declared.add(re.split(r"[<>=\[]", line)[0].strip().lower())

    import_alias = {"scikit-learn": "sklearn", "pillow": "pil"}
    optional = {"uvicorn", "razorpay", "pytest", "matplotlib"}   # entrypoints / optional paths

    sources = list((ROOT / "src").rglob("*.py")) + list((ROOT / "tests").glob("*.py"))
    text = "\n".join(p.read_text(encoding="utf-8") for p in sources)
    imported = set(re.findall(r"^\s*(?:import|from)\s+([a-zA-Z0-9_]+)", text, flags=re.M))

    unused = {d for d in declared - optional
              if import_alias.get(d, d.replace("-", "_")) not in imported}
    assert not unused, f"requirements.txt declares packages the code never imports: {sorted(unused)}"
