import os
import sqlite3
from pathlib import Path

# Vercel Functions run from a read-only deployment bundle. /tmp is writable,
# but it is ephemeral and may be cleared when an instance is recycled.
if os.environ.get("VERCEL") == "1":
    DB_PATH = Path("/tmp") / "finguard.db"
else:
    DB_PATH = Path(__file__).resolve().parent / "finguard.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_ref TEXT UNIQUE NOT NULL,
            timestamp TEXT NOT NULL,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            amount REAL NOT NULL,
            channel TEXT NOT NULL,
            location TEXT NOT NULL,
            device_new INTEGER NOT NULL DEFAULT 0,
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            risk_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            status TEXT NOT NULL,
            reasons TEXT NOT NULL,
            model_flag INTEGER NOT NULL DEFAULT 0,
            anomaly_flag INTEGER NOT NULL DEFAULT 0,
            aml_flag INTEGER NOT NULL DEFAULT 0
        )
        """)
        conn.commit()

def insert_transaction(row):
    with get_connection() as conn:
        conn.execute("""
        INSERT OR IGNORE INTO transactions
        (txn_ref,timestamp,sender,receiver,amount,channel,location,device_new,
         failed_attempts,risk_score,risk_level,status,reasons,model_flag,anomaly_flag,aml_flag)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            row["txn_ref"], row["timestamp"], row["sender"], row["receiver"],
            row["amount"], row["channel"], row["location"], row["device_new"],
            row["failed_attempts"], row["risk_score"], row["risk_level"],
            row["status"], row["reasons"], row["model_flag"],
            row["anomaly_flag"], row["aml_flag"]
        ))
        conn.commit()

def fetch_transactions(limit=500):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

def fetch_by_id(txn_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM transactions WHERE id=?", (txn_id,)).fetchone()

def count_transactions():
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()["n"]

def clear_transactions():
    with get_connection() as conn:
        conn.execute("DELETE FROM transactions")
        conn.commit()
