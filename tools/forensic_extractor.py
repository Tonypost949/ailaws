#!/usr/bin/env python3
"""
Forensic Extractor Script (Trinity-gated)
=========================================
Recursively scans the evidence directory, generates SHA-256 hashes for
chain-of-custody, extracts EXIF metadata (if Pillow is available), and puts every
artifact through THE TRINITY gates before it is recorded in the ledger.

Law: THE TRINITY: FOUNDATIONAL ENGINE FOR TRUTH & ACCURACY
     C:\\Amd949609_Antigravity_v1\\00_ailaws.md

Outputs:
  evidence_ledger.csv  — additive schema; existing columns preserved, Trinity columns appended
  (an artifact that mutated since a previous intake, or that fails a physical
   constraint, is marked QUARANTINE in the ledger but NEVER deleted — Law 15)

Directories are configurable and auto-detected for WSL/Kali, Windows and Termux.

Usage:
  python3 forensic_extractor.py                     # auto-detected dirs
  python3 forensic_extractor.py --dir <evidence> --out <ledger.csv>
  python3 forensic_extractor.py --dry-run           # report without writing
"""

import argparse
import csv
import hashlib
import os
import sys
from datetime import datetime, timezone

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

TOOLS_DIR = "/mnt/c/Amd949609_Antigravity_v1/tools"
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
try:
    import trinity_hook
    HAS_TRINITY = True
except Exception as _exc:  # degrade gracefully
    HAS_TRINITY = False
    _TRINITY_ERR = str(_exc)

# Candidate evidence roots, in priority order (first existing wins).
EVIDENCE_CANDIDATES = [
    os.environ.get("TRINITY_EVIDENCE_DIR", ""),
    "/mnt/c/Amd949609_Antigravity_v1/evidence",
    "/mnt/c/Amd949609_Antigravity_v1/EVIDENCE_LOCKER_MASTER",
    "/data/data/com.termux/files/home/osintneoai/evidence",
    os.path.expanduser("~/evidence"),
]
OUTPUT_CANDIDATES = [
    os.environ.get("TRINITY_LEDGER_OUT", ""),
    "/mnt/c/Amd949609_Antigravity_v1/EVIDENCE_LOCKER_MASTER/evidence_ledger.csv",
    os.path.expanduser("~/evidence_ledger.csv"),
]

LEDGER_FIELDS = [
    "Filename", "Path", "Size (Bytes)", "System_Created", "SHA-256", "EXIF_Data",
    "Trinity_Verdict", "Trinity_Gates_Failed", "Trinity_Posterior",
    "Mutated_Since_Intake", "Trinity_Rule_Version", "Gated_At",
]


def first_existing(cands, must_be_file=False):
    for c in cands:
        if not c:
            continue
        if (os.path.isfile(c) if must_be_file else os.path.isdir(c)):
            return c
    return None


def hash_file(filepath):
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha256.update(block)
        return sha256.hexdigest()
    except Exception as exc:
        return "ERROR: " + str(exc)


def extract_exif(filepath):
    if not HAS_PIL:
        return "Install Pillow (pip install Pillow) for EXIF extraction"
    if not filepath.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif")):
        return "N/A (Not an image)"
    try:
        img = Image.open(filepath)
        exif_data = img.getexif()
        if not exif_data:
            return "No EXIF Data Found"
        extracted = []
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag in ("DateTime", "DateTimeOriginal", "Make", "Model", "Software"):
                extracted.append(f"{tag}: {value}")
        return " | ".join(extracted) if extracted else "No relevant EXIF found"
    except Exception as exc:
        return "EXIF ERROR: " + str(exc)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Trinity-gated forensic extractor")
    ap.add_argument("--dir", default="", help="evidence directory to scan")
    ap.add_argument("--out", default="", help="ledger CSV to write")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    ap.add_argument("--limit", type=int, default=0, help="stop after N files (0 = no limit)")
    args = ap.parse_args(argv)

    evidence_dir = args.dir or first_existing(EVIDENCE_CANDIDATES)
    if not evidence_dir:
        print("[!] No evidence directory found. Checked:")
        for c in EVIDENCE_CANDIDATES:
            if c:
                print("    -", c)
        return 1

    out_csv = args.out or first_existing(OUTPUT_CANDIDATES, must_be_file=True) \
        or os.path.join(evidence_dir, "evidence_ledger.csv")

    print(f"[*] Scanning directory: {evidence_dir}")
    print(f"[*] Ledger target      : {out_csv}")
    print(f"[*] Trinity available  : {HAS_TRINITY}"
          + ("" if HAS_TRINITY else f"  ({_TRINITY_ERR})"))
    print(f"[*] Pillow available   : {HAS_PIL}")

    prior = trinity_hook.provenance_ledger_load(out_csv) if HAS_TRINITY else {}
    if prior:
        print(f"[*] Prior ledger rows  : {len(prior)} (used for mutation detection)")

    records = []
    quarantined = 0
    for root, _dirs, files in os.walk(evidence_dir):
        for file in sorted(files):
            filepath = os.path.join(root, file)
            if filepath == out_csv:
                continue
            print("[*] Processing:", file)
            try:
                file_size = os.path.getsize(filepath)
                created = datetime.fromtimestamp(os.path.getctime(filepath)).strftime("%Y-%m-%d %H:%M:%S")
            except OSError as exc:
                print("    [!] unreadable:", exc)
                continue

            row = {
                "Filename": file,
                "Path": filepath,
                "Size (Bytes)": file_size,
                "System_Created": created,
                "SHA-256": hash_file(filepath),
                "EXIF_Data": extract_exif(filepath),
                "Trinity_Verdict": "NOT_GATED",
                "Trinity_Gates_Failed": "",
                "Trinity_Posterior": "",
                "Mutated_Since_Intake": "",
                "Trinity_Rule_Version": "",
                "Gated_At": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }

            if HAS_TRINITY:
                gate = trinity_hook.gate_file(filepath, prior_ledger=prior,
                                              source_tier="official_record")
                row["Trinity_Verdict"] = gate["verdict"]
                row["Trinity_Gates_Failed"] = ",".join(gate["gates_failed"])
                row["Trinity_Posterior"] = gate["posterior"]
                row["Mutated_Since_Intake"] = gate["mutated_since_intake"]
                row["Trinity_Rule_Version"] = gate["rule_version"]
                if gate["verdict"] == "QUARANTINE":
                    quarantined += 1
                    print("    [!] QUARANTINE:", "; ".join(
                        r for a in gate["required_actions"] for r in a.get("reasons", [])))

            records.append(row)
            if args.limit and len(records) >= args.limit:
                break
        if args.limit and len(records) >= args.limit:
            break

    if not records:
        print("[-] No files found to process.")
        return 0

    if args.dry_run:
        print(f"\n[dry-run] {len(records)} file(s), {quarantined} quarantine(s) — nothing written")
        return 0

    new_file = not os.path.exists(out_csv)
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "a" if not new_file else "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS, extrasaction="ignore")
        if new_file:
            writer.writeheader()
        writer.writerows(records)

    print(f"\n[+] Processed {len(records)} file(s), {quarantined} quarantined.")
    print(f"[+] Forensic ledger: {out_csv}")
    if quarantined:
        print("[!] QUARANTINEd artifacts are recorded but must not be indexed until the")
        print("    physical constraint is satisfied (provenance re-verified).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
