"""The evidence pack must stay internally consistent and JSON-clean.

``docs/evaluation.md`` is generated rather than written, so these tests are what stands
between us and a published document that quietly contradicts itself.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.data.generate_synthetic_cod import generate
from src.features.build_features import build_features
from src.model.full_report import _clean, render_markdown
from src.model.threshold import fit_thresholds
from src.model.train import save, train_model


@pytest.fixture(scope="module")
def pack(tmp_path_factory):
    """A small but complete evidence pack, built through the real code path."""
    from src.model.full_report import build

    tmp = tmp_path_factory.mktemp("pack")
    orders, _ = generate(n=6000, seed=0)
    orders_path = tmp / "orders.csv"
    orders.to_csv(orders_path, index=False)

    bundle = build_features(orders)
    result = train_model(bundle, params={"n_estimators": 150, "learning_rate": 0.05})
    save(result, tmp)
    X_val, y_val = bundle.split("val")
    from src.model.threshold import save_thresholds

    save_thresholds(fit_thresholds(y_val.to_numpy(), result.model.predict_proba(X_val),
                                   bundle.frame.loc[X_val.index, "order_value"].to_numpy()),
                    tmp)

    monkey_cwd = tmp / "out"
    monkey_cwd.mkdir()
    import os

    prev = os.getcwd()
    os.chdir(monkey_cwd)
    try:
        rep = build(str(orders_path), str(tmp), n_boot=40, lag_tax=False)
    finally:
        os.chdir(prev)
    return rep


def test_pack_is_json_serialisable(pack):
    """Anything with a NaN or a numpy scalar in it breaks the API and the notebook."""
    text = json.dumps(_clean(pack))
    assert "NaN" not in text and "Infinity" not in text
    assert json.loads(text)["headline"]["tau_source"] == "val_frozen"


def test_headline_threshold_matches_the_frozen_artifact(pack):
    assert pack["headline"]["tau_star"] == pack["thresholds"]["tau_star"]
    assert pack["thresholds"]["fitted_on"] == "val"


def test_shipped_cost_is_never_better_than_the_oracle(pack):
    """If it were, we would be reporting a threshold tuned on test after all."""
    assert pack["headline"]["optimism"]["cost_gap"] >= 0


def test_model_beats_both_naive_baselines(pack):
    money = pack["headline"]["money"]
    assert money["model_cost_per_1k"] < money["approve_all_cost_per_1k"]
    assert money["model_cost_per_1k"] < money["block_all_cod_cost_per_1k"]


def test_the_leaked_variant_really_is_inflated(pack):
    """The leakage exhibit is only honest if the leak is genuine."""
    leak = pack["leakage_tax"]
    assert leak["leaked_INVALID"]["roc_auc"] > leak["honest"]["roc_auc"] + 0.1


def test_derived_bands_are_not_more_expensive_than_the_old_magic_numbers(pack):
    band = pack["band_economics"]
    assert band["derived"]["cost_per_1k"] <= band["legacy_hardcoded"]["cost_per_1k"]
    assert band["saving_per_1k_vs_hardcoded"] >= 0


def test_ablation_includes_a_real_opponent(pack):
    models = set(pd.DataFrame(pack["ablation"])["model"])
    assert {"rules-only scorecard", "logistic regression", "LightGBM (Axiom)"} <= models


def test_failure_modes_name_a_worst_slice(pack):
    worst = pd.DataFrame(pack["failure_modes"]["worst"])
    assert len(worst) >= 1
    assert (worst["fp_rate_on_good"] >= 0).all()


def test_markdown_renders_every_section_and_no_placeholders(pack):
    md = render_markdown(pack)
    for heading in ("Why accuracy is not on this page",
                    "The operating point is chosen on validation",
                    "The money story",
                    "Is the machine learning worth it?",
                    "Which good customers pay for the false positives?",
                    "Two leakage taxes we paid",
                    "Where the band cut-points come from",
                    "Known limitations"):
        assert heading in md, heading
    assert "TBD" not in md and "TODO" not in md
    assert "nan" not in md.lower().replace("finance", "")


def test_markdown_quotes_the_frozen_threshold_not_the_oracle(pack):
    md = render_markdown(pack)
    assert f"{pack['thresholds']['tau_star']:.3f}" in md
    assert "not reportable" in md            # the oracle row is labelled as such


def test_report_never_claims_accuracy(pack):
    md = render_markdown(pack).lower()
    assert "accuracy" in md                  # it is discussed...
    assert "accuracy of" not in md           # ...but never quoted as a result
    assert not any(line.strip().startswith("| accuracy")
                   for line in md.splitlines())


def test_clean_drops_private_keys_and_nonfinite_values():
    dirty = {"_curve": pd.DataFrame({"a": [1]}), "x": np.float64("nan"),
             "y": np.int64(3), "z": [np.float64("inf"), 1.5]}
    assert _clean(dirty) == {"x": None, "y": 3, "z": [None, 1.5]}
