"""Robustness tests: varied real-world statement formats + connectors.

These simulate what actually lands from Indian banks — preamble junk rows,
different column names, 2-digit years, dd-MMM-yyyy dates, single Amount + Dr/Cr
columns, and .xlsx files — so we know LedgerFlow is ready for a real statement.
"""

import tempfile
import unittest
import zipfile
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
