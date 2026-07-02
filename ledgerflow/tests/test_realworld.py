"""Robustness tests: varied real-world statement formats + connectors.

These simulate what actually lands from Indian banks — preamble junk rows,
different column names, 2-digit years, dd-MMM-yyyy dates, single Amount + Dr/Cr
columns, and .xlsx files — so we know LedgerFlow is ready for a real statement.
"""

import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from ledgerflow import connectors, ingest
from ledgerflow.models import Direction


def _write(tmp: Path, name: str, text: str) -> Path:
    path = tmp / name
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def _col_letter(idx: int) -> str:
    letters = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _build_xlsx(path: Path, rows: list[list]) -> None:
    """Write a minimal but valid .xlsx (inline strings) using only stdlib."""
    def cell(r: int, c: int, value) -> str:
        ref = f"{_col_letter(c)}{r + 1}"
        if isinstance(value, (int, float)):
            return f'<c r="{ref}"><v>{value}</v></c>'
        if value == "" or value is None:
            return f'<c r="{ref}"/>'
        return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'

    sheet_rows = "".join(
        f'<row r="{r + 1}">' + "".join(cell(r, c, v) for c, v in enumerate(row)) + "</row>"
        for r, row in enumerate(rows)
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{sheet_rows}</sheetData></worksheet>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)


class TestRealWorldFormats(unittest.TestCase):
    def test_hdfc_style_preamble_and_two_digit_year(self):
        text = """
Statement of Account
Account No,50100XXXXXX
Period,01/04/24 to 30/04/24

Date,Narration,Chq/Ref No,Withdrawal Amt.,Deposit Amt.,Closing Balance
01/04/24,JIO PREPAID RECHARGE,BIL1,"999.00","","1,000.00"
02/04/24,SALARY INTEREST CREDIT,INT1,"","1,50,000.00","1,51,000.00"
"""
        with tempfile.TemporaryDirectory() as d:
            path = _write(Path(d), "hdfc.csv", text)
            txns = ingest.read_statement_auto(path)
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0].date, "2024-04-01")
        self.assertEqual(txns[0].direction, Direction.OUTFLOW)
        self.assertEqual(txns[1].direction, Direction.INFLOW)
        self.assertEqual(str(txns[1].amount), "150000.00")

    def test_icici_single_amount_with_drcr(self):
        text = """
Transaction Date,Transaction Remarks,Ref No,Amount,Dr/Cr,Balance
05-Apr-2024,UPI/SWIGGY/ORDER,UPI9,"850.00",DR,"49,150.00"
06-Apr-2024,NEFT CONSULTING FEE,NEFT9,"90,000.00",CR,"1,39,150.00"
"""
        with tempfile.TemporaryDirectory() as d:
            path = _write(Path(d), "icici.csv", text)
            txns = ingest.read_statement_auto(path)
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0].date, "2024-04-05")
        self.assertEqual(txns[0].direction, Direction.OUTFLOW)
        self.assertEqual(txns[1].direction, Direction.INFLOW)

    def test_xlsx_bank_statement(self):
        rows = [
            ["Date", "Narration", "Reference", "Debit", "Credit", "Balance"],
            ["01-Apr-2024", "JIO RECHARGE", "BIL1", 999, "", 1000],
            ["02-Apr-2024", "INTEREST CREDIT", "INT1", "", 50, 1050],
        ]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "statement.xlsx"
            _build_xlsx(path, rows)
            txns = ingest.read_statement_auto(path)
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0].narration, "JIO RECHARGE")
        self.assertEqual(txns[0].direction, Direction.OUTFLOW)
        self.assertEqual(txns[1].direction, Direction.INFLOW)

    def test_amounts_with_parentheses_negative(self):
        text = """
Date,Description,Amount
01/04/2024,ATM WITHDRAWAL,(10000.00)
02/04/2024,REFUND,2500.00
"""
        with tempfile.TemporaryDirectory() as d:
            path = _write(Path(d), "signed.csv", text)
            txns = ingest.read_statement_auto(path)
        self.assertEqual(txns[0].direction, Direction.OUTFLOW)
        self.assertEqual(txns[1].direction, Direction.INFLOW)


class TestPdfStatementParsing(unittest.TestCase):
    # Bank-of-Maharashtra-style lines: DATE PARTICULARS AMOUNT{Dr|Cr} BALANCE.
    LINES = [
        "STATEMENT OF ACCOUNT FOR THE PERIOD OF 05-06-2025 to 05-06-2026",
        "DATE PARTICULARS CHQ.NO. WITHDRAWALS DEPOSITS BALANCE",
        "31-05-2026 IMPS Charges/615123743570 5.90Dr 3,137.37",
        "31-05-2026 MB/IMPS/615123743570/VISHAL/UTIB/XXXXXX5072/Bill 40,000.00Dr 3,143.27",
        "31-05-2026 IMPS/615115089165/GANESH /KKBK/XXXXXX6048/RETUR 1,50,000.00Cr 1,54,155.07",
        "PAGE:1",
    ]

    def test_parses_only_transaction_rows(self):
        from ledgerflow.ingest import parse_statement_lines
        txns = parse_statement_lines(self.LINES)
        self.assertEqual(len(txns), 3)

    def test_drcr_suffix_sets_direction_and_amount(self):
        from ledgerflow.ingest import parse_statement_lines
        txns = parse_statement_lines(self.LINES)
        self.assertEqual(txns[0].direction, Direction.OUTFLOW)   # charges
        self.assertEqual(str(txns[0].amount), "5.90")
        self.assertEqual(txns[2].direction, Direction.INFLOW)    # 1,50,000 Cr
        self.assertEqual(str(txns[2].amount), "150000.00")

    def test_reference_extracted_from_narration(self):
        from ledgerflow.ingest import parse_statement_lines
        txns = parse_statement_lines(self.LINES)
        self.assertEqual(txns[1].reference, "615123743570")

    def test_counterparty_extraction_and_grouping(self):
        from ledgerflow.ingest import parse_statement_lines
        from ledgerflow import suspense
        txns = parse_statement_lines(self.LINES)
        self.assertEqual(suspense.extract_counterparty(txns[1].narration), "Vishal")
        # All three are unclassified here → grouped by party.
        for t in txns:
            t.status = "suspense"
        groups = suspense.group_review(txns)
        parties = {g["counterparty"] for g in groups}
        self.assertIn("Vishal", parties)
        self.assertIn("Ganesh", parties)


class TestPayeeClustering(unittest.TestCase):
    def test_whole_word_prefix_merges_but_partial_does_not(self):
        from ledgerflow import suspense
        rep = suspense.cluster_parties({"Kunal", "Kunal Dnyanoba", "Shreya", "Shreyash"})
        # 'Kunal' is a whole-word prefix of 'Kunal Dnyanoba' -> merged.
        self.assertEqual(rep["Kunal"], "Kunal Dnyanoba")
        # 'Shreya' is only a partial prefix of 'Shreyash' -> kept separate.
        self.assertNotEqual(rep["Shreya"], rep["Shreyash"])

    def test_grouping_collapses_truncated_duplicates(self):
        from ledgerflow.ingest import parse_statement_lines
        from ledgerflow import suspense
        lines = [
            "01-05-2026 MB/IMPS/611111111111/KUNAL/UTIB/XXXXXX3424/Bill 100.00Dr 900.00",
            "02-05-2026 MB/611111111112/XXXXXX6831/KUNAL DNYANOBA/Bill 200.00Dr 700.00",
        ]
        txns = parse_statement_lines(lines)
        for t in txns:
            t.status = "suspense"
        groups = suspense.group_review(txns)
        self.assertEqual(len(groups), 1)          # both Kunal lines -> one party
        self.assertEqual(groups[0]["count"], 2)


class TestLearningMemory(unittest.TestCase):
    def _txn(self, narration, ledger=None, rule=None):
        from ledgerflow.models import Direction, Transaction, TxnStatus
        t = Transaction(date="2026-05-01", narration=narration, amount=Decimal("100"),
                        direction=Direction.OUTFLOW, source="bank")
        t.status = TxnStatus.RESOLVED if ledger else TxnStatus.SUSPENSE
        t.ledger, t.matched_rule = ledger, rule
        return t

    def test_learn_then_apply_roundtrip(self):
        from ledgerflow import memory as mem
        from ledgerflow.models import TxnStatus
        answered = self._txn("MB/IMPS/1/VISHAL/UTIB/XXXXXX5072/Bill",
                             ledger="Sundry Creditors", rule="client-response")
        store: dict = {}
        self.assertEqual(mem.learn([answered], store), 1)
        # A fresh, unclassified Vishal transaction on a later statement:
        later = self._txn("MB/IMPS/2/VISHAL/UTIB/XXXXXX5072/Bill")
        self.assertEqual(mem.apply_memory([later], store), 1)
        self.assertEqual(later.status, TxnStatus.RESOLVED)
        self.assertEqual(later.ledger, "Sundry Creditors")
        self.assertEqual(later.matched_rule, "memory")

    def test_persist_and_reload(self):
        from ledgerflow import memory as mem
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "memory.json"
            mem.save_memory(path, {"vishal": "Sundry Creditors"})
            self.assertEqual(mem.load_memory(path), {"vishal": "Sundry Creditors"})

    def test_no_memory_file_is_empty(self):
        from ledgerflow import memory as mem
        self.assertEqual(mem.load_memory(None), {})


class TestHostedReviewRoundTrip(unittest.TestCase):
    LINES = [
        "01-05-2026 MB/IMPS/611111111111/KUNAL/UTIB/XXXXXX3424/Bill 100.00Dr 900.00",
        "02-05-2026 MB/611111111112/XXXXXX6831/KUNAL DNYANOBA/Bill 200.00Dr 700.00",
        "03-05-2026 MB/IMPS/611111111113/VISHAL/UTIB/XXXXXX5072/Bill 300.00Dr 400.00",
    ]

    def _suspense_txns(self):
        from ledgerflow.ingest import parse_statement_lines
        txns = parse_statement_lines(self.LINES)
        for t in txns:
            t.status = "suspense"
        return txns

    def test_group_key_answers_resolve_all_matching_txns(self):
        from ledgerflow import suspense
        txns = self._suspense_txns()
        groups = suspense.group_review(txns)
        key_by_name = {g["counterparty"]: g["key"] for g in groups}
        # Answer just the (merged) Kunal group -> both Kunal lines resolve.
        kunal_key = key_by_name[[n for n in key_by_name if "Kunal" in n][0]]
        resolved = suspense.apply_group_responses(
            txns, {kunal_key: "Sundry Creditors (paid a supplier)"})
        self.assertEqual(resolved, 2)
        kunal = [t for t in txns if "KUNAL" in t.narration.upper()]
        self.assertTrue(all(t.status == "resolved" for t in kunal))
        self.assertTrue(all(t.ledger == "Sundry Creditors" for t in kunal))
        self.assertEqual(kunal[0].matched_rule, "client-response")

    def test_load_group_responses_accepts_both_shapes(self):
        from ledgerflow import suspense
        with tempfile.TemporaryDirectory() as d:
            p1 = Path(d) / "a.json"; p1.write_text('{"answers":{"vishal":"Staff Welfare"}}')
            p2 = Path(d) / "b.json"; p2.write_text('{"vishal":"Staff Welfare"}')
            self.assertEqual(suspense.load_group_responses(p1), {"vishal": "Staff Welfare"})
            self.assertEqual(suspense.load_group_responses(p2), {"vishal": "Staff Welfare"})


class TestConnectors(unittest.TestCase):
    def setUp(self):
        sample = Path(__file__).resolve().parent.parent
        from ledgerflow import rules_engine
        self.txns = ingest.ingest_directory(sample / "sample_data")
        rules_engine.classify(self.txns, rules_engine.load_rules(sample / "rules.json"))

    def test_all_connectors_render_nonempty_files(self):
        for name in connectors.available():
            conn = connectors.get(name)
            artifacts = conn.render(self.txns, company="Test Co")
            self.assertTrue(artifacts, f"{name} produced no files")
            for filename, content in artifacts.items():
                self.assertTrue(content.strip(), f"{name}:{filename} was empty")

    def test_tally_is_the_only_push_connector(self):
        pushers = [n for n, _, can in connectors.describe() if can]
        self.assertEqual(pushers, ["tally"])

    def test_zoho_emits_two_journal_lines_per_voucher(self):
        csv_text = connectors.get("zoho_books").render(self.txns)["zoho_books_journals.csv"]
        data_lines = [ln for ln in csv_text.strip().splitlines()[1:] if ln]
        self.assertEqual(len(data_lines), len(self.txns) * 2)

    def test_unknown_connector_raises_helpful_error(self):
        with self.assertRaises(KeyError):
            connectors.get("sap")


if __name__ == "__main__":
    unittest.main()
