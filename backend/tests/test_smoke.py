from backend.app.services.risk_scoring import score_claim
def test_shared_address_is_low_weight():
    result=score_claim({},[{"indicator_type":"SHARED_ADDRESS","description":"same address"}])
    assert result.score < 35
    assert result.category == "LOW"
