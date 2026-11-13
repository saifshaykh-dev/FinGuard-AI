from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
from datetime import datetime
import csv
import io
import json
import os
import random
import secrets
from database import init_db, insert_transaction, fetch_transactions, fetch_by_id, count_transactions
from fraud_engine import FraudEngine, make_demo_transactions

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
engine = FraudEngine()

def as_dict(row):
    return dict(row)

def seed_if_empty():
    if count_transactions() > 0:
        return
    demo = make_demo_transactions(100)
    history = []
    for tx in demo:
        result = engine.assess(tx, history)
        row = {**tx, **result, "reasons": json.dumps(result["reasons"])}
        insert_transaction(row)
        history.append(tx)

@app.before_request
def startup():
    init_db()
    seed_if_empty()

@app.route("/health")
def health():
    """Lightweight health check for local and hosted deployment verification."""
    return jsonify({"ok": True, "service": "FinGuard AI", "mode": "synthetic-demo"})

@app.route("/")
def index():
    rows = [as_dict(r) for r in fetch_transactions(500)]
    total = len(rows)
    high = sum(r["risk_level"] == "High" for r in rows)
    medium = sum(r["risk_level"] == "Medium" for r in rows)
    review = sum(r["status"] == "Review required" for r in rows)
    avg = round(sum(r["risk_score"] for r in rows) / total, 1) if total else 0
    recent = rows[:8]
    chart = {
        "labels": ["Low", "Medium", "High"],
        "values": [
            sum(r["risk_level"] == "Low" for r in rows),
            medium, high
        ]
    }
    daily = {}
    for r in rows:
        day = r["timestamp"][:10]
        daily[day] = daily.get(day, 0) + 1
    daily_items = sorted(daily.items())[-7:]
    return render_template("index.html", total=total, high=high, medium=medium,
                           review=review, avg=avg, recent=recent,
                           chart=json.dumps(chart), daily=json.dumps({
                               "labels": [x[0][5:] for x in daily_items],
                               "values": [x[1] for x in daily_items]
                           }))

@app.route("/transactions")
def transactions():
    rows = [as_dict(r) for r in fetch_transactions(500)]
    q = request.args.get("q", "").strip().lower()
    level = request.args.get("level", "All")
    if q:
        rows = [r for r in rows if q in " ".join(str(r[k]) for k in
                 ["txn_ref", "sender", "receiver", "channel", "location"]).lower()]
    if level in ("Low", "Medium", "High"):
        rows = [r for r in rows if r["risk_level"] == level]
    return render_template("transactions.html", rows=rows, q=q, level=level)

@app.route("/transaction/<int:txn_id>")
def transaction_detail(txn_id):
    row = fetch_by_id(txn_id)
    if not row:
        flash("Transaction not found.", "error")
        return redirect(url_for("transactions"))
    item = as_dict(row)
    try:
        item["reason_list"] = json.loads(item["reasons"])
    except Exception:
        item["reason_list"] = [item["reasons"]]
    return render_template("transaction_detail.html", item=item)

@app.route("/alerts")
def alerts():
    rows = [as_dict(r) for r in fetch_transactions(500)]
    rows = [r for r in rows if r["risk_level"] in ("High", "Medium") or r["aml_flag"]]
    return render_template("alerts.html", rows=rows)

@app.route("/simulate", methods=["POST"])
def simulate():
    try:
        amount = float(request.form.get("amount", 125000))
        typical_amount = float(request.form.get("typical_amount", 5000))
        failed_attempts = int(request.form.get("failed_attempts", 0))
        txn_count_1h = int(request.form.get("txn_count_1h", 1))
        device_new = int(request.form.get("device_new", 0))
        if not (1 <= amount <= 1000000000):
            raise ValueError("Amount must be between ₹1 and ₹1,000,000,000.")
        if not (1 <= typical_amount <= 1000000000):
            raise ValueError("Typical amount must be between ₹1 and ₹1,000,000,000.")
        if not (0 <= failed_attempts <= 20 and 1 <= txn_count_1h <= 100):
            raise ValueError("Failed attempts or transaction frequency is out of range.")
        if device_new not in (0, 1):
            raise ValueError("Invalid device selection.")
    except (TypeError, ValueError) as exc:
        flash(str(exc) or "Please enter valid transaction details.", "error")
        return redirect(url_for("transactions"))

    now = datetime.now().replace(second=0, microsecond=0)
    sender = request.form.get("sender", "ACCT-0099").strip()[:40] or "ACCT-0099"
    receiver = request.form.get("receiver", "ACCT-0021").strip()[:40] or "ACCT-0021"
    if sender == receiver:
        flash("Sender and receiver must be different demo accounts.", "error")
        return redirect(url_for("transactions"))

    tx = {
        "txn_ref": f"FG-LIVE-{now.strftime('%H%M%S')}-{random.randint(100,999)}",
        "timestamp": now.isoformat(timespec="minutes"),
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "channel": request.form.get("channel", "UPI")[:30],
        "location": request.form.get("location", "India")[:40],
        "device_new": device_new,
        "failed_attempts": failed_attempts,
        "typical_amount": typical_amount,
        "txn_count_1h": txn_count_1h
    }
    history = [as_dict(r) for r in fetch_transactions(500)]
    result = engine.assess(tx, history)
    insert_transaction({**tx, **result, "reasons": json.dumps(result["reasons"])})
    flash(f"Transaction analysed. Risk score: {result['risk_score']}/100 ({result['risk_level']}).", "success")
    return redirect(url_for("transactions"))

@app.route("/export")
def export():
    rows = [as_dict(r) for r in fetch_transactions(500)]
    output = io.StringIO()
    fields = ["txn_ref", "timestamp", "sender", "receiver", "amount", "channel",
              "location", "risk_score", "risk_level", "status", "reasons"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=finguard_transactions.csv"})

if __name__ == "__main__":
    init_db()
    seed_if_empty()
    print("\nFinGuard AI is running at http://127.0.0.1:5000\n")
    app.run(debug=False, host="127.0.0.1", port=5000)
