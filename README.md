# FinGuard AI — Financial Fraud & AML Monitoring

A hackathon-ready educational prototype for analysing **synthetic** financial transactions. It combines RandomForest classification, IsolationForest anomaly detection, behavioural indicators, basic AML heuristics, explainable risk scoring, transaction search, alerts, a simulator and CSV export.

## Run locally (Python 3.12+)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py app.py
```

Open http://127.0.0.1:5000.

## Deploy on Vercel

Import this repository into Vercel with root directory `./`. It uses Vercel's Python/Flask detection. Keep build and output directory settings empty. The Flask app is exported as `app` from the root-level `app.py`; dependencies are in `requirements.txt`; Python 3.12 is selected by `.python-version`; frontend assets are mirrored under `public/static/`.

After deployment, visit `/health`; the response should contain `{"ok":true}`. No API keys are required for the synthetic demo. Set `FLASK_SECRET_KEY` in Vercel Environment Variables before sharing the site.

## Hosted database behaviour

On Vercel, SQLite uses `/tmp` because the deployment filesystem is read-only. That location is ephemeral and instance-local: demo records may disappear when an instance is recycled, and separate serverless instances do not share the same database. Use a managed persistent database before multi-user or production use.

## Responsible-use limitations

This is a learning/demo tool, not a bank integration or certified fraud system. It uses synthetic training labels and synthetic transactions; model scores are not calibrated probabilities. AML checks are simple indicators, not legal findings. A flag is not proof of fraud or money laundering. Do not enter real customer information or credentials and do not automatically block, accuse, or report anyone based only on this prototype. Production use needs authentication, authorization, durable encrypted storage, audit logs, monitoring, fairness and model validation, retention controls, and legal/regulatory review.
