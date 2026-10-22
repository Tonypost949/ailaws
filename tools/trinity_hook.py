#!/usr/bin/env python3
"""
trinity_hook.py — integration layer that puts files and parsed artifacts through
THE TRINITY gates before they enter the Evidence Locker.

Law: THE TRINITY: FOUNDATIONAL ENGINE FOR TRUTH & ACCURACY
     C:\\Amd949609_Antigravity_v1\\00_ailaws.md

Two jobs:

1. `gate_file()` — build a Trinity record from a file on disk (sha256, size, mtime,
   optional EXIF/GPS, optional declared provenance) and return a verdict. A file whose
   hash no longer matches the previously recorded hash for that path is a Gate 1
   provenance violation and is QUARANTINEd: it means the artifact changed after intake.

2. `gate_artifact()` — gate an already-parsed artifact (e.g. a municipal record page or
   a docket) using host-based source tiering, so anything scraped from an official
   portal gets `official_record`/`official_secondary` and anything else falls back.

Also exposes `provenance_ledger_*` helpers for the path -> sha256 registry.
Stdlib only (Pillow optional for EXIF GPS).
"""
from __future__ import annotations

import csv
import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trinity_gate as tg  # noqa: E402

try:  # optional
    from PIL import Image  # type: ignore
    from PIL.ExifTags import TAGS, GPSTAGS  # type: ignore
    HAS_PIL = True
except Exception:  # pragma: no cover
    HAS_PIL = False

LEDGER_FIELDS = ["path", "sha256", "size", "observed_at", "verdict", "gates_failed"]

# Host -> source tier. Official portals outrank everything (Law 15).
HOST_TIERS = [
    (r"(^|\.)gov$", "official_record"),
    (r"(^|\.)us$", "official_record"),
    (r"(^|\.)courts\.ca\.gov$", "official_record"),
    (r"dockets\.justia\.com$", "official_secondary"),
    (r"unicourt\.com$", "third_party_data"),
    (r"laserfiche", "official_record"),          # clerk records systems (any host)
    (r"accela", "official_record"),              # permit/enforcement portals
    (r"civicplus|granicus|tylertech|muni\.codes|municode", "official_record"),
    (r"publicrecords|govqa|nextrequest|justfoia", "official_record"),
    (r"opencorporates\.com$", "third_party_data"),
    (r"facebook\.com$|x\.com$|twitter\.com$|instagram\.com$", "social_media"),
]


def sha256_file(path: str, chunk: int = 1 << 20) -> Optional[str]:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(chunk), b""):
                h.update(block)
    except OSError:
        return None
    return h.hexdigest()


def tier_for_url(url: str) -> str:
    host = re.sub(r"^[a-z]+://", "", str(url or "")).split("/")[0].split("@")[-1].lower()
    for pattern, tier in HOST_TIERS:
        if re.search(pattern, host):
            return tier
    return "unattributed"


def exif_gps(path: str) -> Optional[Dict[str, float]]:
    """Extract (lat, lon) from image EXIF when available; returns None otherwise."""
    if not HAS_PIL or not path.lower().endswith((".jpg", ".jpeg", ".tif", ".tiff", ".png")):
        return None
    try:
        exif = Image.open(path).getexif()
        gps = exif.get_ifd(0x8825) if hasattr(exif, "get_ifd") else None
        if not gps:
            return None
        out: Dict[str, Any] = {}
        for tag_id, value in gps.items():
            tag = GPSTAGS.get(tag_id, tag_id)
            out[tag] = value

        def to_deg(v: Any) -> Optional[float]:
            try:
                d, m, s = [float(x) for x in v]
            except Exception:
                return None
            return d + m / 60.0 + s / 3600.0

        lat, lon = to_deg(out.get("GPSLatitude")), to_deg(out.get("GPSLongitude"))
        if lat is None or lon is None:
            return None
        if out.get("GPSLatitudeRef") in ("S", b"S"):
            lat = -lat
        if out.get("GPSLongitudeRef") in ("W", b"W"):
            lon = -lon
        return {"lat": lat, "lon": lon}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# provenance ledger
# ---------------------------------------------------------------------------
def provenance_ledger_load(path: str) -> Dict[str, Dict[str, str]]:
    """Return {absolute_path: row} from an existing ledger CSV, tolerating large files."""
    rows: Dict[str, Dict[str, str]] = {}
    if not path or not os.path.exists(path):
        return rows
    try:
        with open(path, "r", newline="", encoding="utf-8", errors="replace") as fh:
            for row in csv.DictReader(fh):
                key = (row.get("path") or row.get("Path") or "").strip()
                if key:
                    rows[key] = row
    except OSError:
        pass
    return rows


def provenance_ledger_append(path: str, records: List[Dict[str, Any]]) -> None:
    if not records:
        return
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LEDGER_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        for r in records:
            w.writerow(r)


# ---------------------------------------------------------------------------
# gating
# ---------------------------------------------------------------------------
def gate_file(path: str, declared_sha256: Optional[str] = None,
              prior_ledger: Optional[Dict[str, Dict[str, str]]] = None,
              source_tier: Optional[str] = None,
              now: Optional[datetime] = None) -> Dict[str, Any]:
    """Gate one file. Returns {"path","sha256","verdict",...} with a Trinity verdict."""
    now = now or datetime.now(timezone.utc)
    actual = sha256_file(path)
    size = None
    try:
        size = os.path.getsize(path)
    except OSError:
        pass

    rec: Dict[str, Any] = {
        "id": path,
        "claim": f"artifact fixed-hash intake: {os.path.basename(path)}",
        "source": {"tier": source_tier or "official_record"},
        "collected_at": now.isoformat(),
        "payload_sha256": actual,
        "sha256": declared_sha256,
    }
    # mtime is the observation time of the artifact's last change
    try:
        rec["observed_at"] = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).isoformat()
    except OSError:
        pass

    gps = exif_gps(path)
    if gps:
        rec["location"] = gps

    prior = (prior_ledger or {}).get(os.path.abspath(path)) or (prior_ledger or {}).get(path)
    if prior:
        previous = (prior.get("sha256") or prior.get("SHA-256") or "").strip()
        if previous and actual and previous != actual:
            # artifact mutated after intake -> Gate 1 provenance break
            rec["sha256"] = previous
            rec["payload_sha256"] = actual
            rec["previous_location"] = None

    verdict = tg.evaluate(rec, now=now)
    out = {
        "path": path,
        "sha256": actual,
        "size": size,
        "observed_at": rec.get("observed_at"),
        "verdict": verdict.verdict,
        "gates_failed": verdict.accuracy.get("gates_failed") or [],
        "required_actions": verdict.accuracy.get("required_actions") or [],
        "posterior": verdict.accuracy["gates"]["gate2"]["posterior"],
        "record_sha256": verdict.audit["record_sha256"],
        "rule_version": verdict.audit["rule_version"],
        "mutated_since_intake": bool(prior and (prior.get("sha256") or prior.get("SHA-256") or "").strip()
                                     not in ("", actual)),
    }
    return out


def gate_artifact(url: str, observed_at: Optional[str] = None,
                  collected_at: Optional[str] = None, value: Optional[float] = None,
                  baseline: Optional[Dict[str, Any]] = None,
                  corroborations: Optional[List[Dict[str, Any]]] = None,
                  now: Optional[datetime] = None) -> Dict[str, Any]:
    """Gate a parsed artifact (HTML/Markdown/docket) by its source URL."""
    tier = tier_for_url(url)
    rec = {
        "id": url,
        "claim": f"parsed artifact from {url}",
        "source": {"tier": tier},
        "collected_at": collected_at or (now or datetime.now(timezone.utc)).isoformat(),
    }
    # only assert a timestamp we actually have; absence is not a physics violation
    if observed_at:
        rec["observed_at"] = observed_at
    if value is not None:
        rec["value"] = value
    if baseline:
        rec["baseline"] = baseline
    if corroborations:
        rec["corroborations"] = corroborations
    v = tg.evaluate(rec, baseline=baseline, now=now)
    return {
        "url": url,
        "source_tier": tier,
        "verdict": v.verdict,
        "gates_failed": v.accuracy.get("gates_failed") or [],
        "posterior": v.accuracy["gates"]["gate2"]["posterior"],
        "required_actions": v.accuracy.get("required_actions") or [],
        "rule_version": v.audit["rule_version"],
    }


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Trinity hook — gate files/artifacts before locker intake")
    ap.add_argument("--file", nargs="*", default=[], help="file(s) to gate")
    ap.add_argument("--url", nargs="*", default=[], help="parsed-artifact URL(s) to gate")
    ap.add_argument("--ledger", help="provenance ledger CSV to read/append")
    ap.add_argument("--append", action="store_true", help="append results to --ledger")
    args = ap.parse_args(argv)

    prior = provenance_ledger_load(args.ledger) if args.ledger else {}
    results: List[Dict[str, Any]] = []
    for f in args.file:
        results.append(gate_file(f, prior_ledger=prior))
    for u in args.url:
        results.append(gate_artifact(u))
    print(json.dumps(results, indent=2, default=str))
    if args.ledger and args.append:
        provenance_ledger_append(args.ledger, [r for r in results if "path" in r])
    return 0


if __name__ == "__main__":
    sys.exit(main())
