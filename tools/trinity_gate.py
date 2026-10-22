#!/usr/bin/env python3
"""
trinity_gate.py — THE TRINITY: Foundational Engine for Truth & Accuracy
=======================================================================
Implements the three-gate validation pipeline defined in the Universal AI Laws
(`THE TRINITY: FOUNDATIONAL ENGINE FOR TRUTH & ACCURACY`, Law file:
C:\\Amd949609_Antigravity_v1\\00_ailaws.md).

Governing principle baked into the API: **Truth/Accuracy is a separate axis from
Transparency.** Every verdict therefore carries two things:

  * `accuracy`  — the gate outcome (physics -> probability -> baseline)
  * `audit`     — the immutable lineage: rule version, every input, every
                  intermediate number, and a sha256 of the original record.

Gates
-----
  Gate 1  Physics / Reality        hard constraints (spatial, temporal, hash)
                                   fail  -> QUARANTINE
  Gate 2  Probability & Odds       Bayesian posterior from source reliability
                                   and independent corroboration
                                   below threshold -> FLAG_CORROBORATE
  Gate 3  Reversion to Mean        z-score vs. longitudinal baseline
                                   outlier -> ESCALATE_HIGH_SCRUTINY

Precedent behaviour (the law is explicit that gates must be able to change their
verdict as evidence accrues): a record is never destroyed, only classified, and
`recheck()` re-runs the same record against a new baseline/corroboration set.

No third-party dependencies. Standard library only.

CLI
---
  python3 trinity_gate.py --input evidence.jsonl --out verdicts.jsonl
  python3 trinity_gate.py --selftest
  python3 trinity_gate.py --lint <file.jsonl>       # schema check only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

RULE_VERSION = "trinity-1.0.0"

# ---------------------------------------------------------------------------
# Tunables (documented so audits can cite them)
# ---------------------------------------------------------------------------
MAX_GROUND_SPEED_KMH = 900.0     # faster than a commercial airliner => physically implausible
FUTURE_TOLERANCE_H = 24.0        # clock skew allowance for "observed in the future"
# Historical events are legitimate: only impossibly-old dates are rejected.
SANITY_FLOOR = datetime(1000, 1, 1, tzinfo=timezone.utc)
EARTH_RADIUS_KM = 6371.0088
GATE2_POSTERIOR_THRESHOLD = 0.60  # below this => needs secondary corroboration
GATE3_Z_LIMIT = 3.0               # |z| beyond this => outlier, high scrutiny
GATE3_MIN_BASELINE_N = 5          # fewer samples than this => baseline untrusted

# Source reliability tiers (prior probability that a single, uncorroborated
# report from this class of source is accurate). Official records outrank
# everything else per Law 15 (Official Evidence Primacy).
SOURCE_TIERS: Dict[str, float] = {
    "official_record": 0.95,   # court/municipal/agency record of record
    "official_secondary": 0.85,  # agency summary, clerk index, recorded instrument
    "primary_media": 0.70,     # contemporaneous press, on-record interview
    "expert_analysis": 0.65,
    "third_party_data": 0.55,  # aggregators, people-search, scraped registries
    "social_media": 0.40,
    "anonymous_tip": 0.30,
    "unattributed": 0.20,
}
DEFAULT_TIER_PRIOR = 0.35

# Severity ordering: a record can trip several gates at once, so the primary
# verdict is the most severe, and every required action is still reported.
SEVERITY = {
    "ACCEPT": 0,
    "FLAG_CORROBORATE": 1,
    "ESCALATE_HIGH_SCRUTINY": 2,
    "QUARANTINE": 3,
}

VERDICT_ACCEPT = "ACCEPT"
VERDICT_QUARANTINE = "QUARANTINE"
VERDICT_CORROBORATE = "FLAG_CORROBORATE"
VERDICT_ESCALATE = "ESCALATE_HIGH_SCRUTINY"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def parse_ts(value: Any) -> Optional[datetime]:
    """Parse ISO-8601 (with or without Z) to an aware UTC datetime."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d %b %Y"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def record_digest(record: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


# ---------------------------------------------------------------------------
# Gate 1 — Physics / Reality (hard constraints)
# ---------------------------------------------------------------------------
def gate1_physics(record: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    violations: List[str] = []
    notes: List[str] = []

    loc = record.get("location") or {}
    if loc:
        lat, lon = loc.get("lat"), loc.get("lon")
        if lat is None or lon is None:
            violations.append("location present but lat/lon incomplete")
        else:
            try:
                lat_f, lon_f = float(lat), float(lon)
            except (TypeError, ValueError):
                violations.append("lat/lon not numeric")
            else:
                if not -90 <= lat_f <= 90:
                    violations.append(f"lat {lat_f} outside [-90,90]")
                if not -180 <= lon_f <= 180:
                    violations.append(f"lon {lon_f} outside [-180,180]")
                if lat_f == 0 and lon_f == 0:  # classic null-island artefact
                    notes.append("coordinates are exactly 0,0 (null-island artefact risk)")

    observed = parse_ts(record.get("observed_at"))
    collected = parse_ts(record.get("collected_at"))

    if observed is None and "observed_at" in record:
        violations.append("observed_at unparseable")
    if observed:
        if observed < SANITY_FLOOR:
            violations.append(f"observed_at precedes the year 1000 sanity floor ({observed.date()})")
        elif observed.year < 1970:
            notes.append(f"historical record ({observed.date()}) — treated as a documented past event")
        if observed - now > timedelta(hours=FUTURE_TOLERANCE_H):
            violations.append(
                f"observed_at is {(observed - now).total_seconds()/3600:.1f}h in the future "
                f"(tolerance {FUTURE_TOLERANCE_H:.0f}h)"
            )
    if observed and collected and collected < observed:
        violations.append("collected_at precedes observed_at")

    # travel feasibility between consecutive observations
    prev = record.get("previous_location") or {}
    if loc and prev and prev.get("lat") is not None and prev.get("lon") is not None:
        prev_at = parse_ts(prev.get("at")) or parse_ts(prev.get("observed_at"))
        if prev_at and observed:
            dt_h = (observed - prev_at).total_seconds() / 3600.0
            try:
                dist = haversine_km(
                    float(prev["lat"]), float(prev["lon"]), float(loc["lat"]), float(loc["lon"])
                )
            except (TypeError, ValueError):
                dist = None
            if dist is not None and dist > 0.5:  # <500 m: same place, not a move
                if dt_h <= 0:
                    violations.append(
                        f"two distinct locations reported at the same or inverted time "
                        f"({dt_h:.3f}h apart, {dist:.1f} km)"
                    )
                else:
                    speed = dist / dt_h
                    if speed > MAX_GROUND_SPEED_KMH:
                        violations.append(
                            f"implied travel speed {speed:.0f} km/h exceeds "
                            f"{MAX_GROUND_SPEED_KMH:.0f} km/h ({dist:.1f} km in {dt_h:.2f}h)"
                        )
                    elif speed > MAX_GROUND_SPEED_KMH * 0.6:
                        notes.append(f"high implied travel speed {speed:.0f} km/h (air travel assumed)")

    # causal mechanism: a claim that asserts a physical process must name one
    if record.get("requires_mechanism"):
        mech = str(record.get("mechanism", "")).strip().lower()
        if mech in ("", "unknown", "none", "absent", "unexplained", "n/a"):
            violations.append(
                "claim requires a physical mechanism but none is supplied "
                "(Gate 1: no physical pathway)"
            )
        else:
            notes.append(f"mechanism supplied: {mech}")

    # physical provenance: optional content hash
    declared = record.get("sha256")
    if declared:
        actual = record.get("payload_sha256")
        if actual and actual.lower() != str(declared).lower():
            violations.append("declared sha256 does not match payload_sha256 (provenance broken)")

    return {
        "gate": "gate1_physics",
        "passed": not violations,
        "violations": violations,
        "notes": notes,
        "checked": {
            "coordinates": "ok" if loc and not any("lat" in v or "lon" in v for v in violations) else ("absent" if not loc else "failed"),
            "temporal_order": "ok" if not any("observed_at" in v or "collected_at" in v for v in violations) else "failed",
            "travel_feasibility": "ok" if not any("travel speed" in v or "inverted time" in v for v in violations) else "failed",
        },
    }


# ---------------------------------------------------------------------------
# Gate 2 — Probability & Odds (Bayesian posterior)
# ---------------------------------------------------------------------------
def _tier_prior(record: Dict[str, Any]) -> Tuple[float, str]:
    src = record.get("source") or {}
    tier = str(src.get("tier", "")).strip().lower()
    if tier in SOURCE_TIERS:
        return SOURCE_TIERS[tier], f"tier:{tier}"
    if src.get("reliability") is not None:
        try:
            r = float(src["reliability"])
            return (min(max(r, 0.01), 0.99), "explicit reliability")
        except (TypeError, ValueError):
            pass
    return DEFAULT_TIER_PRIOR, "default prior (unclassified source)"


def gate2_probability(record: Dict[str, Any]) -> Dict[str, Any]:
    prior, basis = _tier_prior(record)
    odds = prior / (1 - prior)

    corroborations = record.get("corroborations") or []
    applied: List[Dict[str, Any]] = []
    for i, cor in enumerate(corroborations):
        if not isinstance(cor, dict):
            continue
        indep = bool(cor.get("independent", True))
        if not indep:
            applied.append({"index": i, "ignored": "not independent (shared origin)"})
            continue
        c_tier = str(cor.get("tier", "")).strip().lower()
        c_prior = SOURCE_TIERS.get(c_tier, DEFAULT_TIER_PRIOR)
        # Likelihood ratio = P(corroboration | claim true) / P(corroboration | claim false).
        # A reliable source is far more likely to exist if the claim is true (LR >> 1);
        # an unreliable one can never raise confidence (floor at 1.0 = neutral).
        lr = max(1.0, 0.9 * c_prior / max(1e-6, 1.0 - c_prior))
        odds *= lr
        applied.append({"index": i, "tier": c_tier or "unclassified", "likelihood_ratio": round(lr, 4)})

    posterior = odds / (1 + odds)
    passed = posterior >= GATE2_POSTERIOR_THRESHOLD
    return {
        "gate": "gate2_probability",
        "passed": passed,
        "prior": round(prior, 4),
        "prior_basis": basis,
        "likelihood_ratios": applied,
        "posterior": round(posterior, 4),
        "threshold": GATE2_POSTERIOR_THRESHOLD,
        "action": "ok" if passed else "needs independent secondary corroboration",
    }


# ---------------------------------------------------------------------------
# Gate 3 — Reversion to Mean / Frequency / Flow
# ---------------------------------------------------------------------------
def gate3_baseline(record: Dict[str, Any], baseline: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    baseline = baseline or record.get("baseline") or {}
    value = record.get("value", record.get("numeric_value"))
    n = baseline.get("n")
    mean = baseline.get("mean", baseline.get("median"))
    stdev = baseline.get("stdev")

    if value is None or mean is None:
        return {
            "gate": "gate3_baseline",
            "passed": True,
            "applicable": False,
            "reason": "no numeric value or no baseline supplied — gate not applicable",
        }
    try:
        value_f = float(value)
        mean_f = float(mean)
        stdev_f = float(stdev) if stdev is not None else 0.0
    except (TypeError, ValueError):
        return {"gate": "gate3_baseline", "passed": True, "applicable": False,
                "reason": "non-numeric value/baseline"}

    if n is not None and int(n) < GATE3_MIN_BASELINE_N:
        return {"gate": "gate3_baseline", "passed": True, "applicable": False,
                "reason": f"baseline n={n} < {GATE3_MIN_BASELINE_N} (untrusted baseline)"}
    if stdev_f == 0.0:
        zero_dev = value_f != mean_f
        return {
            "gate": "gate3_baseline", "passed": not zero_dev, "applicable": True,
            "z_score": None if not zero_dev else float("inf"),
            "reason": "zero variance baseline" + (" — value deviates from a constant baseline" if zero_dev else ""),
            "action": "ok" if not zero_dev else "outlier vs constant baseline, high scrutiny",
        }

    z = (value_f - mean_f) / stdev_f
    outlier = abs(z) > GATE3_Z_LIMIT
    return {
        "gate": "gate3_baseline",
        "passed": not outlier,
        "applicable": True,
        "value": value_f,
        "mean": mean_f,
        "stdev": stdev_f,
        "z_score": round(z, 3),
        "z_limit": GATE3_Z_LIMIT,
        "direction": "above" if z > 0 else "below",
        "action": "ok" if not outlier else "outlier vs longitudinal baseline, escalate to high scrutiny",
    }


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------
@dataclass
class Verdict:
    record_id: str
    verdict: str
    accuracy: Dict[str, Any]
    audit: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate(record: Dict[str, Any], baseline: Optional[Dict[str, Any]] = None,
             now: Optional[datetime] = None) -> Verdict:
    rid = str(record.get("id") or record.get("record_id") or record_digest(record)[:12])
    g1 = gate1_physics(record, now=now)
    g2 = gate2_probability(record)
    g3 = gate3_baseline(record, baseline)

    actions: List[Dict[str, Any]] = []
    if not g1["passed"]:
        actions.append({"gate": "gate1", "verdict": VERDICT_QUARANTINE,
                        "action": "reject/quarantine until the physical constraint is satisfied",
                        "reasons": g1["violations"]})
    if not g2["passed"]:
        actions.append({"gate": "gate2", "verdict": VERDICT_CORROBORATE,
                        "action": "obtain independent secondary corroboration",
                        "reasons": [f"posterior {g2['posterior']} < threshold {g2['threshold']}"]})
    if g3.get("applicable", False) and not g3["passed"]:
        actions.append({"gate": "gate3", "verdict": VERDICT_ESCALATE,
                        "action": "escalate to high-scrutiny review",
                        "reasons": [f"z-score {g3.get('z_score')} beyond ±{g3['z_limit']}"]})

    verdict = max((a["verdict"] for a in actions), key=lambda v: SEVERITY[v]) if actions else VERDICT_ACCEPT

    return Verdict(
        record_id=rid,
        verdict=verdict,
        accuracy={"gates": {"gate1": g1, "gate2": g2, "gate3": g3},
                  "final": verdict,
                  "required_actions": actions,
                  "gates_failed": [a["gate"] for a in actions]},
        audit={
            "rule_version": RULE_VERSION,
            "evaluated_at": (now or datetime.now(timezone.utc)).isoformat(),
            "record_sha256": record_digest(record),
            "record_snapshot": record,
            "baseline_snapshot": baseline or record.get("baseline") or {},
            "gate_sequence": ["gate1_physics", "gate2_probability", "gate3_baseline"],
            "verdict_rule": "all gates evaluated; primary verdict = most severe failing gate "
                            "(QUARANTINE > ESCALATE > FLAG_CORROBORATE > ACCEPT), all actions reported",
            "transparency_note": "verdict + full input lineage retained; record never destroyed (Law 15)",
        },
    )


def recheck(verdict: Verdict, new_corroborations: Optional[List[Dict[str, Any]]] = None,
            new_baseline: Optional[Dict[str, Any]] = None) -> Verdict:
    """Trinity precedent: a record that failed a gate today may pass later."""
    rec = dict(verdict.audit["record_snapshot"])
    if new_corroborations is not None:
        rec["corroborations"] = list(rec.get("corroborations") or []) + list(new_corroborations)
    base = new_baseline if new_baseline is not None else verdict.audit.get("baseline_snapshot")
    return evaluate(rec, baseline=base)


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def iter_records(path: str) -> Iterable[Tuple[int, Dict[str, Any]]]:
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                yield lineno, json.loads(line)
            except json.JSONDecodeError as exc:
                yield lineno, {"_parse_error": str(exc), "_raw": line[:400], "id": f"line{lineno}"}


def cmd_selftest() -> int:
    """Historical precedent cases from the law file + core sanity checks."""
    now = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
    failures = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal failures
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + detail) if detail and not cond else ''}")
        if not cond:
            failures += 1

    print("Trinity self-test")

    # Wegner 1912: claim with no physical mechanism, weak sourcing -> not ACCEPT
    wegener = evaluate({
        "id": "precedent-wegener-1912",
        "claim": "continents drift",
        "source": {"tier": "expert_analysis"},
        "observed_at": "1912-01-06",
        "collected_at": "2026-10-21",
        "requires_mechanism": True,
        "mechanism": "unknown",
    }, now=now)
    check("Wegener 1912 is not ACCEPTed on 1912 evidence", wegener.verdict != VERDICT_ACCEPT, wegener.verdict)

    # ...and passes once physics evidence is added (seafloor spreading, 1960s)
    wegener_later = evaluate({
        "id": "precedent-wegener-1963",
        "claim": "continents drift",
        "source": {"tier": "expert_analysis"},
        "observed_at": "1963-01-06",
        "collected_at": "2026-10-21",
        "requires_mechanism": True,
        "mechanism": "seafloor spreading, paleomagnetic striping symmetry",
        "corroborations": [
            {"tier": "official_record", "independent": True},
            {"tier": "official_secondary", "independent": True},
        ],
    }, now=now)
    check("Wegener passes after 1960s physics corroboration", wegener_later.verdict == VERDICT_ACCEPT, wegener_later.verdict)

    # Semmelweis 1847: defies baseline -> escalated, then accepted with microbiology
    semmelweis = evaluate({
        "id": "precedent-semmelweis-1847",
        "claim": "handwashing reduces puerperal fever",
        "source": {"tier": "official_secondary"},
        "observed_at": "1847-05-15",
        "collected_at": "2026-10-21",
        "value": 1.2,
        "baseline": {"n": 24, "mean": 9.9, "stdev": 1.1},
    }, now=now)
    check("Semmelweis 1847 is flagged as outlier, not accepted", semmelweis.verdict == VERDICT_ESCALATE, semmelweis.verdict)

    # Gate 1 physics: teleportation
    teleport = evaluate({
        "id": "physics-teleport",
        "source": {"tier": "official_record"},
        "location": {"lat": 33.6595, "lon": -117.9988},
        "previous_location": {"lat": 40.7128, "lon": -74.0060, "at": "2026-10-20T09:00:00Z"},
        "observed_at": "2026-10-20T10:00:00Z",
        "collected_at": "2026-10-21T00:00:00Z",
    }, now=now)
    check("Impossible travel (NYC->HB in 1h) quarantined", teleport.verdict == VERDICT_QUARANTINE, teleport.verdict)

    future = evaluate({
        "id": "physics-future",
        "source": {"tier": "official_record"},
        "observed_at": "2027-01-01T00:00:00Z",
        "collected_at": "2026-10-21T00:00:00Z",
    }, now=now)
    check("Future-dated record quarantined", future.verdict == VERDICT_QUARANTINE, future.verdict)

    bad_coords = evaluate({
        "id": "physics-coords",
        "source": {"tier": "official_record"},
        "location": {"lat": 95.0, "lon": -117.0},
        "observed_at": "2026-10-20T09:00:00Z",
        "collected_at": "2026-10-21T00:00:00Z",
    }, now=now)
    check("Out-of-range latitude quarantined", bad_coords.verdict == VERDICT_QUARANTINE, bad_coords.verdict)

    # Gate 2: anonymous tip alone must be corroborated; official record alone may pass
    tip = evaluate({
        "id": "gate2-tip",
        "source": {"tier": "anonymous_tip"},
        "observed_at": "2026-10-20T09:00:00Z",
        "collected_at": "2026-10-21T00:00:00Z",
    }, now=now)
    check("Anonymous tip alone requires corroboration", tip.verdict == VERDICT_CORROBORATE, tip.verdict)

    official = evaluate({
        "id": "gate2-official",
        "source": {"tier": "official_record"},
        "observed_at": "2026-10-20T09:00:00Z",
        "collected_at": "2026-10-21T00:00:00Z",
    }, now=now)
    check("Official record alone is accepted", official.verdict == VERDICT_ACCEPT, official.verdict)

    shared_origin = evaluate({
        "id": "gate2-shared-origin",
        "source": {"tier": "social_media"},
        "observed_at": "2026-10-20T09:00:00Z",
        "collected_at": "2026-10-21T00:00:00Z",
        "corroborations": [
            {"tier": "official_record", "independent": False},
            {"tier": "official_record", "independent": False},
        ],
    }, now=now)
    check("Non-independent corroboration does not launder a weak source", shared_origin.verdict == VERDICT_CORROBORATE, shared_origin.verdict)

    # Gate 3: within-baseline value accepted, outlier escalated
    normal = evaluate({
        "id": "gate3-normal",
        "source": {"tier": "official_record"},
        "observed_at": "2026-10-20T09:00:00Z",
        "collected_at": "2026-10-21T00:00:00Z",
        "value": 10.4,
        "baseline": {"n": 30, "mean": 10.0, "stdev": 1.0},
    }, now=now)
    check("Value inside baseline band accepted", normal.verdict == VERDICT_ACCEPT, normal.verdict)

    # transparency axis: audit lineage present and stable
    v = evaluate({"id": "audit", "source": {"tier": "official_record"}}, now=now)
    check("Audit lineage carries rule version", v.audit.get("rule_version") == RULE_VERSION)
    check("Audit lineage carries record hash", len(v.audit.get("record_sha256", "")) == 64)
    check("Audit retains the record snapshot", "record_snapshot" in v.audit)

    print(f"self-test: {'ALL PASS' if failures == 0 else str(failures) + ' FAILURE(S)'}")
    return 1 if failures else 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="The Trinity — three-gate truth & accuracy engine")
    ap.add_argument("--input", help="JSONL file of evidence records")
    ap.add_argument("--out", help="JSONL file for verdicts (default: <input>.verdicts.jsonl)")
    ap.add_argument("--audit-log", help="append-only audit JSONL (default: alongside --out)")
    ap.add_argument("--selftest", action="store_true", help="run precedent + sanity cases")
    ap.add_argument("--lint", help="schema-check a JSONL file without evaluating")
    args = ap.parse_args(argv)

    if args.selftest:
        return cmd_selftest()

    if args.lint:
        bad = 0
        for lineno, rec in iter_records(args.lint):
            if "_parse_error" in rec:
                print(f"  line {lineno}: JSON error — {rec['_parse_error']}")
                bad += 1
            elif not (rec.get("source") or {}).get("tier"):
                print(f"  line {lineno}: missing source.tier (will fall back to default prior)")
        print(f"lint: {bad} parse error(s)")
        return 1 if bad else 0

    if not args.input:
        ap.print_help()
        return 2

    out_path = args.out or (args.input + ".verdicts.jsonl")
    audit_path = args.audit_log or (out_path + ".audit.jsonl")
    counts: Dict[str, int] = {}

    with open(out_path, "w", encoding="utf-8") as out, open(audit_path, "a", encoding="utf-8") as audit:
        for _lineno, rec in iter_records(args.input):
            v = evaluate(rec)
            counts[v.verdict] = counts.get(v.verdict, 0) + 1
            out.write(json.dumps(v.to_dict(), default=str) + "\n")
            audit.write(json.dumps(v.audit, default=str) + "\n")

    print(json.dumps({"rule_version": RULE_VERSION, "records": sum(counts.values()),
                      "verdicts": counts, "out": out_path, "audit": audit_path}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
