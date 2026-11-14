# Insurance Fraud Detection and Suspicious Network Investigation

Synthetic-data-first project to identify suspicious insurance claims, provider networks, invoices, and payments using explainable rules and graph analysis.

## Stack
- FastAPI + SQLAlchemy
- SQLite by default (PostgreSQL supported through `DATABASE_URL`)
- NetworkX
- React frontend scaffold (planned in this starter)

## Quick start (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python scripts\generate_data.py
python scripts\validate_data.py
uvicorn backend.app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

## Generate scale
```powershell
python scripts\generate_data.py --claims 5000 --claimants 2000 --providers 500 --edges 8000 --seed 20261022
```

## Data
Generated CSVs are in `data/generated/`; labels are separately stored in `data/ground_truth/ground_truth.csv`.
Never use ground-truth fields as model features.

## Notes
This is an initial implementation foundation. Review `docs/` and expand the model and frontend before production use.
