from fastapi import APIRouter
from backend.app.fraud_engine import detect_fraud
from backend.app.network_analysis import analyze_network

router = APIRouter(prefix="/api", tags=["Fraud Intelligence"])

@router.get("/fraud-analysis")
def fraud_analysis():
    # Use the same source as the claims dashboard. Historical exception
    # CSVs from unrelated synthetic datasets must not be attached to these claims.
    results = detect_fraud()
    return {
        "total_suspicious_claims": len(results),
        "high_risk": sum(item["risk_level"] == "HIGH" for item in results),
        "medium_risk": sum(item["risk_level"] == "MEDIUM" for item in results),
        "low_risk": sum(item["risk_level"] == "LOW" for item in results),
        "claims": results,
    }

@router.get("/network-analysis")
def network_analysis():
    return analyze_network()
