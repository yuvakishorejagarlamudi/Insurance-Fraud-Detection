"""Calculate and save explainable fraud risk scores for imported claims.
Run from the project root: python -m scripts.calculate_fraud_scores
"""
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.models.entities import Claim, Invoice, Payment, RelationshipEdge, FraudIndicator
from backend.app.services.fraud_detection import detect_claim_indicators


def main():
    with SessionLocal() as db:
        claims = db.execute(select(Claim)).scalars().all()
        invoices = db.execute(select(Invoice)).scalars().all()
        payments = db.execute(select(Payment)).scalars().all()
        edges = db.execute(select(RelationshipEdge)).scalars().all()
        if not claims:
            print('No claims in database. Import data first.')
            return

        claim_rows = [{"claim_id": c.claim_id, "claimed_amount": c.claimed_amount,
                       "approved_amount": c.approved_amount, "status": c.status} for c in claims]
        invoice_rows = [{"invoice_id": i.invoice_id, "claim_id": i.claim_id,
                         "invoice_number": i.invoice_number, "amount": i.amount} for i in invoices]
        payment_rows = [{"payment_id": p.payment_id, "claim_id": p.claim_id,
                         "amount": p.amount} for p in payments]
        edge_rows = [{"edge_id": e.edge_id, "source_type": e.source_type,
                      "source_id": e.source_id, "target_type": e.target_type,
                      "target_id": e.target_id, "relationship_type": e.relationship_type,
                      "strength": e.strength} for e in edges]

        results = detect_claim_indicators(claim_rows, invoice_rows, payment_rows, edge_rows)
        claim_map = {c.claim_id: c for c in claims}
        # Replace only the indicators produced by this script, making reruns safe.
        prefix = 'AUTO-'
        existing = db.execute(select(FraudIndicator).where(FraudIndicator.indicator_id.like(prefix + '%'))).scalars().all()
        for item in existing:
            db.delete(item)
        db.flush()
        category_counts = Counter()
        flagged = []
        count_indicators = 0
        timestamp = datetime.now(timezone.utc).isoformat()
        for result in results:
            cid = result['claim_id']
            claim_map[cid].risk_score = float(result['risk_score'])
            category_counts[result['risk_category']] += 1
            if result['indicators']:
                flagged.append(result)
            for index, indicator in enumerate(result['indicators'], start=1):
                count_indicators += 1
                db.add(FraudIndicator(
                    indicator_id=f'{prefix}{cid}-{index:03d}',
                    claim_id=cid,
                    indicator_type=indicator['indicator_type'],
                    description=indicator['description'],
                    score=float(result['risk_score']),
                    detected_at=timestamp,
                ))
        db.commit()
        print(f'Claims scored: {len(results)}')
        print(f'Fraud indicators saved: {count_indicators}')
        print('Risk categories: ' + ', '.join(f'{k}={category_counts[k]}' for k in ('LOW','MEDIUM','HIGH')))
        print(f'Claims with detected indicators: {len(flagged)}')
        print('Top flagged claims:')
        for result in sorted(flagged, key=lambda r: (-r['risk_score'], r['claim_id']))[:10]:
            print(f"  {result['claim_id']}: {result['risk_score']:.0f} ({result['risk_category']}) — "
                  + '; '.join(i['indicator_type'] for i in result['indicators']))
        print('Done. Refresh http://127.0.0.1:8000/api/claims?limit=5')


if __name__ == '__main__':
    main()
