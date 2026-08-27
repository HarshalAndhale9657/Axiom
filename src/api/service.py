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
from src.model.train import load
from src.rag.policy import PolicyRetriever
from src.rules.decision_core import DecisionConfig, decide_from_row

_ORDER_FIELDS = ["payment_method", "order_value", "product_category", "city", "city_tier",
                 "pincode", "distance_km", "address_text", "address_completeness",
                 "is_first_time_buyer", "account_age_days", "phone_verified"]


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
        self.config = DecisionConfig()
        self._provider = provider

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

    def metrics(self) -> dict:
        """Honest evaluation numbers (BMR cost story) for the dashboard header."""
        rep = report(self.queue["is_rto"].to_numpy(), self._proba,
                     self.queue["order_value"].to_numpy(), self.queue["is_cod"].to_numpy(),
                     self.cost)
        rep.pop("_curve", None)
        return rep

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
        return {"points": points, "tau_star": rep["tau_star"],
                "block_all_cod_cost": rep["baselines"]["block_all_cod_cost"],
                "approve_all_cost": rep["baselines"]["approve_all_cost"], "n": rep["n"]}

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
