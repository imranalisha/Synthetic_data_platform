import datetime as dt
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ..core.money import q2
from .common import (CurrencyCode, Locale, Money, NonNegMoney, Rate, Seed, StrictModel)

TaxRate = Annotated[Decimal, Field(ge=0, le=1, max_digits=5, decimal_places=4)]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=3)]


class TaxRegion(str, Enum):
    US_CA = "US-CA"; US_NY = "US-NY"; US_TX = "US-TX"
    GB = "GB"; DE = "DE"; FR = "FR"; IN = "IN"; AE = "AE"; AU = "AU"; PK = "PK"


class DocumentExportFormat(str, Enum):
    PDF = "pdf"
    JSON = "json"


class Party(StrictModel):
    name: str = Field(max_length=120)
    address_lines: list[str] = Field(default_factory=list, max_length=5)
    tax_id: str | None = None
    email: str | None = None


# ------------------------------- Invoices -------------------------------------------------
class InvoiceRequest(StrictModel):
    region: TaxRegion = TaxRegion.US_CA
    locale: Locale | None = Field(None, description="Defaults to the region's locale.")
    currency: CurrencyCode | None = Field(None, description="Defaults to the region's currency.")
    seed: Seed | None = 42
    line_item_count: int = Field(5, ge=1, le=50)
    document_count: int = Field(1, ge=1, le=200, description=">1 exports as a ZIP of PDFs.")
    payment_terms_days: int = Field(30, ge=0, le=180)
    issue_date: dt.date | None = None
    template: Literal["classic", "modern", "minimal"] = "classic"
    seller: Party | None = None
    buyer: Party | None = None
    include_mixed_tax_rates: bool = Field(True, description="Allow reduced-rate lines where the region has them.")


class InvoiceExportRequest(InvoiceRequest):
    format: DocumentExportFormat = DocumentExportFormat.PDF


class InvoiceLineItem(StrictModel):
    description: str
    quantity: Quantity
    unit_price: Money
    line_net: Money
    tax_rate: TaxRate
    tax_amount: Money
    line_total: Money


class TaxBreakdownRow(StrictModel):
    tax_rate: TaxRate
    taxable_amount: Money
    tax_amount: Money


class InvoiceData(StrictModel):
    """Reconciliation contract. Rules (identical to the engine, via core.money):
    line_net = q2(qty*unit_price); tax_amount = q2(line_net*rate) PER LINE (half-up);
    subtotal = sum(line_net); tax_total = sum(line tax); grand_total = subtotal + tax_total."""
    invoice_number: str
    issue_date: dt.date
    due_date: dt.date
    region: TaxRegion
    currency: CurrencyCode
    tax_label: str = Field(description="e.g. 'Sales Tax', 'VAT', 'GST'")
    seller: Party
    buyer: Party
    line_items: list[InvoiceLineItem] = Field(min_length=1)
    tax_breakdown: list[TaxBreakdownRow]
    subtotal: Money
    tax_total: Money
    grand_total: Money

    @model_validator(mode="after")
    def _reconcile(self):
        if self.due_date < self.issue_date:
            raise ValueError("due_date precedes issue_date.")
        sub = tax = Decimal("0.00")
        by_rate: dict[Decimal, list[Decimal]] = {}
        for i, li in enumerate(self.line_items, 1):
            if li.line_net != q2(li.quantity * li.unit_price):
                raise ValueError(f"Line {i}: line_net != quantity * unit_price.")
            if li.tax_amount != q2(li.line_net * li.tax_rate):
                raise ValueError(f"Line {i}: tax_amount != line_net * tax_rate.")
            if li.line_total != li.line_net + li.tax_amount:
                raise ValueError(f"Line {i}: line_total != line_net + tax_amount.")
            sub += li.line_net
            tax += li.tax_amount
            b = by_rate.setdefault(li.tax_rate, [Decimal("0.00"), Decimal("0.00")])
            b[0] += li.line_net
            b[1] += li.tax_amount
        if self.subtotal != sub:
            raise ValueError("subtotal != sum(line_net).")
        if self.tax_total != tax:
            raise ValueError("tax_total != sum(line tax).")
        if self.grand_total != self.subtotal + self.tax_total:
            raise ValueError("grand_total != subtotal + tax_total.")
        given = {r.tax_rate: (r.taxable_amount, r.tax_amount) for r in self.tax_breakdown}
        if given != {k: (v[0], v[1]) for k, v in by_rate.items()}:
            raise ValueError("tax_breakdown does not match line items.")
        return self


class InvoiceBatchResponse(StrictModel):
    seed: int
    invoices: list[InvoiceData]


# ------------------------------- Bank statements -------------------------------------------
class BankStatementRequest(StrictModel):
    locale: Locale = Locale.EN_US
    currency: CurrencyCode = "USD"
    seed: Seed | None = 42
    opening_balance: Money = Decimal("5000.00")
    start_date: dt.date = dt.date(2026, 1, 1)
    end_date: dt.date = dt.date(2026, 1, 31)
    transaction_count: int = Field(40, ge=1, le=2000)
    credit_ratio: Rate = 0.3
    allow_overdraft: bool = False
    document_count: int = Field(1, ge=1, le=200)
    template: Literal["classic", "modern", "minimal"] = "classic"
    account_holder: Party | None = None
    bank_name: str | None = None

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date.")
        if (self.end_date - self.start_date).days > 366:
            raise ValueError("Statement period cannot exceed 366 days.")
        if not self.allow_overdraft and self.opening_balance < 0:
            raise ValueError("Negative opening_balance requires allow_overdraft=true.")
        return self


class BankStatementExportRequest(BankStatementRequest):
    format: DocumentExportFormat = DocumentExportFormat.PDF


class Transaction(StrictModel):
    posted_on: dt.date
    description: str
    reference: str
    debit: NonNegMoney = Decimal("0.00")
    credit: NonNegMoney = Decimal("0.00")
    balance: Money

    @model_validator(mode="after")
    def _one_side(self):
        if (self.debit > 0) == (self.credit > 0):
            raise ValueError("Exactly one of debit/credit must be non-zero.")
        return self


class BankStatementData(StrictModel):
    """balance[i] = balance[i-1] + credit[i] - debit[i]; balance[-1] == closing_balance."""
    statement_number: str
    bank_name: str
    account_holder: Party
    account_number: str
    iban: str | None = None
    currency: CurrencyCode
    period_start: dt.date
    period_end: dt.date
    overdraft_allowed: bool
    opening_balance: Money
    transactions: list[Transaction] = Field(min_length=1)
    total_debits: Money
    total_credits: Money
    closing_balance: Money

    @model_validator(mode="after")
    def _reconcile(self):
        running = self.opening_balance
        debits = credits = Decimal("0.00")
        prev = None
        for i, t in enumerate(self.transactions, 1):
            if prev and t.posted_on < prev:
                raise ValueError(f"Row {i}: transactions must be chronological.")
            if not (self.period_start <= t.posted_on <= self.period_end):
                raise ValueError(f"Row {i}: date outside statement period.")
            prev = t.posted_on
            running = running + t.credit - t.debit
            if t.balance != running:
                raise ValueError(f"Row {i}: running balance {t.balance} != expected {running}.")
            if not self.overdraft_allowed and running < 0:
                raise ValueError(f"Row {i}: overdraft while not allowed.")
            debits += t.debit
            credits += t.credit
        if self.total_debits != debits or self.total_credits != credits:
            raise ValueError("Totals do not match transactions.")
        if self.closing_balance != running or self.closing_balance != self.opening_balance + credits - debits:
            raise ValueError("closing_balance does not reconcile.")
        return self


class BankStatementBatchResponse(StrictModel):
    seed: int
    statements: list[BankStatementData]