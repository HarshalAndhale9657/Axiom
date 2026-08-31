"""RiskEngine — the end-to-end orchestrator behind the Axiom API.

Wires the whole brain together: features -> calibrated score -> anomaly -> SHAP -> decision
core -> (amber) bounded agent -> immutable audit. Loads everything once; the "incoming
order queue" for the demo is the held-out test split (orders the model never trained on).

The core decision (score + rules + band + action) is instant. The LLM agent runs only on
demand (``investigate``) for borderline cases, keeping the queue fast and free-tier-friendly.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from src.agent.investigate import investigate as run_investigation
from src.agent.llm import get_provider
from src.agent.tools import OrderContext
from src.audit.store import AuditStore
from src.features.build_features import build_features
from src.model.anomaly import AnomalyDetector
from src.model.evaluation import CostModel, cost_curve, report
from src.model.explain import RTOExplainer
from src.model.threshold import band_policy_cost, load_thresholds, sensitivity
from src.model.train import load
from src.rag.policy import PolicyRetriever
from src.rules.decision_core import DecisionConfig, decide_from_row
from src.util import to_jsonable

_ORDER_FIELDS = ["payment_method", "order_value", "product_category", "city", "city_tier",
                 "pincode", "distance_km", "address_text", "address_completeness",
                 "is_first_time_buyer", "account_age_days", "phone_verified"]

# Disclosed with every batch result — the honest basis of the ₹ figures.
_BATCH_BASIS = {"basis": ("Rupees measured on the labelled held-out test batch. Assumes an "
                          "applied friction (verify / prepaid / part-pay) prevents that return.")}


def _py(v):
    """numpy -> native python for JSON."""
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    return v


class RiskEngine:
    def __init__(self, orders: pd.DataFrame | None = None,
                 data_path: str = "data/cod_orders.csv", model_dir: str = "models",
                 audit_path: str = "audit.sqlite", provider=None, queue_limit: int = 200) -> None:
        self.orders_raw = orders if orders is not None else pd.read_csv(data_path)
        self._latents_path = (str(Path(data_path).with_name(Path(data_path).stem + "_latents.csv"))
                              if orders is None else None)
        self.bundle = build_features(self.orders_raw)
        self.feature_cols = self.bundle.feature_columns
        self.model = load(model_dir)["model"]
        self.model_version = self._version(Path(model_dir) / "axiom_rto_model.joblib")

        train = self.bundle.frame[self.bundle.frame["split"] == "train"]
        self.anomaly = AnomalyDetector(self.feature_cols, self.bundle.categorical_columns).fit(train)
        self.explainer = RTOExplainer(self.model)
        self.retriever = PolicyRetriever()
        self.audit = AuditStore(audit_path)
        self.cost = CostModel()
        # The operating point comes from models/thresholds.json — fitted on the validation
        # split at train time and frozen. If it is missing we fall back to the module
        # defaults and say so, rather than silently inventing cut-points.
        self.thresholds = load_thresholds(model_dir)
        self.config = (DecisionConfig(tau_low=self.thresholds.tau_low,
                                      tau_high=self.thresholds.tau_high)
                       if self.thresholds else DecisionConfig())
        self._provider = provider
        self._metrics_cache: dict | None = None

        self.queue = self.bundle.frame[self.bundle.frame["split"] == "test"].reset_index(drop=True)
        self._proba = self.model.predict_proba(self.queue[self.feature_cols])
        self._anom = self.anomaly.anomaly_score(self.queue)
        self._idx = {str(oid): i for i, oid in enumerate(self.queue["order_id"])}
        self.queue_limit = queue_limit

    @staticmethod
    def _version(path: Path) -> str:
        try:
            return "lgbm-" + hashlib.sha256(path.read_bytes()).hexdigest()[:10]
        except OSError:
            return "lgbm-dev"

    def provider(self):
        return self._provider or get_provider()

    def _locate(self, order_id: str) -> int:
        i = self._idx.get(str(order_id))
        if i is None:
            raise KeyError(order_id)
        return i

    def _core(self, i: int, explanation=None):
        return decide_from_row(self.queue.iloc[i], risk_score=float(self._proba[i]),
                               anomaly_score=float(self._anom[i]), explanation=explanation,
                               config=self.config)

    # ---- API surface ----------------------------------------------------------------
    def queue_view(self, limit: int | None = None) -> list[dict]:
        """Fast queue (no SHAP, no LLM): core band + action + rupee-at-risk per order."""
        limit = limit or self.queue_limit
        rows = []
        for i in range(min(limit, len(self.queue))):
            row = self.queue.iloc[i]
            d = self._core(i)
            rows.append({
                "order_id": str(row["order_id"]),
                "risk_score": round(float(self._proba[i]), 4),
                "anomaly_score": round(float(self._anom[i]), 4),
                "band": d.band, "action": d.action, "requires_human": d.requires_human,
                "order_value": float(row["order_value"]),
                "rupee_at_risk": round(float(self.cost.c_fn(np.array([row["order_value"]]))[0])),
                "payment_method": str(row["payment_method"]),
            })
        return rows

    def assess(self, order_id: str) -> dict:
        """Full case detail: score + SHAP factors + core decision + order context."""
        i = self._locate(order_id)
        row = self.queue.iloc[i]
        explanation = self.explainer.explain_row(self.queue[self.feature_cols].iloc[[i]])
        d = self._core(i, explanation=explanation)
        return {
            "order_id": str(row["order_id"]),
            "risk_score": round(float(self._proba[i]), 4),
            "anomaly_score": round(float(self._anom[i]), 4),
            "decision": d.as_dict(),
            "order": {k: _py(row[k]) for k in _ORDER_FIELDS},
        }

    def investigate(self, order_id: str) -> dict:
        """Run the bounded agent and persist the decision to the immutable audit trail."""
        i = self._locate(order_id)
        row = self.queue.iloc[i]
        ctx = OrderContext.from_feature_row(row, float(self._proba[i]), float(self._anom[i]))
        dec = run_investigation(ctx, self.retriever, provider=self.provider(), config=self.config)
        decision_id = self.audit.log_decision(
            order_id=str(row["order_id"]), risk_score=float(self._proba[i]),
            anomaly_score=float(self._anom[i]), band=self._core(i).band, action=dec.action,
            reason=dec.rationale, confidence=dec.confidence, requires_human=dec.requires_human,
            source=dec.source, model_version=self.model_version, detail=dec.as_dict())
        return {"decision_id": decision_id, **dec.as_dict()}

    def run_batch(self, config=None, *, now_hour: int | None = None,
                  scan_limit: int | None = None) -> dict:
        """Autonomously work the AMBER queue with real stopping rules; report honest ₹ economics.

        Every processed order is audited. Rupees are measured post-hoc on the labelled held-out
        test batch: gross recovered (prevented-RTO cost on interventions that would have RTO'd),
        the friction cost incurred on genuine customers, and the resulting net.
        """
        from src.agent.batch import (
            BatchConfig,
            BatchState,
            in_quiet_hours,
            is_intervention,
            recovered_and_cost,
            stop_reason,
            update_state,
        )

        config = config or BatchConfig()
        zero = {"stopped": True, "processed": 0, "amber_seen": 0, "interventions": 0,
                "rto_caught": 0, "good_frictioned": 0, "rto_missed": 0, "recovered_gross": 0,
                "friction_cost": 0, "net_recovered": 0, "missed_cost": 0, "actions": []}
        if in_quiet_hours(now_hour, config.quiet_hours):
            return {**zero, "stop_reason": f"quiet hours {config.quiet_hours} — no run", **_BATCH_BASIS}

        state = BatchState()
        actions: list[dict] = []
        recovered_gross = friction_cost = missed_cost = 0.0
        rto_caught = good_frictioned = rto_missed = amber_seen = 0
        scan = min(scan_limit or len(self.queue), len(self.queue))
        reason = None
        for i in range(scan):
            if self._core(i).band != "amber":
                continue
            reason = stop_reason(state, config)
            if reason:
                break
            amber_seen += 1
            row = self.queue.iloc[i]
            value, is_rto = float(row["order_value"]), int(row["is_rto"])
            ctx = OrderContext.from_feature_row(row, float(self._proba[i]), float(self._anom[i]))
            dec = run_investigation(ctx, self.retriever, provider=self.provider(),
                                    config=self.config, verifier=None)  # autonomous throughput
            c_fn = float(self.cost.c_fn(np.array([value]))[0])
            c_fp = float(self.cost.c_fp(np.array([value]))[0])
            rec, fcost = recovered_and_cost(dec.action, is_rto, c_fn, c_fp)
            recovered_gross += rec
            friction_cost += fcost
            intervened = is_intervention(dec.action)
            if intervened and is_rto:
                rto_caught += 1
            elif intervened:
                good_frictioned += 1
            elif is_rto:
                rto_missed += 1
                missed_cost += c_fn
            decision_id = self.audit.log_decision(
                order_id=str(row["order_id"]), risk_score=float(self._proba[i]),
                anomaly_score=float(self._anom[i]), band="amber", action=dec.action,
                reason=dec.rationale, confidence=dec.confidence,
                requires_human=dec.requires_human, source=f"batch:{dec.source}",
                model_version=self.model_version, detail=dec.as_dict())
            actions.append({
                "order_id": str(row["order_id"]), "action": dec.action, "order_value": round(value),
                "is_rto": is_rto, "intervened": intervened, "recovered": round(rec),
                "friction_cost": round(fcost), "source": dec.source, "decision_id": decision_id})
            update_state(state, value, config)
        reason = reason or stop_reason(state, config) or "scanned the entire queue"
        gross, friction = round(recovered_gross), round(friction_cost)   # reconcile: net = gross - friction
        return {
            "stopped": True, "stop_reason": reason, "processed": state.processed,
            "amber_seen": amber_seen, "interventions": rto_caught + good_frictioned,
            "rto_caught": rto_caught, "good_frictioned": good_frictioned, "rto_missed": rto_missed,
            "recovered_gross": gross, "friction_cost": friction,
            "net_recovered": gross - friction, "missed_cost": round(missed_cost),
            "actions": actions, **_BATCH_BASIS,
        }

    def ask(self, order_id: str, question: str) -> dict:
        """Grounded analyst copilot — answer a question using ONLY this case's record + policy."""
        from src.agent.copilot import answer as copilot_answer

        detail = self.assess(order_id)                    # score + SHAP + core decision + order
        decision = detail["decision"]
        rag_query = (f"{question} pincode {detail['order'].get('pincode')} address quality "
                     f"buyer history {decision.get('action')} step-up verification part-pay")
        policy = self.retriever.snippets(rag_query, k=4)
        return copilot_answer(
            question, order=detail["order"], risk_score=detail["risk_score"],
            anomaly_score=detail["anomaly_score"], band=decision["band"], decision=decision,
            factors=decision.get("top_factors", []), policy=policy, provider=self.provider())

    def execute(self, order_id: str, action: str | None = None) -> dict:
        """Run the bounded action for REAL (Razorpay test-mode link) and audit it."""
        from src.actions.razorpay_actuator import create_partial_link, create_prepaid_link

        i = self._locate(order_id)
        row = self.queue.iloc[i]
        core = self._core(i)
        action = action or core.action
        amount = float(row["order_value"])
        score = float(self._proba[i])
        if action == "convert_cod_to_prepaid":
            res = create_prepaid_link(str(row["order_id"]), amount, core.band, score)
        elif action == "part_pay_cod":
            deposit = min(amount, max(50.0, float(self.cost.c_fn(np.array([amount]))[0]) * score))
            res = create_partial_link(str(row["order_id"]), amount, deposit, core.band, score)
        else:
            return {"executed": False, "action": action,
                    "message": "This action stays in-platform (no external payment link)."}
        decision_id = self.audit.log_decision(
            order_id=str(row["order_id"]), risk_score=score, anomaly_score=float(self._anom[i]),
            band=core.band, action=action, reason="Executed via Razorpay test-mode",
            confidence=core.confidence, requires_human=False, source="actuator",
            model_version=self.model_version, detail={"actuation": res})
        return {"executed": True, "decision_id": decision_id, **res}

    def override(self, decision_id: int, reviewer: str, to_action: str, reason: str) -> dict:
        """Human-in-the-loop override — logged as a new immutable row (before/after preserved)."""
        decision = self.audit.get_decision(decision_id)
        if decision is None:
            raise KeyError(decision_id)
        override_id = self.audit.log_override(
            decision_id=decision_id, reviewer=reviewer, from_action=decision["action"],
            to_action=to_action, reason=reason)
        return {"override_id": override_id, "decision_id": decision_id,
                "from_action": decision["action"], "to_action": to_action, "reviewer": reviewer}

    def audit_log(self, limit: int = 100) -> list[dict]:
        return self.audit.list_decisions(limit)

    def metrics(self, n_boot: int = 500) -> dict:
        """Honest evaluation numbers (BMR cost story) for the dashboard header.

        Scored at the **frozen** threshold from ``models/thresholds.json`` (fitted on the
        validation split), with bootstrap intervals and the optimism gap against the
        test-optimal oracle we deliberately do not use. Cached: the numbers are a property
        of a fixed model on a fixed split, so recomputing them per request would only burn
        CPU.
        """
        if self._metrics_cache is not None:
            return self._metrics_cache
        rep = report(self.queue["is_rto"].to_numpy(), self._proba,
                     self.queue["order_value"].to_numpy(), self.queue["is_cod"].to_numpy(),
                     self.cost, tau=self.thresholds.tau_star if self.thresholds else None,
                     n_boot=n_boot)
        rep.pop("_curve", None)
        rep["thresholds"] = self.thresholds.as_dict() if self.thresholds else None
        rep["band_policy"] = band_policy_cost(
            self.queue["is_rto"].to_numpy(), self._proba,
            self.queue["order_value"].to_numpy(),
            self.config.tau_low, self.config.tau_high, self.cost)
        self._metrics_cache = to_jsonable(rep)
        return self._metrics_cache

    def threshold_report(self) -> dict:
        """Where the cut-points come from, and how far they move if our assumptions do."""
        value = self.queue["order_value"].to_numpy()
        sweep = sensitivity(value)
        band = self.metrics()["band_policy"]
        # What the previously hard-coded 0.15/0.45 band would have cost on the same split —
        # the price of the magic numbers we removed.
        legacy = band_policy_cost(self.queue["is_rto"].to_numpy(), self._proba, value,
                                  0.15, 0.45, self.cost)
        return to_jsonable({
            "thresholds": self.thresholds.as_dict() if self.thresholds else None,
            "band_policy": band,
            "legacy_hardcoded_band_policy": legacy,
            "saving_per_1k_vs_hardcoded": legacy["cost_per_1k"] - band["cost_per_1k"],
            "sensitivity": sweep.to_dict(orient="records"),
            "note": ("Band cut-points are derived in closed form from the cost model and the "
                     "assumed efficacy of each bounded action; the sensitivity grid shows how "
                     "far they move across the plausible range of those assumptions."),
        })

    def baseline_report(self, n_boot: int = 300) -> dict:
        """Is the ML worth it? LightGBM vs a scorecard vs logistic regression."""
        if getattr(self, "_baselines_cache", None):
            return self._baselines_cache
        from src.model.baselines import compare

        table = compare(self.bundle, self.model, self.cost, n_boot=n_boot)
        self._baselines_cache = to_jsonable({
            "rows": table,
            "note": ("Identical features and splits for every contender; each is isotonically "
                     "calibrated on validation and given its own validation-fitted rupee "
                     "threshold. Gaps carry paired bootstrap intervals."),
        })
        return self._baselines_cache

    def slice_report(self) -> dict:
        """Failure-mode matrix: which good customers absorb the false positives."""
        if getattr(self, "_slices_cache", None):
            return self._slices_cache
        from src.model.slices import disparity, slice_report, worst_slices

        tau = self.thresholds.tau_star if self.thresholds else self.config.tau_high
        rep = slice_report(self.queue, self._proba, tau, self.cost)
        self._slices_cache = to_jsonable({
            "tau": tau,
            "slices": rep,
            "worst": worst_slices(rep),
            "disparity": disparity(rep),
            "note": ("Operational harm audit, not a legal fairness audit: the model uses no "
                     "protected attribute. 'fp_rate_on_good' is the share of genuine customers "
                     "in a slice that were put through friction."),
        })
        return self._slices_cache

    def model_meta(self) -> dict:
        """Provenance and reproducibility card for the served artifact."""
        meta = self.bundle.meta
        return to_jsonable({
            "model_version": self.model_version,
            "algorithm": "LightGBM (binary) + isotonic calibration fitted on validation",
            "n_features": len(self.feature_cols),
            "features": self.feature_cols,
            "data_provenance": "synthetic — causal COD/RTO generator (seed 42), disclosed",
            "n_orders": meta.get("n_total"),
            "split": {"policy": "chronological (never shuffled)", **meta.get("split_sizes", {})},
            "train_prior_rto": meta.get("train_prior"),
            "test_rto_rate_natural": meta.get("test_rto_rate"),
            "outcome_lag_days": meta.get("outcome_lag_days"),
            "target_encoding_alpha": meta.get("alpha"),
            "thresholds": self.thresholds.as_dict() if self.thresholds else None,
            "protected_attributes_used": [],
            "pii_used": [],
            "intended_use": "Ranking COD orders for RTO risk to select a bounded, defensive, "
                            "reversible action. Decision support with human override.",
            "out_of_scope": ["credit decisions", "permanent bans", "any offensive use",
                             "deployment on real orders without recalibration on real data"],
        })

    def cost_curve_points(self, n_grid: int = 60) -> dict:
        """The BMR cost curve as plottable points, for the interactive threshold slider."""
        curve = cost_curve(self.queue["is_rto"].to_numpy(), self._proba,
                           self.queue["order_value"].to_numpy(), self.cost, n_grid=n_grid)
        rep = self.metrics()
        points = [
            {"threshold": round(float(r.threshold), 4), "cost": round(float(r.cost)),
             "precision": None if r.precision != r.precision else round(float(r.precision), 4),
             "recall": round(float(r.recall), 4), "flag_rate": round(float(r.flag_rate), 4),
             "tp": int(r.tp), "fp": int(r.fp), "fn": int(r.fn), "tn": int(r.tn),
             "fp_cost": round(float(r.fp_cost)), "fn_cost": round(float(r.fn_cost))}
            for r in curve.itertuples()
        ]
        return to_jsonable({"points": points, "tau_star": rep["tau_star"],
                "tau_source": rep.get("tau_source"),
                "tau_low": self.config.tau_low, "tau_high": self.config.tau_high,
                "oracle_tau": rep["oracle"]["tau"], "oracle_cost": rep["oracle"]["cost"],
                "optimism_cost_gap_per_1k": rep["optimism"]["cost_gap_per_1k"],
                "block_all_cod_cost": rep["baselines"]["block_all_cod_cost"],
                "approve_all_cost": rep["baselines"]["approve_all_cost"], "n": rep["n"]})

    def leakage_report(self) -> dict:
        """The 'leakage tax': Axiom's honest metrics vs a DELIBERATELY leaked model (INVALID).

        Proves we can trivially manufacture the ~0.99 AUC that public RTO models brag about —
        and chose the true, lower number instead. Trains the leaky model once and caches it.
        """
        if getattr(self, "_leakage", None):
            return self._leakage
        from sklearn.metrics import average_precision_score, roc_auc_score

        from src.model.train import train_model

        y = self.queue["is_rto"].to_numpy()
        honest = {"roc_auc": round(float(roc_auc_score(y, self._proba)), 4),
                  "pr_auc": round(float(average_precision_score(y, self._proba)), 4),
                  "prevalence": round(float(y.mean()), 4)}

        leaky_bundle = build_features(self.orders_raw, leak=True)  # same split, test untouched
        leaky = train_model(leaky_bundle, params={"n_estimators": 300, "learning_rate": 0.05})
        lt = leaky_bundle.frame[leaky_bundle.frame["split"] == "test"]
        lp = leaky.model.predict_proba(lt[leaky_bundle.feature_columns])
        ly = lt["is_rto"].to_numpy()
        leaked = {"roc_auc": round(float(roc_auc_score(ly, lp)), 4),
                  "pr_auc": round(float(average_precision_score(ly, lp)), 4),
                  "prevalence": round(float(ly.mean()), 4)}
        self._leakage = {"honest": honest, "leaky": leaked}
        return self._leakage

    def rings(self) -> dict:
        """Unsupervised fraud rings (shared-device graph) + honest validation vs the hidden flag."""
        if getattr(self, "_rings_cache", None):
            return self._rings_cache
        from src.graph.rings import find_rings, validate

        ring_objs = find_rings(self.orders_raw, min_size=3)
        self._rings_by_id = {r.ring_id: r for r in ring_objs}
        val: dict = {}
        if self._latents_path and Path(self._latents_path).exists():
            latents = pd.read_csv(self._latents_path)
            val = validate(self.orders_raw, latents, ring_objs)
        self._rings_cache = {"validation": val, "rings": [r.summary() for r in ring_objs[:40]]}
        return self._rings_cache

    def ring_graph(self, ring_id: str) -> dict:
        from src.graph.rings import ring_graph_payload

        self.rings()
        ring = getattr(self, "_rings_by_id", {}).get(ring_id)
        if ring is None:
            raise KeyError(ring_id)
        return ring_graph_payload(self.orders_raw, ring)
