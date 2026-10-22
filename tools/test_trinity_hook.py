#!/usr/bin/env python3
"""Unit tests for trinity_hook.py — run: python3 -m unittest test_trinity_hook -v"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trinity_gate as tg   # noqa: E402
import trinity_hook as th   # noqa: E402


class TestSourceTiering(unittest.TestCase):
    def test_official_domains(self):
        for url in ("https://www.huntingtonbeachca.gov/permits",
                    "https://ca.courts.ca.gov/case",
                    "https://records.us/agency",
                    "https://records.cityofexample.gov/WebLink/DocView.aspx?id=1",
                    "https://laserfiche.cityofexample.org/WebLink/DocView.aspx?id=1",
                    "https://aca-prod.accela.com/HB/",
                    "https://someagency.accela.com/x"):
            self.assertEqual(th.tier_for_url(url), "official_record", url)

    def test_secondary_and_third_party(self):
        self.assertEqual(th.tier_for_url("https://dockets.justia.com/docket/ca9/1"), "official_secondary")
        self.assertEqual(th.tier_for_url("https://opencorporates.com/companies/us_ca/1"), "third_party_data")

    def test_social_and_unknown(self):
        self.assertEqual(th.tier_for_url("https://facebook.com/x"), "social_media")
        self.assertEqual(th.tier_for_url("https://example.com/x"), "unattributed")
        self.assertEqual(th.tier_for_url(""), "unattributed")


class TestFileGating(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "artifact.txt")
        with open(self.path, "w") as fh:
            fh.write("original content\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_file_accepted(self):
        r = th.gate_file(self.path)
        self.assertEqual(r["verdict"], tg.VERDICT_ACCEPT)
        self.assertEqual(len(r["sha256"]), 64)
        self.assertFalse(r["mutated_since_intake"])

    def test_mutation_triggers_quarantine(self):
        first = th.gate_file(self.path)
        ledger = {os.path.abspath(self.path): {"sha256": first["sha256"]}}
        with open(self.path, "w") as fh:
            fh.write("tampered content\n")
        second = th.gate_file(self.path, prior_ledger=ledger)
        self.assertEqual(second["verdict"], tg.VERDICT_QUARANTINE)
        self.assertIn("gate1", second["gates_failed"])
        self.assertTrue(second["mutated_since_intake"])

    def test_unchanged_file_stays_accepted(self):
        first = th.gate_file(self.path)
        ledger = {self.path: {"sha256": first["sha256"]}}
        second = th.gate_file(self.path, prior_ledger=ledger)
        self.assertEqual(second["verdict"], tg.VERDICT_ACCEPT)
        self.assertFalse(second["mutated_since_intake"])

    def test_missing_file_does_not_crash(self):
        r = th.gate_file(os.path.join(self.tmp.name, "nope.txt"))
        self.assertIsNone(r["sha256"])
        self.assertIn(r["verdict"], tg.SEVERITY)

    def test_non_image_has_no_gps(self):
        self.assertIsNone(th.exif_gps(self.path))


class TestArtifactGating(unittest.TestCase):
    def test_official_url_accepted(self):
        r = th.gate_artifact("https://www.huntingtonbeachca.gov/records/1")
        self.assertEqual(r["verdict"], tg.VERDICT_ACCEPT)
        self.assertEqual(r["source_tier"], "official_record")

    def test_social_url_needs_corroboration(self):
        r = th.gate_artifact("https://facebook.com/someone")
        self.assertEqual(r["verdict"], tg.VERDICT_CORROBORATE)

    def test_uncorroborated_claim_escalates_above_weak_source(self):
        r = th.gate_artifact("https://opencorporates.com/x", value=2_450_000,
                             baseline={"n": 42, "mean": 812_000, "stdev": 95_000})
        self.assertEqual(r["verdict"], tg.VERDICT_ESCALATE)

    def test_audit_lineage_present(self):
        r = th.gate_artifact("https://www.huntingtonbeachca.gov/x")
        self.assertTrue(r["rule_version"])
        self.assertGreater(r["posterior"], 0)


class TestProvenanceLedger(unittest.TestCase):
    def test_append_and_reload(self):
        with tempfile.TemporaryDirectory() as td:
            led = os.path.join(td, "ledger.csv")
            rows = [{"path": "/a/b.txt", "sha256": "x" * 64, "size": 1,
                     "observed_at": "2026-10-22T00:00:00Z", "verdict": "ACCEPT", "gates_failed": "[]"}]
            th.provenance_ledger_append(led, rows)
            loaded = th.provenance_ledger_load(led)
            self.assertIn("/a/b.txt", loaded)
            self.assertEqual(loaded["/a/b.txt"]["sha256"], "x" * 64)

    def test_append_empty_is_noop(self):
        with tempfile.TemporaryDirectory() as td:
            led = os.path.join(td, "l.csv")
            th.provenance_ledger_append(led, [])
            self.assertFalse(os.path.exists(led))

    def test_load_missing_file(self):
        self.assertEqual(th.provenance_ledger_load("/definitely/not/here.csv"), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
