from decimal import Decimal

from pydantic import BaseModel


class PersonBalanceResponse(BaseModel):
    person: str
    paid_inr: Decimal
    owed_inr: Decimal
    net_balance_inr: Decimal


class BalanceTraceResponse(BaseModel):
    raw_row_number: int
    description: str
    paid_by: str
    participant: str
    expense_amount_inr: Decimal
    share_amount_inr: Decimal
    split_type: str
    row_status: str


class BalanceSkippedRowResponse(BaseModel):
    raw_row_number: int
    description: str
    row_status: str
    reason: str


class ImportBalanceResponse(BaseModel):
    group_id: int
    import_batch_id: int
    included_row_count: int
    excluded_row_count: int
    skipped_row_count: int
    balances: list[PersonBalanceResponse]
    traces: list[BalanceTraceResponse]
    skipped_rows: list[BalanceSkippedRowResponse]
