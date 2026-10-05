"""Regulatory compliance checklist (GDPR-like / Ministry of Health / HIPAA).

This document describes the relative readiness of the barekat Genomics platform.
The live status is also available from the API:

  GET /api/v1/compliance/checklist

## Product RBAC roles

| Product role | Internal role (compatible) | Key access |
|-----------|---------------------|---------------|
| Admin | admin | All permissions, users, organization, billing |
| Analyst | analyst / geneticist | Variant interpretation, report approval, EHR |
| Physician | physician / clinician | Own patients, approved reports |
| Lab Tech | lab_tech | Samples and pipeline |

## Implemented controls

1. JWT authentication and permission matrix
2. Patient name field encryption (PHI)
3. Access audit log and EHR export
4. Multi-organization isolation (`organization_id`)
5. Standard FHIR R4 and HL7 v2 Export/Import
6. Data subject access right (`/compliance/subjects/{id}/export`)
7. Partial PHI anonymization (`/erase`)

## Partial items / planned

- Structured informed consent (Consent entity)
- Cleanup job based on `phi_retention_days`
- Data breach procedure and notification
- Formal DPIA for hospital deployment

## Ministry of Health / national exchanges

- `sepas` and `tajhiz` connectors for output push
- FHIR Organization identifiers are configurable
- On-prem deployment through the `enterprise_onprem` plan

## Revenue model

| Plan | Mode | Sample limit/month |
|-----|------|---------------------|
| starter | SaaS | 50 |
| professional | SaaS | 500 |
| enterprise_onprem | On-prem | Very high |

API: `/api/v1/billing/plans`, `/subscribe`, `/usage`
"""
