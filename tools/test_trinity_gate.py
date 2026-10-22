#!/usr/bin/env python3
"""Unit tests for trinity_gate.py — run: python3 -m unittest test_trinity_gate -v"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trinity_gate as tg  # noqa: E402

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)


def rec(**over):
    base = {
        "id": "t",
        "source": {"tier": "official_record"},
        "observed_at": "2026-10-20T09:00:00Z",
        "collected_at": "2026-10-21T00:00:00Z",
    }
    base.update(over)
    return base


class TestGate1Physics(unittest.TestCase):
    def test_clean_record_passes(self):
        g = tg.gate1_physics(rec(), now=NOW)
        self.assertTrue(g["passed"], g["violations"])

    def test_latitude_out_of_range(self):
        g = tg.gate1_physics(rec(location={"lat": 91.0, "lon": 0.0}), now=NOW)
        self.assertFalse(g["passed"])

    def test_longitude_out_of_range(self):
        g = tg.gate1_physics(rec(location={"lat": 0.0, "lon": -181.0}), now=NOW)
        self.assertFalse(g["passed"])

    def test_impossible_travel(self):
        g = tg.gate1_physics(rec(
            location={"lat": 33.6595, "lon": -117.9988},
            previous_location={"lat": 40.7128, "lon": -74.0060, "at": "2026-10-20T08:30:00Z"},
        ), now=NOW)
        self.assertFalse(g["passed"])
        self.assertTrue(any("travel speed" in v for v in g["violations"]))

    def test_feasible_travel(self):
        g = tg.gate1_physics(rec(
            location={"lat": 33.6595, "lon": -117.9988},
            previous_location={"lat": 33.7000, "lon": -118.1000, "at": "2026-10-20T08:00:00Z"},
        ), now=NOW)
        self.assertTrue(g["passed"], g["violations"])

    def test_same_place_same_time_is_not_a_violation(self):
        g = tg.gate1_physics(rec(
            location={"lat": 33.0, "lon": -117.0},
            previous_location={"lat": 33.0, "lon": -117.0, "at": "2026-10-20T09:00:00Z"},
        ), now=NOW)
        # dt == 0 but distance == 0 -> no contradiction
        self.assertTrue(g["passed"], g["violations"])

    def test_future_observation(self):
        g = tg.gate1_physics(rec(observed_at="2027-01-01T00:00:00Z"), now=NOW)
        self.assertFalse(g["passed"])

    def test_clock_skew_tolerated(self):
        g = tg.gate1_physics(rec(observed_at="2026-10-21T18:00:00Z",
                                 collected_at="2026-10-21T23:00:00Z"), now=NOW)  # +6h skew
        self.assertTrue(g["passed"], g["violations"])

    def test_collected_before_observed(self):
        g = tg.gate1_physics(rec(observed_at="2026-10-20T09:00:00Z",
                                 collected_at="2026-10-19T00:00:00Z"), now=NOW)
        self.assertFalse(g["passed"])

    def test_historical_date_allowed(self):
        g = tg.gate1_physics(rec(observed_at="1847-05-15", collected_at="2026-10-21"), now=NOW)
        self.assertTrue(g["passed"], g["violations"])
        self.assertTrue(any("historical" in n for n in g["notes"]))

    def test_pre_1000_rejected(self):
        g = tg.gate1_physics(rec(observed_at="0900-01-01", collected_at="2026-10-21"), now=NOW)
        self.assertFalse(g["passed"])

    def test_missing_mechanism_rejected(self):
        g = tg.gate1_physics(rec(requires_mechanism=True, mechanism="unknown"), now=NOW)
        self.assertFalse(g["passed"])

    def test_mechanism_supplied_passes(self):
        g = tg.gate1_physics(rec(requires_mechanism=True, mechanism="gravity, tide tables"), now=NOW)
        self.assertTrue(g["passed"], g["violations"])

    def test_hash_mismatch(self):
        g = tg.gate1_physics(rec(sha256="a" * 64, payload_sha256="b" * 64), now=NOW)
        self.assertFalse(g["passed"])

    def test_unparseable_timestamp(self):
        g = tg.gate1_physics(rec(observed_at="not a date"), now=NOW)
        self.assertFalse(g["passed"])


class TestGate2Probability(unittest.TestCase):
    def test_official_record_alone_passes(self):
        self.assertTrue(tg.gate2_probability(rec())["passed"])

    def test_anonymous_tip_alone_fails(self):
        g = tg.gate2_probability({"source": {"tier": "anonymous_tip"}})
        self.assertFalse(g["passed"])

    def test_tip_with_independent_official_corroboration_passes(self):
        g = tg.gate2_probability({
            "source": {"tier": "anonymous_tip"},
            "corroborations": [{"tier": "official_record", "independent": True}],
        })
        self.assertTrue(g["passed"])

    def test_non_independent_corroboration_ignored(self):
        g = tg.gate2_probability({
            "source": {"tier": "social_media"},
            "corroborations": [{"tier": "official_record", "independent": False}] * 5,
        })
        self.assertFalse(g["passed"])
        self.assertTrue(any("ignored" in str(x) for x in g["likelihood_ratios"]))

    def test_unknown_tier_uses_default_prior(self):
        g = tg.gate2_probability({"source": {"tier": "totally-made-up"}})
        self.assertEqual(g["prior"], tg.DEFAULT_TIER_PRIOR)

    def test_explicit_reliability_override(self):
        g = tg.gate2_probability({"source": {"reliability": 0.9}})
        self.assertAlmostEqual(g["prior"], 0.9, places=3)

    def test_posterior_monotonic_in_corroboration(self):
        a = tg.gate2_probability({"source": {"tier": "third_party_data"}})["posterior"]
        b = tg.gate2_probability({
            "source": {"tier": "third_party_data"},
            "corroborations": [{"tier": "official_record", "independent": True}],
        })["posterior"]
        self.assertGreater(b, a)


class TestGate3Baseline(unittest.TestCase):
    def test_not_applicable_without_baseline(self):
        self.assertFalse(tg.gate3_baseline({"value": 5})["applicable"])

    def test_within_band_passes(self):
        g = tg.gate3_baseline({"value": 10.5, "baseline": {"n": 40, "mean": 10.0, "stdev": 1.0}})
        self.assertTrue(g["passed"])

    def test_outlier_flagged(self):
        g = tg.gate3_baseline({"value": 20.0, "baseline": {"n": 40, "mean": 10.0, "stdev": 1.0}})
        self.assertFalse(g["passed"])
        self.assertGreater(abs(g["z_score"]), tg.GATE3_Z_LIMIT)

    def test_small_sample_baseline_untrusted(self):
        g = tg.gate3_baseline({"value": 99.0, "baseline": {"n": 2, "mean": 10.0, "stdev": 1.0}})
        self.assertFalse(g["applicable"])

    def test_zero_variance_constant_baseline(self):
        same = tg.gate3_baseline({"value": 7, "baseline": {"n": 10, "mean": 7, "stdev": 0}})
        diff = tg.gate3_baseline({"value": 8, "baseline": {"n": 10, "mean": 7, "stdev": 0}})
        self.assertTrue(same["passed"])
        self.assertFalse(diff["passed"])


class TestPipeline(unittest.TestCase):
    def test_verdict_precedence_quarantine_wins(self):
        v = tg.evaluate({"id": "x", "source": {"tier": "anonymous_tip"},
                         "location": {"lat": 99, "lon": 0},
                         "observed_at": "2026-10-20T09:00:00Z",
                         "collected_at": "2026-10-21T00:00:00Z"}, now=NOW)
        self.assertEqual(v.verdict, tg.VERDICT_QUARANTINE)

    def test_accuracy_and_audit_are_separate_axes(self):
        v = tg.evaluate(rec(), now=NOW)
        self.assertIn("gates", v.accuracy)
        self.assertIn("rule_version", v.audit)
        self.assertIn("record_snapshot", v.audit)
        self.assertEqual(len(v.audit["record_sha256"]), 64)

    def test_recheck_can_upgrade_verdict(self):
        v = tg.evaluate({"id": "r", "source": {"tier": "anonymous_tip"},
                         "observed_at": "2026-10-20T09:00:00Z",
                         "collected_at": "2026-10-21T00:00:00Z"}, now=NOW)
        self.assertEqual(v.verdict, tg.VERDICT_CORROBORATE)
        v2 = tg.recheck(v, new_corroborations=[{"tier": "official_record", "independent": True}])
        self.assertEqual(v2.verdict, tg.VERDICT_ACCEPT)

    def test_recheck_never_destroys_record(self):
        v = tg.evaluate(rec(), now=NOW)
        v2 = tg.recheck(v)
        self.assertEqual(v2.audit["record_snapshot"], v.audit["record_snapshot"])


class TestIO(unittest.TestCase):
    def test_batch_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "in.jsonl")
            with open(src, "w") as fh:
                fh.write(json.dumps(rec(id="a")) + "\n")
                fh.write(json.dumps({"id": "b", "source": {"tier": "anonymous_tip"},
                                     "observed_at": "2026-10-20T09:00:00Z",
                                     "collected_at": "2026-10-21T00:00:00Z"}) + "\n")
                fh.write("not json\n")
            out = os.path.join(td, "out.jsonl")
            rc = tg.main(["--input", src, "--out", out])
            self.assertEqual(rc, 0)
            lines = [json.loads(l) for l in open(out)]
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[0]["verdict"], tg.VERDICT_ACCEPT)
            self.assertEqual(lines[1]["verdict"], tg.VERDICT_CORROBORATE)

    def test_selftest_passes(self):
        self.assertEqual(tg.cmd_selftest(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestCombinedGateActions(unittest.TestCase):
    def test_weak_source_outlier_reports_both_actions(self):
        v = tg.evaluate({
            "id": "combined",
            "source": {"tier": "third_party_data"},
            "observed_at": "2026-10-20T09:00:00Z",
            "collected_at": "2026-10-21T00:00:00Z",
            "value": 2450000,
            "baseline": {"n": 42, "mean": 812000, "stdev": 95000},
        }, now=NOW)
        self.assertEqual(v.verdict, tg.VERDICT_ESCALATE)
        self.assertEqual(sorted(v.accuracy["gates_failed"]), ["gate2", "gate3"])
        self.assertEqual(len(v.accuracy["required_actions"]), 2)

    def test_severity_ordering_is_monotonic(self):
        self.assertGreater(tg.SEVERITY["QUARANTINE"], tg.SEVERITY["ESCALATE_HIGH_SCRUTINY"])
        self.assertGreater(tg.SEVERITY["ESCALATE_HIGH_SCRUTINY"], tg.SEVERITY["FLAG_CORROBORATE"])
        self.assertGreater(tg.SEVERITY["FLAG_CORROBORATE"], tg.SEVERITY["ACCEPT"])
