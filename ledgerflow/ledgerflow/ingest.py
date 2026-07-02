"""Stage 1 — Ingestion.

Pull bank statements, credit-card exports, and tax-portal data from many
different real-world formats into one normalised list of ``Transaction``
objects.

Real bank statements are messy: different column names, different date
formats, junk/preamble rows before the header, separate Debit/Credit columns
*or* a single signed Amount column *or* an Amount + Dr/Cr flag, and files that
arrive as either CSV or Excel (.xlsx). The reader here auto-detects all of
that so you can feed it a statement straight from your bank.

In production the same normalised output would come from India's Account
Aggregator and GSTN APIs; the file readers simulate those feeds.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import re
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

from .models import Direction, Transaction

# --------------------------------------------------------------------------- #
# Low-level parsing helpers
# --------------------------------------------------------------------------- #

_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%d-%b-%Y", "%d/%b/%Y", "%d %b %Y", "%d-%b-%y", "%d %b %y",
    "%d-%B-%Y", "%d %B %Y",
    "%m/%d/%Y", "%m-%d-%Y",  # US-style, last resort
]


def _parse_date(raw: str) -> str | None:
    """Parse many date shapes into ISO YYYY-MM-DD, or return None."""
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    # Drop a trailing time component ("01-Apr-2024 12:00:00").
    value = value.split(" ")[0] if ":" in value else value
    for fmt in _DATE_FORMATS:
        try:
            return _dt.datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Excel serial date (days since 1899-12-30) stored as a bare number.
    if re.fullmatch(r"\d{4,6}(\.0+)?", value):
        try:
            serial = int(float(value))
            if 20000 <= serial <= 80000:  # ~1954..2119, a sane window
                base = _dt.date(1899, 12, 30)
                return (base + _dt.timedelta(days=serial)).strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            pass
    return None


def _parse_amount_cell(raw: str) -> tuple[Decimal, int]:
    """Parse a money cell → (absolute value, sign).

    Handles ``1,25,000.00``, ``(1,200.00)`` (a negative), a trailing ``Dr``/
    ``Cr``, ``₹`` and ``INR`` prefixes, and plain negatives. ``sign`` is
    ``-1`` for debit/negative, ``+1`` for credit/positive, ``0`` if unknown.
    """
    if raw is None:
        return Decimal("0"), 0
    text = str(raw).strip()
    if not text:
        return Decimal("0"), 0

    sign = 0
    low = text.lower()
    if re.search(r"\bdr\b", low) or low.endswith("dr"):
        sign = -1
    elif re.search(r"\bcr\b", low) or low.endswith("cr"):
        sign = 1
    if text.startswith("(") and text.endswith(")"):
        sign = -1
    if "-" in text and sign == 0:
        sign = -1

    cleaned = re.sub(r"[^0-9.]", "", text)
    if not cleaned or cleaned == ".":
        return Decimal("0"), sign
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0"), sign
    return value, sign


def _money(raw: str) -> Decimal:
    """Absolute money value for the simple two-column Debit/Credit case."""
    return _parse_amount_cell(raw)[0]


# --------------------------------------------------------------------------- #
# File readers → list of rows (each row a list of string cells)
# --------------------------------------------------------------------------- #

def _read_csv_rows(path: Path) -> list[list[str]]:
    # Sniff the delimiter; fall back to comma. Tolerate BOMs.
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    return [list(row) for row in csv.reader(text.splitlines(), dialect)]


def _col_index(ref: str) -> int:
    """Excel column ref ('B7') → zero-based column index."""
    letters = re.match(r"[A-Z]+", ref).group(0)
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _read_xlsx_rows(path: Path) -> list[list[str]]:
    """Minimal .xlsx reader using only the standard library."""
    def local(tag: str) -> str:
        return tag.split("}")[-1]

    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()

        # Shared strings table.
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root:
                shared.append("".join(
                    t.text or "" for t in si.iter() if local(t.tag) == "t"
                ))

        # First worksheet.
        sheets = sorted(n for n in names if n.startswith("xl/worksheets/") and n.endswith(".xml"))
        if not sheets:
            return []
        root = ET.fromstring(zf.read(sheets[0]))

        rows: list[list[str]] = []
        for row_el in root.iter():
            if local(row_el.tag) != "row":
                continue
            cells: dict[int, str] = {}
            for c in row_el:
                if local(c.tag) != "c":
                    continue
                ref = c.get("r", "A1")
                col = _col_index(ref)
                ctype = c.get("t")
                value = ""
                if ctype == "inlineStr":
                    value = "".join(
                        t.text or "" for t in c.iter() if local(t.tag) == "t"
                    )
                else:
                    v = next((e for e in c if local(e.tag) == "v"), None)
                    if v is not None and v.text is not None:
                        if ctype == "s":
                            try:
                                value = shared[int(v.text)]
                            except (ValueError, IndexError):
                                value = v.text
                        else:
                            value = v.text
                cells[col] = value
            width = (max(cells) + 1) if cells else 0
            rows.append([cells.get(i, "") for i in range(width)])
        return rows


def _read_rows(path: Path) -> list[list[str]]:
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        return _read_xlsx_rows(path)
    return _read_csv_rows(path)


# --------------------------------------------------------------------------- #
# Header detection + column mapping
# --------------------------------------------------------------------------- #

def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


# Fuzzy header aliases → logical column. Order matters (first hit wins).
_HEADER_ALIASES = {
    "date": ["transactiondate", "txndate", "valuedate", "postingdate", "date"],
    "desc": ["narration", "particulars", "description", "transactionremarks",
             "remarks", "details", "transactiondetails", "narrative"],
    "ref": ["chqrefno", "refnocchequeno", "referenceno", "reference",
            "chequeno", "refno", "utrno", "instrno"],
    "debit": ["withdrawalamt", "withdrawal", "debitamount", "debit", "dr",
              "paymentsdr", "withdrawals"],
    "credit": ["depositamt", "deposit", "creditamount", "credit", "cr",
               "receiptscr", "deposits"],
    "amount": ["amount", "transactionamount", "amt"],
    "drcr": ["drcr", "type", "transactiontype", "crdr", "debitcredit"],
    "balance": ["closingbalance", "balance", "runningbalance"],
}


def _detect_columns(header: list[str]) -> dict[str, int]:
    """Map logical columns to indices.

    Short aliases (``dr``/``cr``/``amt``) match only on an exact cell so they
    don't grab a combined ``Dr/Cr`` column; longer aliases may match as a
    substring. Each source column is claimed by at most one logical column.
    """
    norm_cells = [_norm(c) for c in header]
    mapping: dict[str, int] = {}
    used: set[int] = set()
    for logical, aliases in _HEADER_ALIASES.items():
        for alias in aliases:
            for idx, cell in enumerate(norm_cells):
                if idx in used:
                    continue
                exact = cell == alias
                fuzzy = len(alias) >= 4 and alias in cell and len(cell) <= len(alias) + 6
                if exact or fuzzy:
                    mapping[logical] = idx
                    used.add(idx)
                    break
            if logical in mapping:
                break
    return mapping


def _looks_like_header(row: list[str]) -> bool:
    cells = {_norm(c) for c in row}
    has_date = any("date" in c for c in cells)
    has_amount = any(
        any(tok in c for tok in ("amount", "debit", "credit", "withdrawal",
                                  "deposit", "amt"))
        for c in cells
    )
    has_desc = any(
        any(tok in c for tok in ("narration", "particular", "description",
                                 "remark", "detail"))
        for c in cells
    )
    return has_date and (has_amount or has_desc)


def _find_header(rows: list[list[str]]) -> int:
    for i, row in enumerate(rows[:40]):  # header is always near the top
        if _looks_like_header(row):
            return i
    return 0


# --------------------------------------------------------------------------- #
# The smart reader
# --------------------------------------------------------------------------- #

def read_statement_auto(
    path: str | Path,
    source: str = "bank",
    contra_ledger: str | None = None,
) -> list[Transaction]:
    """Read an arbitrary bank/card statement (CSV or XLSX) with auto-detection.

    Copes with preamble rows, varied headers, multiple amount layouts, and
    several date formats. Rows without a parseable date or amount are skipped
    (they are almost always sub-totals or blank separators).
    """
    path = Path(path)
    contra_ledger = contra_ledger or (
        "Credit Card" if source == "credit_card" else "Bank Account"
    )
    if path.suffix.lower() == ".pdf":
        return read_pdf_statement(path, source=source, contra_ledger=contra_ledger)
    rows = _read_rows(path)
    if not rows:
        return []

    header_idx = _find_header(rows)
    cols = _detect_columns(rows[header_idx])
    if "date" not in cols or "desc" not in cols:
        raise ValueError(
            f"Could not detect date/description columns in {path.name}. "
            f"Header row seen: {rows[header_idx]!r}"
        )
    has_two_col = "debit" in cols and "credit" in cols
    if not has_two_col and "amount" not in cols:
        raise ValueError(
            f"Could not detect amount columns in {path.name}. "
            f"Header row seen: {rows[header_idx]!r}"
        )

    def cell(row: list[str], key: str) -> str:
        idx = cols.get(key)
        if idx is None or idx >= len(row):
            return ""
        return row[idx]

    data_rows = rows[header_idx + 1:]

    # For a single-amount column with no Dr/Cr flag: if the column ever uses an
    # explicit negative (minus or parentheses), it follows the "+in / -out"
    # convention, so an unsigned positive means an inflow. Otherwise (a plain
    # spend column, e.g. a card statement) an unsigned value defaults to outflow.
    signed_column = False
    if not has_two_col and "drcr" not in cols:
        for row in data_rows:
            if _parse_amount_cell(cell(row, "amount"))[1] < 0:
                signed_column = True
                break

    txns: list[Transaction] = []
    for row in data_rows:
        if not any(str(c).strip() for c in row):
            continue
        iso = _parse_date(cell(row, "date"))
        if iso is None:
            continue

        if has_two_col:
            debit = _money(cell(row, "debit"))
            credit = _money(cell(row, "credit"))
            if debit > 0:
                amount, direction = debit, Direction.OUTFLOW
            elif credit > 0:
                amount, direction = credit, Direction.INFLOW
            else:
                continue  # zero row / carried balance
        else:
            amount, sign = _parse_amount_cell(cell(row, "amount"))
            if amount == 0:
                continue
            drcr = cell(row, "drcr").strip().lower()
            if drcr:
                is_out = any(t in drcr for t in ("dr", "debit", "withdraw", "w"))
                direction = Direction.OUTFLOW if is_out else Direction.INFLOW
            elif sign < 0:
                direction = Direction.OUTFLOW
            elif sign > 0:
                direction = Direction.INFLOW
            elif signed_column:
                direction = Direction.INFLOW  # positive in a signed column
            else:
                direction = Direction.OUTFLOW  # unsigned spend column, default

        narration = str(cell(row, "desc")).strip()
        txns.append(
            Transaction(
                date=iso,
                narration=narration,
                amount=amount,
                direction=direction,
                source=source,
                reference=str(cell(row, "ref")).strip(),
                contra_ledger=contra_ledger,
            )
        )
    return txns


# --------------------------------------------------------------------------- #
# Named readers (thin presets over the smart reader) + GST + directory
# --------------------------------------------------------------------------- #

def read_bank_statement(path: str | Path) -> list[Transaction]:
    """Read a bank statement (auto-detecting layout)."""
    return read_statement_auto(path, source="bank", contra_ledger="Bank Account")


def read_credit_card(path: str | Path) -> list[Transaction]:
    """Read a credit-card export (auto-detecting layout)."""
    return read_statement_auto(path, source="credit_card", contra_ledger="Credit Card")


# --------------------------------------------------------------------------- #
# PDF statements (text-layer PDFs, e.g. Bank of Maharashtra / most Indian banks)
# --------------------------------------------------------------------------- #

# A transaction row: DATE  PARTICULARS  [CHQ]  AMOUNT{Dr|Cr}  BALANCE
# The Dr/Cr suffix is attached to the amount (e.g. "40,000.00Dr").
_PDF_ROW_RE = re.compile(
    r"^(\d{2}[-/]\d{2}[-/]\d{4})\s+(.*?)\s+([\d,]+\.\d{2})\s*(Dr|Cr)\b\s+([\d,]+\.\d{2})\s*$",
    re.IGNORECASE,
)
_REF_RE = re.compile(r"(\d{9,18})")  # IMPS/NEFT/UTR-style reference numbers


def parse_statement_lines(
    lines: list[str], source: str = "bank", contra_ledger: str = "Bank Account"
) -> list[Transaction]:
    """Parse already-extracted PDF text lines into transactions.

    Factored out from PDF reading so it can be unit-tested without a PDF.
    """
    txns: list[Transaction] = []
    for raw in lines:
        m = _PDF_ROW_RE.match(str(raw).strip())
        if not m:
            continue
        date, narration, amount_str, drcr, _balance = m.groups()
        iso = _parse_date(date)
        if iso is None:
            continue
        value = _money(amount_str)
        if value == 0:
            continue
        direction = Direction.OUTFLOW if drcr.lower() == "dr" else Direction.INFLOW
        ref_match = _REF_RE.search(narration)
        txns.append(
            Transaction(
                date=iso,
                narration=narration.strip(),
                amount=value,
                direction=direction,
                source=source,
                reference=ref_match.group(1) if ref_match else "",
                contra_ledger=contra_ledger,
            )
        )
    return txns


def read_pdf_statement(
    path: str | Path,
    source: str = "bank",
    contra_ledger: str | None = None,
) -> list[Transaction]:
    """Read a text-layer PDF bank statement (needs the optional ``pypdf``)."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on optional dep
        raise RuntimeError(
            "PDF support requires 'pypdf'. Install it with:  pip install pypdf"
        ) from exc

    contra_ledger = contra_ledger or (
        "Credit Card" if source == "credit_card" else "Bank Account"
    )
    reader = PdfReader(str(path))
    lines: list[str] = []
    for page in reader.pages:
        lines.extend((page.extract_text() or "").splitlines())
    return parse_statement_lines(lines, source=source, contra_ledger=contra_ledger)


def read_gst_portal(path: str | Path) -> list[Transaction]:
    """Read tax-portal challans (simulating a GSTN feed) from JSON."""
    txns: list[Transaction] = []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for entry in data:
        txns.append(
            Transaction(
                date=_parse_date(str(entry["date"])) or str(entry["date"]),
                narration=f"GST {entry.get('type', 'Payment')} challan "
                f"{entry.get('challan_no', '')}".strip(),
                amount=_money(str(entry["amount"])),
                direction=Direction.OUTFLOW,
                source="gst_portal",
                reference=entry.get("challan_no", ""),
                contra_ledger="Bank Account",
            )
        )
    return txns


def ingest_directory(input_dir: str | Path) -> list[Transaction]:
    """Ingest every known feed found in ``input_dir`` and merge them.

    Looks for: bank_statement.csv, credit_card.csv, gst_portal.json.
    Missing files are simply skipped.
    """
    input_dir = Path(input_dir)
    readers = {
        "bank_statement.csv": read_bank_statement,
        "credit_card.csv": read_credit_card,
        "gst_portal.json": read_gst_portal,
    }
    txns: list[Transaction] = []
    for filename, reader in readers.items():
        path = input_dir / filename
        if path.exists():
            txns.extend(reader(path))
    return txns
