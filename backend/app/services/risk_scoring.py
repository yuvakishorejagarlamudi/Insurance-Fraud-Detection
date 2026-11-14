from dataclasses import dataclass

@dataclass
class RiskResult:
    score: float
    category: str
    reasons: list[str]

def score_claim(claim: dict, indicators: list[dict]) -> RiskResult:
    """Explainable rule score. Shared address alone is deliberately low-weight."""
    score = 0.0
    reasons = []
    weights = {
        "PAYMENT_OVERAGE": 35,
        "DUPLICATE_INVOICE": 35,
        "REPEATED_NARRATIVE": 20,
        "UNUSUAL_TIMING": 15,
        "SHARED_PHONE": 15,
        "SHARED_ADDRESS": 3,
        "PROVIDER_CONCENTRATION": 20,
        "OUT_OF_COVERAGE": 30,
    }
    for item in indicators:
        kind = item.get("indicator_type", "")
        weight = weights.get(kind, 5)
        score += weight
        reasons.append(f"{kind}: {item.get('description', 'rule triggered')}")
    score = min(100.0, score)
    category = "HIGH" if score >= 70 else "MEDIUM" if score >= 35 else "LOW"
    return RiskResult(score, category, reasons)
