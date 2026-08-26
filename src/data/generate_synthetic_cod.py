"""Synthetic COD order generator for Axiom (Razorpay AI Buildathon, Track 2).

Why this exists
---------------
No clean public dataset exists for Indian Cash-on-Delivery (COD) / Return-to-Origin
(RTO) orders. We therefore *generate* orders whose RTO label is drawn from an explicit
**causal** model of the real drivers (COD vs prepaid, address quality, pincode risk,
buyer reliability, order value, category, distance, first-time buyer, non-serviceable
pincodes, and device/velocity fraud rings). Because we control the ground truth, we can
measure precision/recall and rupee cost **honestly and without leakage**.

Leakage discipline (READ THIS)
------------------------------
The *true* risk drivers -- a pincode's latent RTO tendency, a buyer's latent
reliability, and whether an order belongs to a fraud ring -- are **hidden**: they are
NOT written to the main orders file. Only fields observable at checkout are emitted.
Downstream feature engineering must therefore *estimate* pincode-risk and buyer-history
**out-of-fold** (training rows only). The hidden latents are written to a separate
``*_latents.csv`` for analysis ONLY and must never be used as model features.

Realistic behaviour
--------------------
Per-payment-method intercepts are calibrated so marginal RTO rates land in real Indian
bands: COD ~27%, prepaid ~4% (both configurable). Everything is seeded and reproducible.

Usage
-----
    python -m src.data.generate_synthetic_cod --n 20000 --seed 42
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------------------
# Domain constants (small, hand-curated pools -> reproducible, no external deps)
# --------------------------------------------------------------------------------------

# category -> (rto_logit_effect, log-value mean, log-value sigma). Fashion/footwear are
# the classic high-RTO verticals; grocery/books are low-RTO.
CATEGORIES: dict[str, tuple[float, float, float]] = {
    "fashion": (0.55, 6.60, 0.55),
    "footwear": (0.45, 6.80, 0.50),
    "electronics": (0.10, 7.60, 0.60),
    "home": (0.00, 6.90, 0.55),
    "beauty": (0.05, 6.20, 0.50),
    "grocery": (-0.35, 6.00, 0.45),
    "books": (-0.25, 5.90, 0.50),
}
CATEGORY_NAMES = list(CATEGORIES.keys())
CATEGORY_WEIGHTS = np.array([0.30, 0.14, 0.14, 0.12, 0.11, 0.11, 0.08])  # fashion-heavy

# Fulfilment centres (lat, lon) in metros -> buyer-to-warehouse distance feature.
WAREHOUSES = np.array(
    [
        [12.97, 77.59],  # Bengaluru
        [28.70, 77.10],  # Delhi
        [19.08, 72.88],  # Mumbai
        [22.57, 88.36],  # Kolkata
        [13.08, 80.27],  # Chennai
        [17.39, 78.49],  # Hyderabad
    ]
)

CITIES_BY_TIER: dict[int, list[str]] = {
    1: ["Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Pune"],
    2: ["Jaipur", "Lucknow", "Indore", "Bhopal", "Nagpur", "Coimbatore", "Surat"],
    3: ["Hoshangabad", "Etawah", "Bhagalpur", "Rewa", "Hazaribagh", "Deoghar", "Basti"],
}
STREETS = ["MG Road", "Station Road", "Gandhi Marg", "Ring Road", "Church Street",
           "Nehru Nagar", "Link Road", "Main Bazaar"]
AREAS = ["Sector 14", "Indira Colony", "Green Park", "Shivaji Nagar", "Rajendra Nagar",
         "Model Town", "Vijay Nagar", "Ashok Vihar"]
LANDMARKS = ["near Metro Station", "opp. City Mall", "behind Bus Stand", "next to SBI ATM",
             "near Water Tank", "beside Govt School"]


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _haversine_km(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Great-circle distance in km between two arrays of lat/lon points (degrees)."""
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlmb = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def _bisect_intercept(eta: np.ndarray, target_rate: float, lo: float = -15.0,
                      hi: float = 15.0, iters: int = 60) -> float:
    """Find intercept c such that mean(sigmoid(eta + c)) == target_rate."""
    for _ in range(iters):
        mid = (lo + hi) / 2
        if _sigmoid(eta + mid).mean() < target_rate:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


@dataclass(frozen=True)
class Coefficients:
    """Logit-scale weights of the causal RTO model (the ground-truth generative process)."""
    addr_incomplete: float = 1.8      # x (1 - address_completeness)
    pincode_risk: float = 2.2         # x centred pincode latent risk
    buyer_propensity: float = 2.5     # x centred buyer latent RTO propensity
    non_serviceable: float = 2.5      # x (1 - is_serviceable)
    order_value_z: float = 0.25       # x z(log order value)
    distance_z: float = 0.20          # x z(distance km)
    first_time: float = 0.50          # x is_first_time_buyer
    phone_unverified: float = 0.60    # x (1 - phone_verified)
    ring: float = 2.00                # x is_ring_order (fraud ring)
    noise_sigma: float = 0.50         # unobserved heterogeneity (caps achievable AUC)


# --------------------------------------------------------------------------------------
# Entity pools
# --------------------------------------------------------------------------------------

def _build_pincodes(rng: np.random.Generator, n: int) -> pd.DataFrame:
    """A pool of pincodes, each with a HIDDEN latent RTO risk + tier, geo, serviceability."""
    tier = rng.choice([1, 2, 3], size=n, p=[0.35, 0.40, 0.25])
    tier_bump = np.select([tier == 1, tier == 2, tier == 3], [-0.08, 0.00, 0.12])
    latent_risk = np.clip(rng.beta(2.0, 5.0, size=n) + tier_bump, 0.01, 0.99)
    # Geo within mainland India bounding box.
    lat = rng.uniform(9.0, 32.0, size=n)
    lon = rng.uniform(70.0, 89.0, size=n)
    serviceable = rng.random(n) > 0.03  # ~3% non-serviceable
    code = rng.integers(110001, 855999, size=n)  # plausible 6-digit-ish codes
    city = [rng.choice(CITIES_BY_TIER[int(t)]) for t in tier]
    return pd.DataFrame(
        {
            "pincode": code,
            "city_tier": tier,
            "city": city,
            "dest_lat": lat,
            "dest_lon": lon,
            "is_serviceable": serviceable,
            "_pincode_latent_risk": latent_risk,  # HIDDEN
        }
    )


def _build_buyers(rng: np.random.Generator, n: int, n_pincodes: int) -> pd.DataFrame:
    """A pool of legitimate buyers, each with a HIDDEN latent RTO propensity."""
    latent_prop = rng.beta(2.0, 6.0, size=n)  # most buyers reliable; a tail of chronic RTO
    home_pincode_idx = rng.integers(0, n_pincodes, size=n)
    signup_offset_days = rng.integers(1, 900, size=n)  # account age seed
    return pd.DataFrame(
        {
            "buyer_id": [f"BUY{100000 + i}" for i in range(n)],
            "home_pincode_idx": home_pincode_idx,
            "device_id": [f"DEV{500000 + i}" for i in range(n)],  # own device
            "signup_offset_days": signup_offset_days,
            "_buyer_latent_propensity": latent_prop,  # HIDDEN
        }
    )


def _make_addresses(rng: np.random.Generator, completeness: np.ndarray,
                    cities: np.ndarray, pincodes: np.ndarray) -> list[str]:
    """Build address strings whose richness tracks the completeness score.

    High completeness -> house no + street + area + landmark + city + pincode.
    Low completeness  -> components dropped / 'monkey-typed' fragments (RTO signal).
    """
    out: list[str] = []
    streets = rng.choice(STREETS, size=len(completeness))
    areas = rng.choice(AREAS, size=len(completeness))
    landmarks = rng.choice(LANDMARKS, size=len(completeness))
    house_nos = rng.integers(1, 400, size=len(completeness))
    for i, c in enumerate(completeness):
        parts: list[str] = []
        if c > 0.35:
            parts.append(f"H.No {house_nos[i]}")
        if c > 0.20:
            parts.append(str(streets[i]))
        parts.append(str(areas[i]))  # area almost always present
        if c > 0.55:
            parts.append(str(landmarks[i]))
        parts.append(str(cities[i]))
        parts.append(str(pincodes[i]))
        if c < 0.25:  # gibberish / malformed fragment
            parts = parts[:2] + ["xkjs" if rng.random() < 0.5 else "..."]
        out.append(", ".join(parts))
    return out


# --------------------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------------------

def generate(
    n: int = 20000,
    seed: int = 42,
    start_date: str = "2026-04-01",
    span_days: int = 120,
    cod_share: float = 0.62,
    ring_frac: float = 0.04,
    cod_rto_target: float = 0.27,
    prepaid_rto_target: float = 0.04,
    coef: Coefficients | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate ``n`` synthetic COD orders.

    Returns
    -------
    orders : DataFrame of observable-at-checkout fields + ``is_rto`` label.
    latents : DataFrame of HIDDEN ground-truth drivers (analysis only, never a feature).
    """
    coef = coef or Coefficients()
    rng = np.random.default_rng(seed)
    start = datetime.fromisoformat(start_date)
    total_seconds = span_days * 24 * 3600

    n_pincodes = max(200, n // 10)
    n_buyers = max(100, int(n * 0.45))  # <1 buyer per order -> natural recurrence
    pins = _build_pincodes(rng, n_pincodes)
    buyers = _build_buyers(rng, n_buyers, n_pincodes)

    n_ring = int(round(n * ring_frac))
    n_normal = n - n_ring

    # ---- normal (legitimate) orders --------------------------------------------------
    b_idx = rng.integers(0, n_buyers, size=n_normal)  # repeated buyers -> history signal
    # pincode: mostly the buyer's home pincode, sometimes elsewhere.
    home_pin = buyers["home_pincode_idx"].to_numpy()[b_idx]
    elsewhere = rng.integers(0, n_pincodes, size=n_normal)
    p_idx = np.where(rng.random(n_normal) < 0.80, home_pin, elsewhere)
    is_cod = rng.random(n_normal) < cod_share
    completeness = np.clip(rng.beta(6.0, 2.0, size=n_normal), 0.02, 1.0)  # mostly complete
    phone_verified = rng.random(n_normal) < 0.85
    ts = start + pd.to_timedelta(rng.uniform(0, total_seconds, size=n_normal), unit="s")
    device = buyers["device_id"].to_numpy()[b_idx]
    buyer_id = buyers["buyer_id"].to_numpy()[b_idx]
    buyer_prop = buyers["_buyer_latent_propensity"].to_numpy()[b_idx]
    signup_off = buyers["signup_offset_days"].to_numpy()[b_idx]
    is_ring = np.zeros(n_normal, dtype=bool)

    # ---- fraud-ring orders: many mule identities sharing few devices, bursty, COD -----
    if n_ring > 0:
        n_ring_devices = max(5, n_ring // 12)
        ring_devices = np.array([f"DEV_RING{i:04d}" for i in range(n_ring_devices)])
        rd_idx = rng.integers(0, n_ring_devices, size=n_ring)
        # bursty timestamps: each ring device fires around a base time.
        dev_base = rng.uniform(0, total_seconds, size=n_ring_devices)
        r_ts_sec = np.clip(dev_base[rd_idx] + rng.exponential(6 * 3600, size=n_ring),
                           0, total_seconds)
        r_ts = start + pd.to_timedelta(r_ts_sec, unit="s")
        r_p_idx = rng.integers(0, n_pincodes, size=n_ring)  # scattered destinations
        # bias ring pincodes toward higher latent risk
        high_risk_pins = pins["_pincode_latent_risk"].to_numpy().argsort()[::-1][: n_pincodes // 3]
        take_high = rng.random(n_ring) < 0.5
        r_p_idx[take_high] = rng.choice(high_risk_pins, size=take_high.sum())
        r_cod = np.ones(n_ring, dtype=bool)  # rings exploit COD
        r_completeness = np.clip(rng.beta(2.0, 4.0, size=n_ring), 0.02, 1.0)  # poor addresses
        r_phone_verified = rng.random(n_ring) < 0.25
        r_device = ring_devices[rd_idx]
        r_buyer_id = np.array([f"MULE{i:06d}" for i in rng.integers(0, n_ring * 3, size=n_ring)])
        r_buyer_prop = np.full(n_ring, 0.85)  # high propensity by construction
        r_signup_off = rng.integers(0, 5, size=n_ring)  # brand-new accounts
        r_is_ring = np.ones(n_ring, dtype=bool)

        # concatenate normal + ring
        b_idx = np.concatenate([b_idx, np.full(n_ring, -1)])
        p_idx = np.concatenate([p_idx, r_p_idx])
        is_cod = np.concatenate([is_cod, r_cod])
        completeness = np.concatenate([completeness, r_completeness])
        phone_verified = np.concatenate([phone_verified, r_phone_verified])
        ts = ts.append(r_ts)
        device = np.concatenate([device, r_device])
        buyer_id = np.concatenate([buyer_id, r_buyer_id])
        buyer_prop = np.concatenate([buyer_prop, r_buyer_prop])
        signup_off = np.concatenate([signup_off, r_signup_off])
        is_ring = np.concatenate([is_ring, r_is_ring])

    # ---- per-order attributes derived from pools ------------------------------------
    cat_idx = rng.choice(len(CATEGORY_NAMES), size=n, p=CATEGORY_WEIGHTS / CATEGORY_WEIGHTS.sum())
    category = np.array(CATEGORY_NAMES)[cat_idx]
    cat_effect = np.array([CATEGORIES[c][0] for c in category])
    cat_mu = np.array([CATEGORIES[c][1] for c in category])
    cat_sig = np.array([CATEGORIES[c][2] for c in category])
    order_value = np.round(np.exp(rng.normal(cat_mu, cat_sig)), 0)
    order_value = np.clip(order_value, 99, 60000)

    pin_risk = pins["_pincode_latent_risk"].to_numpy()[p_idx]
    serviceable = pins["is_serviceable"].to_numpy()[p_idx]
    city_tier = pins["city_tier"].to_numpy()[p_idx]
    dest_lat = pins["dest_lat"].to_numpy()[p_idx]
    dest_lon = pins["dest_lon"].to_numpy()[p_idx]
    pincode = pins["pincode"].to_numpy()[p_idx]
    city = pins["city"].to_numpy()[p_idx]

    # distance to nearest warehouse
    dist = np.min(
        [_haversine_km(dest_lat, dest_lon, WAREHOUSES[k, 0], WAREHOUSES[k, 1])
         for k in range(len(WAREHOUSES))],
        axis=0,
    )

    def _z(a: np.ndarray) -> np.ndarray:
        return (a - a.mean()) / (a.std() + 1e-9)

    # ---- causal logit (everything except the payment-group intercept) ---------------
    eta = (
        coef.addr_incomplete * (1.0 - completeness)
        + coef.pincode_risk * (pin_risk - 0.30)
        + coef.buyer_propensity * (buyer_prop - 0.25)
        + coef.non_serviceable * (~serviceable).astype(float)
        + coef.order_value_z * _z(np.log(order_value))
        + coef.distance_z * _z(dist)
        + coef.first_time * 0.0  # first-time added after chronological sort (below)
        + coef.phone_unverified * (~phone_verified).astype(float)
        + coef.ring * is_ring.astype(float)
        + rng.normal(0.0, coef.noise_sigma, size=n)
    )

    # ---- assemble, sort by time, derive first-time-buyer, then finalise label -------
    df = pd.DataFrame(
        {
            "order_ts": ts.values if hasattr(ts, "values") else ts,
            "buyer_id": buyer_id,
            "device_id": device,
            "payment_method": np.where(is_cod, "COD", "PREPAID"),
            "is_cod": is_cod.astype(int),
            "order_value": order_value,
            "product_category": category,
            "pincode": pincode,
            "city": city,
            "city_tier": city_tier,
            "is_serviceable": serviceable.astype(int),
            "dest_lat": np.round(dest_lat, 4),
            "dest_lon": np.round(dest_lon, 4),
            "distance_km": np.round(dist, 1),
            "address_completeness": np.round(completeness, 3),
            "phone_verified": phone_verified.astype(int),
            "signup_offset_days": signup_off,
            "_eta": eta,
            "_pincode_latent_risk": np.round(pin_risk, 4),
            "_buyer_latent_propensity": np.round(buyer_prop, 4),
            "_is_ring": is_ring.astype(int),
        }
    )
    df = df.sort_values("order_ts", kind="mergesort").reset_index(drop=True)

    # first-time buyer = chronologically first order for that buyer
    df["is_first_time_buyer"] = (~df.duplicated("buyer_id", keep="first")).astype(int)
    # account age: signup happened signup_offset_days before this order (>=0).
    # First-time buyers are newer accounts (clip to <=30 days).
    age = df["signup_offset_days"].astype("int64").to_numpy().copy()
    first_time = df["is_first_time_buyer"].to_numpy() == 1
    age[first_time] = np.clip(age[first_time], 0, 30)
    df["account_age_days"] = age

    # fold first-time effect into the logit, then calibrate per-payment intercepts
    eta = df["_eta"].to_numpy() + coef.first_time * df["is_first_time_buyer"].to_numpy()
    cod_mask = df["is_cod"].to_numpy() == 1
    c_cod = _bisect_intercept(eta[cod_mask], cod_rto_target)
    c_pre = _bisect_intercept(eta[~cod_mask], prepaid_rto_target)
    intercept = np.where(cod_mask, c_cod, c_pre)
    p_rto = _sigmoid(eta + intercept)
    df["is_rto"] = (rng.random(len(df)) < p_rto).astype(int)

    # order id + tidy timestamp
    df.insert(0, "order_id", [f"ORD{1000000 + i}" for i in range(len(df))])
    df["order_ts"] = pd.to_datetime(df["order_ts"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    # address text (needs city + pincode)
    df["address_text"] = _make_addresses(
        rng, df["address_completeness"].to_numpy(), df["city"].to_numpy(), df["pincode"].to_numpy()
    )

    # ---- split observable vs hidden --------------------------------------------------
    hidden_cols = ["_eta", "_pincode_latent_risk", "_buyer_latent_propensity", "_is_ring",
                   "signup_offset_days"]
    observable_cols = [
        "order_id", "order_ts", "buyer_id", "account_age_days", "is_first_time_buyer",
        "device_id", "phone_verified", "payment_method", "is_cod", "order_value",
        "product_category", "pincode", "city", "city_tier", "is_serviceable",
        "dest_lat", "dest_lon", "distance_km", "address_text", "address_completeness",
        "is_rto",
    ]
    orders = df[observable_cols].copy()
    latents = df[["order_id", "is_rto", "is_cod"] + [c for c in hidden_cols if c in df]].copy()
    latents = latents.rename(columns=lambda x: x.lstrip("_"))
    return orders, latents


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def _summary(orders: pd.DataFrame) -> str:
    total = len(orders)
    overall = orders["is_rto"].mean()
    by_pay = orders.groupby("payment_method")["is_rto"].agg(["mean", "size"])
    by_tier = orders.groupby("city_tier")["is_rto"].mean()
    n_buyers = orders["buyer_id"].nunique()
    repeat = (orders.groupby("buyer_id").size() > 1).sum()
    shared_dev = (orders.groupby("device_id").size() > 5).sum()
    lines = [
        f"orders                : {total:,}",
        f"unique buyers         : {n_buyers:,}  (repeat buyers: {repeat:,})",
        f"devices used >5 times : {shared_dev:,}  (fraud-ring signal)",
        f"overall RTO rate      : {overall:6.2%}",
        "by payment method     :",
    ]
    for pm, row in by_pay.iterrows():
        lines.append(f"    {pm:<8} RTO {row['mean']:6.2%}   (n={int(row['size']):,})")
    lines.append("by city tier          :")
    for t, m in by_tier.items():
        lines.append(f"    tier {t}   RTO {m:6.2%}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic COD/RTO orders for Axiom.")
    ap.add_argument("--n", type=int, default=20000, help="number of orders")
    ap.add_argument("--seed", type=int, default=42, help="random seed (reproducibility)")
    ap.add_argument("--out", default="data/cod_orders.csv", help="output CSV path")
    ap.add_argument("--start-date", default="2026-04-01", help="first order date (ISO)")
    ap.add_argument("--span-days", type=int, default=120, help="order window length in days")
    ap.add_argument("--cod-share", type=float, default=0.62, help="fraction of orders that are COD")
    ap.add_argument("--ring-frac", type=float, default=0.04, help="fraction that are fraud-ring")
    ap.add_argument("--cod-rto", type=float, default=0.27, help="target COD RTO rate")
    ap.add_argument("--prepaid-rto", type=float, default=0.04, help="target prepaid RTO rate")
    args = ap.parse_args()

    orders, latents = generate(
        n=args.n, seed=args.seed, start_date=args.start_date, span_days=args.span_days,
        cod_share=args.cod_share, ring_frac=args.ring_frac,
        cod_rto_target=args.cod_rto, prepaid_rto_target=args.prepaid_rto,
    )

    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    orders.to_csv(args.out, index=False)
    latents_path = args.out.replace(".csv", "_latents.csv")
    latents.to_csv(latents_path, index=False)

    print(f"[axiom] wrote {len(orders):,} orders -> {args.out}")
    print(f"[axiom] wrote hidden latents (analysis only) -> {latents_path}")
    print("-" * 60)
    print(_summary(orders))
    print("-" * 60)
    print("NOTE: *_latents.csv holds the ground-truth drivers. NEVER use them as features.")


if __name__ == "__main__":
    main()
