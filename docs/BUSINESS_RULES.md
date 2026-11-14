# Business Rules

- IDs are deterministic and immutable.
- Baseline records are generated before anomalies.
- Ground truth is stored separately from features.
- A shared address is a weak signal, never proof of fraud.
- Legitimate repeat claims are permitted.
- Payment overage is paid_total > approved_amount.
- Duplicate invoice detection uses invoice_number across records.
- Every risk score must include evidence/reasons.
- Investigation status transitions are validated.
- Invalid foreign keys are reported rather than silently repaired.
