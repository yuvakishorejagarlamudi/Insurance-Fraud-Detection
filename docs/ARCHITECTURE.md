# Architecture

- `scripts/generate_data.py`: deterministic synthetic data generation and anomaly planting.
- `scripts/validate_data.py`: integrity checks and report.
- `backend/app/models/entities.py`: SQLAlchemy persistence models.
- `backend/app/services/fraud_detection.py`: rule-based indicators.
- `backend/app/services/risk_scoring.py`: explainable score.
- `backend/app/services/graph_analysis.py`: NetworkX graph construction and summary.
- `backend/app/services/investigation.py`: state transition validation.
- `backend/app/main.py`: FastAPI health/dashboard/claims endpoints.
- `data/ground_truth/`: evaluation labels, separate from features.
