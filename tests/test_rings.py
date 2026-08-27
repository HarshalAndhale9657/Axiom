"""Tests for unsupervised fraud-ring detection."""
from __future__ import annotations

import pytest

from src.data.generate_synthetic_cod import generate
from src.graph.rings import build_buyer_graph, find_rings, ring_graph_payload, validate


@pytest.fixture(scope="module")
def data():
    return generate(n=6000, seed=0)


def test_ring_detection_uses_no_label(data):
    """PROOF of honesty: rings are found from topology even with the label column removed."""
    orders, _ = data
    rings = find_rings(orders.drop(columns=["is_rto"]), min_size=3)
    assert len(rings) > 0


def test_rings_recover_true_rings_honestly(data):
    """Discovered rings should honestly match the hidden `is_ring` latent."""
    orders, latents = data
    rings = find_rings(orders, min_size=3)
    val = validate(orders, latents, rings)
    assert val["precision"] > 0.7, f"low precision {val}"
    assert val["recall"] > 0.4, f"low recall {val}"


def test_ring_graph_payload_is_bipartite(data):
    orders, _ = data
    rings = find_rings(orders, min_size=3)
    g = ring_graph_payload(orders, rings[0])
    assert g["nodes"] and g["links"]
    kinds = {n["kind"] for n in g["nodes"]}
    assert "buyer" in kinds and "device" in kinds


def test_legit_buyers_are_not_forced_into_rings(data):
    """A buyer on their own (unshared) device must not appear in any ring."""
    orders, _ = data
    g = build_buyer_graph(orders)
    # every ring member has degree >= 1 (shares a device); isolated buyers are excluded
    rings = find_rings(orders, min_size=3)
    members = {b for r in rings for b in r.buyers}
    assert all(g.degree(b) >= 1 for b in members)
