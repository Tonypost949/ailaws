# Trinity intake — 20261022T004107Z

## demo.jsonl

```json
{
  "rule_version": "trinity-1.0.0",
  "records": 5,
  "verdicts": {
    "ACCEPT": 1,
    "FLAG_CORROBORATE": 1,
    "QUARANTINE": 2,
    "ESCALATE_HIGH_SCRUTINY": 1
  },
  "out": "/mnt/c/Amd949609_Antigravity_v1/EVIDENCE_LOCKER_MASTER/trinity/20261022T004107Z/.part.jsonl",
  "audit": "/mnt/c/Amd949609_Antigravity_v1/EVIDENCE_LOCKER_MASTER/trinity/20261022T004107Z/audit.jsonl"
}
```


## Verdict table

| record | verdict | gates failed |
|---|---|---|
| HB-DEED-001 | ACCEPT | - |
| TIP-003 | FLAG_CORROBORATE | gate2 |
| GEO-IMPOSSIBLE | QUARANTINE | gate1 |
| PRICE-OUTLIER | ESCALATE_HIGH_SCRUTINY | gate2, gate3 |
| DRIFT-CLAIM | QUARANTINE | gate1 |
