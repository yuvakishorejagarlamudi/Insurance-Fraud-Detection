# Data Dictionary (starter)

| Entity | Primary Key | Key fields | Relationships |
|---|---|---|---|
| Claimant | claimant_id | name, address_hash, phone_hash, status | 1:N policies, incidents, claims |
| Policy | policy_id | claimant_id, coverage, dates, status | N:1 claimant; 1:N claims |
| Incident | incident_id | claimant_id, date, type, narrative_hash | N:1 claimant; 1:N claims |
| Claim | claim_id | claimant_id, policy_id, incident_id, amounts, status | N:1 claimant/policy/incident |
| Provider | provider_id | type, address_hash, bank_account_hash | 1:N invoices |
| Invoice | invoice_id | claim_id, provider_id, number, amount | N:1 claim/provider; 1:N payments |
| Payment | payment_id | claim_id, invoice_id, amount, date, status | N:1 claim/invoice |
| RelationshipEdge | edge_id | source/target type/id, relationship_type | graph edge |
| FraudIndicator | indicator_id | claim_id, type, score, evidence | N:1 claim |
| Investigation | investigation_id | claim_id, status, priority, outcome | N:1 claim |

All amounts are in the synthetic currency unit (INR by convention). Hash fields are synthetic tokens, not hashes of real personal data.
