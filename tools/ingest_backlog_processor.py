#!/usr/bin/env python3
"""ingest_backlog_processor.py — processes queued parse tasks from automated_backlog.json.

Reads the task_system automated_backlog.json, parses each queued target file
(HTML visualization / markdown), extracts structured content, writes
`<name>.parsed.md` + `<name>.parsed.json` into the output dir, and marks the
backlog entry completed (with timestamp + outputs). Backs up the backlog JSON
first (Law 14).

Supports (regex-based, stdlib only):
  * html_parse  -> title/subtitle, headings, mermaid diagram blocks, tables
                   (headers+rows), cards (h3+p), bullet lists, script JSON blobs
  * markdown_parse -> headings outline; special: dockets.justia.com_* ->
                   structured federal docket (filings list, key orders)

Usage (Linux side / WSL):
  python3 ingest_backlog_processor.py \
    --backlog "/mnt/c/Amd949609_Antigravity_v1/tools/task_system/automated_backlog.json" \
    --srcdir  "/mnt/c/OsintNeoAi/evidence/downloads_batch_ingest" \
    --out     "/mnt/c/OsintNeoAi/evidence/downloads_batch_ingest/parsed_20261018"
"""
import argparse
import html as htmlmod
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

# THE TRINITY gates (law: THE TRINITY: FOUNDATIONAL ENGINE FOR TRUTH & ACCURACY).
# Every artifact is gated before it is indexed; QUARANTINEd artifacts are recorded
# in the backlog but their parsed output is NOT written (nothing is ever deleted).
sys.path.insert(0, "/mnt/c/Amd949609_Antigravity_v1/tools")
try:
    import trinity_hook
    HAS_TRINITY = True
except Exception as _e:  # degrade gracefully, never block the pipeline
    HAS_TRINITY = False
    _TRINITY_ERR = str(_e)

sys.stdout.reconfigure(line_buffering=True)

LEDGER = "/mnt/c/Amd949609_Antigravity_v1/EVIDENCE_LOCKER_MASTER/trinity_provenance_ledger.csv"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def strip_tags(s):
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    return re.sub(r"[ \t\r\f]+", " ", s)


def clean(s):
    return re.sub(r"\s+", " ", htmlmod.unescape(s)).strip()


def parse_html(text):
    out = {"kind": "html"}
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
    out["title"] = clean(m.group(1)) if m else ""
    m = re.search(r'class="subtitle"[^>]*>(.*?)</div>', text, re.S | re.I)
    out["subtitle"] = strip_tags(m.group(1)).strip() if m else ""
    out["headings"] = [strip_tags(x).strip() for x in re.findall(r"<h[1-4][^>]*>(.*?)</h[1-4]>", text, re.S | re.I)]
    out["headings"] = [h for h in out["headings"] if h][:60]
    out["mermaid"] = [strip_tags(b).strip() for b in re.findall(r'<div class="mermaid"[^>]*>(.*?)</div>', text, re.S | re.I)]
    # tables
    tables = []
    for tbl in re.findall(r"<table.*?</table>", text, re.S | re.I):
        headers = [strip_tags(x).strip() for x in re.findall(r"<th[^>]*>(.*?)</th>", tbl, re.S | re.I)]
        rows = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, re.S | re.I):
            cells = [strip_tags(x).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
            if cells and any(cells):
                rows.append(cells)
        tables.append({"headers": headers, "rows": rows})
    out["tables"] = tables
    # cards h3+p
    out["cards"] = [{"title": strip_tags(t).strip(), "body": strip_tags(b).strip()}
                    for t, b in re.findall(r"<h3[^>]*>(.*?)</h3>\s*(?:<p[^>]*>(.*?)</p>)?", text, re.S | re.I)]
    # generic bullet/paragraph text dump (body minus scripts/styles)
    body = re.search(r"<body[^>]*>(.*?)</body>", text, re.S | re.I)
    body = body.group(1) if body else text
    out["text"] = strip_tags(body).strip()
    # inline JSON-likes in scripts
    blobs = []
    for sc in re.findall(r"<script[^>]*>(.*?)</script>", text, re.S | re.I):
        for cand in re.findall(r"(\{.*\}|\[.*\])", sc, re.S):
            cand = cand.strip()
            if len(cand) > 40 and ('"' in cand or "'" in cand):
                blobs.append(cand[:20000])
    out["script_blobs"] = blobs[:10]
    return out


def parse_docket_md(text):
    out = {"kind": "docket", "raw_len": len(text)}
    # header block: parties/case number/date/judge/nature
    m = re.search(r"^(.*?)This docket was last retrieved on ([A-Za-z]+ \d+, \d{4})", text, re.S)
    header = clean(m.group(1))[:800] if m else ""
    out["header"] = header
    out["retrieved"] = m.group(2) if m else ""
    m2 = re.search(r"(\d:\d{2}-[a-z]{2}-\d{5})", text, re.I)
    out["case_number"] = m2.group(1) if m2 else ""
    # filings: split on 'Filing N'
    parts = re.split(r"(?=Filing\s+\d+\s)", text)
    filings = []
    for p in parts:
        m3 = re.match(r"Filing\s+(\d+)\s+(.*)", p, re.S)
        if not m3:
            continue
        num = int(m3.group(1))
        desc = clean(m3.group(2))[:600]
        filings.append({"filing": num, "desc": desc})
    # dedupe by number keep longest desc
    bynum = {}
    for f in filings:
        cur = bynum.get(f["filing"])
        if cur is None or len(f["desc"]) > len(cur["desc"]):
            bynum[f["filing"]] = f
    out["filings"] = [bynum[k] for k in sorted(bynum)]
    out["filing_count"] = len(out["filings"])
    return out


def parse_md(text):
    out = {"kind": "markdown", "raw_len": len(text)}
    out["headings"] = [clean(h) for h in re.findall(r"^#{1,6}\s+(.*)$", text, re.M)][:80]
    out["text"] = text
    return out


def render_md(name, parsed):
    L = [f"# Parsed: {name}", f"- kind: {parsed.get('kind')}", f"- parsed: {now_iso()}"]
    if parsed.get("title"):
        L.append(f"- title: {parsed['title']}")
    if parsed.get("subtitle"):
        L.append(f"- subtitle: {parsed['subtitle']}")
    if parsed.get("retrieved"):
        L.append(f"- docket retrieved: {parsed['retrieved']}")
    if parsed.get("case_number"):
        L.append(f"- case number: {parsed['case_number']}")
    L.append("")
    if parsed.get("headings"):
        L += ["## Headings"] + [f"- {h}" for h in parsed["headings"][:60]] + [""]
    if parsed.get("mermaid"):
        for i, mm in enumerate(parsed["mermaid"], 1):
            L += [f"## Mermaid diagram {i}", "```mermaid", mm[:12000], "```", ""]
    if parsed.get("tables"):
        for i, tb in enumerate(parsed["tables"], 1):
            L += [f"## Table {i} ({len(tb['rows'])} rows)"]
            if tb["headers"]:
                L.append("| " + " | ".join(tb["headers"]) + " |")
                L.append("|" + "|".join(["---"] * len(tb["headers"])) + "|")
            for r in tb["rows"][:500]:
                L.append("| " + " | ".join(c.replace("|", "/") for c in r) + " |")
            L.append("")
    if parsed.get("cards"):
        L += ["## Cards"] + [f"### {c['title']}\n{c['body']}\n" for c in parsed["cards"][:60]]
    if parsed.get("filings"):
        L += [f"## Docket filings ({parsed['filing_count']})"]
        for f in parsed["filings"]:
            L.append(f"- **#{f['filing']}** — {f['desc'][:300]}")
        L.append("")
    if parsed.get("text") and not parsed.get("filings"):
        L += ["## Text", parsed["text"][:40000]]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backlog", default="/mnt/c/Amd949609_Antigravity_v1/tools/task_system/automated_backlog.json")
    ap.add_argument("--srcdir", default="/mnt/c/OsintNeoAi/evidence/downloads_batch_ingest")
    ap.add_argument("--out", default="", help="output dir (default: <srcdir>/parsed_<date>)")
    ap.add_argument("--only", default="", help="comma-separated target substrings to process")
    args = ap.parse_args()

    outdir = args.out or os.path.join(args.srcdir, "parsed_" + datetime.now().strftime("%Y%m%d"))
    os.makedirs(outdir, exist_ok=True)

    # backup backlog (Law 14)
    if os.path.exists(args.backlog):
        bak = args.backlog + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(args.backlog, bak)
        print(f"[backup] {bak}")

    with open(args.backlog, encoding="utf-8") as f:
        raw = f.read()
    # File may be: JSON array + NDJSON tail (appended task records). Parse both.
    tail = ""
    try:
        backlog = json.loads(raw)
    except json.JSONDecodeError:
        dec = json.JSONDecoder()
        backlog, idx = dec.raw_decode(raw.lstrip())
        tail = raw.lstrip()[idx:].strip()
        print(f"[note] parsed JSON array + {len(tail.splitlines())} NDJSON tail line(s) preserved")

    only = [s.strip().lower() for s in args.only.split(",") if s.strip()]
    processed = 0
    quarantined = 0
    prior_ledger = trinity_hook.provenance_ledger_load(LEDGER) if HAS_TRINITY else {}
    ledger_rows = []
    for item in backlog:
        if item.get("status") != "queued":
            continue
        target = item.get("target", "")
        if only and not any(o in target.lower() for o in only):
            continue

        # locate file: srcdir, then visualizations, then downloads_import
        cands = [
            os.path.join(args.srcdir, target),
            os.path.join("/mnt/c/OsintNeoAi/evidence/visualizations", target),
            os.path.join("/mnt/c/OsintNeoAi/evidence/downloads_import", target),
        ]
        src = next((c for c in cands if os.path.exists(c)), None)
        if not src:
            print(f"[miss] {target} — not found in any candidate dir")
            item["status"] = "blocked_missing_file"
            continue

        ext = os.path.splitext(src)[1].lower()
        with open(src, encoding="utf-8", errors="ignore") as f:
            text = f.read()

        # ---- THE TRINITY GATE 1/2/3 on the artifact before it is indexed ----
        trinity = None
        if HAS_TRINITY:
            file_gate = trinity_hook.gate_file(src, prior_ledger=prior_ledger)
            url_gate = trinity_hook.gate_artifact(item.get("url") or target)
            trinity = {"file": file_gate, "artifact": url_gate}
            ledger_rows.append(file_gate)
            if file_gate["verdict"] == "QUARANTINE":
                item["status"] = "quarantined"
                item["quarantined_at"] = now_iso()
                item["trinity"] = trinity
                quarantined += 1
                print(f"[quarantine] {target} — {file_gate['required_actions'][:1]}")
                continue

        if ext in (".html", ".htm"):
            parsed = parse_html(text)
        elif "dockets.justia" in target:
            parsed = parse_docket_md(text)
        else:
            parsed = parse_md(text)

        base = os.path.splitext(os.path.basename(target))[0]
        pmd = os.path.join(outdir, base + ".parsed.md")
        pjs = os.path.join(outdir, base + ".parsed.json")
        with open(pmd, "w", encoding="utf-8") as f:
            f.write(render_md(target, parsed))
        with open(pjs, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=1, ensure_ascii=False)

        if trinity:
            parsed["trinity"] = trinity
            with open(pjs, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=1, ensure_ascii=False)
        item["status"] = "completed"
        item["completed_at"] = now_iso()
        item["outputs"] = [pmd, pjs]
        if trinity:
            item["trinity_verdict"] = trinity["artifact"]["verdict"]
            item["trinity_gates_failed"] = trinity["artifact"]["gates_failed"]
        processed += 1
        print(f"[done] {target} -> {os.path.basename(pmd)} "
              f"(tables={len(parsed.get('tables', []))}, "
              f"mermaid={len(parsed.get('mermaid', []))}, "
              f"filings={parsed.get('filing_count', 0)}, "
              f"headings={len(parsed.get('headings', []))})")

    with open(args.backlog, "w", encoding="utf-8") as f:
        f.write(json.dumps(backlog, indent=1, ensure_ascii=False))
        if tail:
            f.write("\n" + tail + "\n")

    if HAS_TRINITY and ledger_rows:
        trinity_hook.provenance_ledger_append(LEDGER, ledger_rows)
        print(f"[trinity] provenance ledger rows appended: {len(ledger_rows)} -> {LEDGER}")

    print(f"\nprocessed={processed} quarantined={quarantined} -> {outdir}")


if __name__ == "__main__":
    main()
