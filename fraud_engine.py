from __future__ import annotations
import random
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import RandomForestClassifier, IsolationForest

FEATURES = [
    "amount", "hour", "txn_count_1h", "device_new",
    "failed_attempts", "is_international", "amount_to_typical"
]

class FraudEngine:
    """Synthetic-data demonstration model; outputs require human review."""

    def __init__(self):
        self.classifier = RandomForestClassifier(
            n_estimators=120, max_depth=8, random_state=42,
            class_weight="balanced"
        )
        self.anomaly = IsolationForest(
            n_estimators=100, contamination=0.08, random_state=42
        )
        self._train()

    def _train(self):
        rng = np.random.default_rng(42)
        n = 7000
        amounts = rng.lognormal(mean=7.0, sigma=1.0, size=n).clip(50, 250000)
        hours = rng.integers(0, 24, n)
        counts = rng.poisson(2.0, n)
        device = rng.binomial(1, 0.12, n)
        failed = rng.poisson(0.35, n).clip(0, 8)
        intl = rng.binomial(1, 0.08, n)
        typical = rng.lognormal(mean=7.0, sigma=0.65, size=n).clip(100, 150000)
        ratio = amounts / np.maximum(typical, 1)
        # Synthetic labels: deliberately imperfect patterns for demo training.
        logit = (
            -3.4 + 0.000018 * amounts
            + 0.75 * (hours <= 4)
            + 0.8 * (counts >= 7)
            + 1.0 * device
            + 0.65 * (failed >= 3)
            + 0.85 * intl
            + 0.75 * (ratio >= 4)
        )
        probability = 1 / (1 + np.exp(-logit))
        labels = rng.binomial(1, probability)
        X = np.column_stack([amounts, hours, counts, device, failed, intl, ratio])
        self.classifier.fit(X, labels)
        self.anomaly.fit(X)

    def assess(self, tx, history):
        amount = float(tx["amount"])
        hour = int(datetime.fromisoformat(tx["timestamp"]).hour)
        typical = max(float(tx.get("typical_amount", 5000)), 100)
        count_1h = int(tx.get("txn_count_1h", 1))
        is_intl = int(tx.get("location", "India") not in ("India", "Unknown"))
        features = np.array([[
            amount, hour, count_1h, int(tx.get("device_new", 0)),
            int(tx.get("failed_attempts", 0)), is_intl, amount / typical
        ]], dtype=float)

        model_probability = float(self.classifier.predict_proba(features)[0][1])
        anomaly_flag = int(self.anomaly.predict(features)[0] == -1)

        reasons = []
        if amount >= 100000:
            reasons.append("High-value transaction compared with the demo threshold")
        if amount / typical >= 4:
            reasons.append("Amount is at least 4× the account's typical transaction")
        if hour <= 4:
            reasons.append("Transaction occurred during unusual overnight hours")
        if count_1h >= 7:
            reasons.append("High transaction frequency within one hour")
        if int(tx.get("device_new", 0)):
            reasons.append("Transaction originated from a new or unfamiliar device")
        if int(tx.get("failed_attempts", 0)) >= 3:
            reasons.append("Multiple failed attempts were recorded")
        if is_intl:
            reasons.append("Transaction location is outside the usual domestic profile")
        if anomaly_flag:
            reasons.append("Unsupervised anomaly model detected an unusual feature combination")

        aml_flag, aml_reasons = self._aml_checks(tx, history)
        reasons.extend(aml_reasons)

        # Transparent blended score, intentionally not a probability.
        score = int(round(
            35 * model_probability
            + 22 * anomaly_flag
            + 10 * (amount / typical >= 4)
            + 10 * (count_1h >= 7)
            + 8 * bool(tx.get("device_new", 0))
            + 7 * (int(tx.get("failed_attempts", 0)) >= 3)
            + 8 * aml_flag
        ))
        score = max(0, min(100, score))
        level = "High" if score >= 65 else ("Medium" if score >= 35 else "Low")
        status = "Review required" if score >= 35 else "No immediate concern"
        if not reasons:
            reasons = ["No major risk indicators were detected by this demonstration model"]

        return {
            "risk_score": score, "risk_level": level, "status": status,
            "reasons": reasons, "model_flag": int(model_probability >= 0.55),
            "anomaly_flag": anomaly_flag, "aml_flag": aml_flag,
            "model_score": round(model_probability * 100, 1)
        }

    def _aml_checks(self, tx, history):
        sender, receiver = tx["sender"], tx["receiver"]
        amount = float(tx["amount"])
        same_sender = [r for r in history if r["sender"] == sender]
        # Demonstration heuristic: several mid-sized outgoing transfers close together.
        recent = []
        now = datetime.fromisoformat(tx["timestamp"])
        for r in same_sender:
            try:
                dt = datetime.fromisoformat(r["timestamp"])
                if 0 <= (now - dt).total_seconds() <= 3600:
                    recent.append(r)
            except Exception:
                continue
        split_flag = len(recent) >= 3 and 10000 <= amount <= 99000
        # A simple two-hop/circular indicator: receiver previously sent to this sender.
        reverse_link = any(r["sender"] == receiver and r["receiver"] == sender for r in history)
        reasons = []
        if split_flag:
            reasons.append("Possible transaction splitting: multiple transfers from one sender within an hour")
        if reverse_link:
            reasons.append("Possible circular movement: a previous transfer exists in the reverse direction")
        return int(split_flag or reverse_link), reasons


def make_demo_transactions(n=100):
    rng = random.Random(19)
    rows = []
    now = datetime.now().replace(second=0, microsecond=0)
    names = [f"ACCT-{i:04d}" for i in range(1, 36)]
    locations = ["India"] * 9 + ["Singapore", "UAE", "United Kingdom"]
    for i in range(n):
        suspicious = rng.random() < 0.13
        amount = round(rng.uniform(100000, 280000) if suspicious else rng.uniform(150, 22000), 2)
        ts = now - timedelta(minutes=rng.randint(0, 60 * 24 * 8))
        sender = rng.choice(names)
        receiver = rng.choice([x for x in names if x != sender])
        rows.append({
            "txn_ref": f"FG-{now.strftime('%y%m%d')}-{i+1:04d}",
            "timestamp": ts.isoformat(timespec="minutes"),
            "sender": sender, "receiver": receiver, "amount": amount,
            "channel": rng.choice(["UPI", "Mobile Wallet", "Net Banking", "Card"]),
            "location": rng.choice(locations if suspicious else ["India"] * 10),
            "device_new": int(suspicious and rng.random() < 0.65),
            "failed_attempts": rng.randint(3, 6) if suspicious and rng.random() < 0.45 else rng.randint(0, 2),
            "typical_amount": round(rng.uniform(1500, 12000), 2),
            "txn_count_1h": rng.randint(7, 12) if suspicious and rng.random() < 0.5 else rng.randint(1, 5)
        })
    return rows
