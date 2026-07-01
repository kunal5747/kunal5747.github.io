"""End-to-end tests for the LedgerFlow pipeline (stdlib unittest)."""

import tempfile
import unittest
from pathlib import Path

from ledgerflow import ingest, rules_engine, suspense
from ledgerflow.export import to_tally_xml
from ledgerflow.models import Direction, TxnStatus
from ledgerflow.pipeline import run

_PKG_ROOT = Path(__file__).resolve().parent.parent
_SAMPLE = _PKG_ROOT / "sample_data"
_RULES = _PKG_ROOT / "rules.json"
_RESPONSES = _SAMPLE / "client_responses.json"


class TestIngestion(unittest.TestCase):
    def test_ingests_all_three_feeds(self):
        txns = ingest.ingest_directory(_SAMPLE)
        sources = {t.source for t in txns}
        self.assertEqual(sources, {"bank", "credit_card", "gst_portal"})
        self.assertEqual(len(txns), 35)

    def test_debit_is_outflow_credit_is_inflow(self):
        txns = ingest.read_bank_statement(_SAMPLE / "bank_statement.csv")
        swiggy = next(t for t in txns if "SWIGGY" in t.narration)
        interest = next(t for t in txns if "INTEREST" in t.narration)
        self.assertEqual(swiggy.direction, Direction.OUTFLOW)
        self.assertEqual(interest.direction, Direction.INFLOW)


class TestRulesEngine(unittest.TestCase):
    def setUp(self):
        self.txns = ingest.ingest_directory(_SAMPLE)
        rules_engine.classify(self.txns, rules_engine.load_rules(_RULES))

    def test_known_patterns_map_correctly(self):
        by_narr = {t.narration: t for t in self.txns}
        self.assertEqual(by_narr["UPI/SWIGGY/Order food"].ledger, "Staff Welfare")
        self.assertEqual(by_narr["JIO PREPAID RECHARGE"].ledger, "Telephone Expenses")

    def test_gst_source_rule_always_matches(self):
        gst = [t for t in self.txns if t.source == "gst_portal"]
        self.assertTrue(gst)
        self.assertTrue(all(t.ledger == "Duties & Taxes" for t in gst))

    def test_auto_rate_is_about_80_percent(self):
        auto = sum(1 for t in self.txns if t.status == TxnStatus.AUTO)
        rate = auto / len(self.txns)
        self.assertGreaterEqual(rate, 0.78)
        self.assertLessEqual(rate, 0.85)

    def test_vague_upi_goes_to_suspense(self):
        vague = next(t for t in self.txns if t.reference == "UPI/402910473821")
        self.assertEqual(vague.status, TxnStatus.SUSPENSE)
        self.assertIsNone(vague.ledger)


class TestSuspenseLoop(unittest.TestCase):
    def setUp(self):
        self.txns = ingest.ingest_directory(_SAMPLE)
        rules_engine.classify(self.txns, rules_engine.load_rules(_RULES))

    def test_flagging_builds_review_links(self):
        queue = suspense.flag_suspense(self.txns)
        self.assertTrue(queue)
        self.assertTrue(all(item["review_link"].startswith("https://") for item in queue))

    def test_client_responses_resolve_transactions(self):
        suspense.flag_suspense(self.txns)
        responses = suspense.load_responses(_RESPONSES)
        resolved = suspense.apply_responses(self.txns, responses)
        self.assertEqual(resolved, 3)
        supplier = next(t for t in self.txns if t.reference == "UPI/402910473821")
        self.assertEqual(supplier.status, TxnStatus.RESOLVED)
        self.assertEqual(supplier.ledger, "Sundry Creditors")


class TestExport(unittest.TestCase):
    def test_xml_has_balanced_vouchers(self):
        txns = ingest.read_bank_statement(_SAMPLE / "bank_statement.csv")
        rules_engine.classify(txns, rules_engine.load_rules(_RULES))
        xml = to_tally_xml(txns, company="Test Co")
        self.assertIn("<TALLYREQUEST>Import Data</TALLYREQUEST>", xml)
        # Each voucher has exactly two ledger entries (debit + credit).
        self.assertEqual(xml.count("<VOUCHER "), len(txns))
        self.assertEqual(xml.count("<ALLLEDGERENTRIES.LIST>"), len(txns) * 2)


class TestFullPipeline(unittest.TestCase):
    def test_run_writes_all_outputs_and_clean_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(
                input_dir=_SAMPLE,
                output_dir=tmp,
                rules_path=_RULES,
                responses_path=_RESPONSES,
                company="Test Co",
            )
            out = Path(tmp)
            for name in ("tally_import.xml", "daybook.csv",
                         "review_queue.json", "summary.json"):
                self.assertTrue((out / name).exists(), f"missing {name}")
            # After the suspense loop, clean rate should exceed the raw auto rate.
            self.assertGreater(result.stats["clean_rate"], result.stats["auto_rate"])
            self.assertEqual(result.stats["resolved_by_client"], 3)


if __name__ == "__main__":
    unittest.main()
