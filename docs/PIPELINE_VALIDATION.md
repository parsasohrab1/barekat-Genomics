# Pipeline Validation Report

_Generated at 2026-07-14T18:14:58.417933+00:00_

## Simulated concordance (PGx panel ground truth)

| Metric | Value |
|--------|-------|
| Mode | `simulated` |
| True positives | 5 |
| False positives | 2 |
| False negatives | 0 |
| Precision | 0.7143 |
| Recall / Sensitivity | 1.0000 |
| F1 | 0.8333 |
| Specificity | N/A (no true-negative set) |

### Matched

rs1142345, rs1799853, rs1800460, rs1801133, rs4244285

### Missed

—

### Extra calls

chr12:21178615:G>A, chr6:31356726:T>TC

## Acceptance gate (Phase 1)

- Simulated recall (sensitivity) ≥ 0.80 for PGx truth set
- Simulated precision ≥ 0.50 (extras without rsID tolerated in demo callset)
