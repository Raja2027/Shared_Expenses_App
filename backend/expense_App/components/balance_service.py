from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from expense_App.components.group_service import GroupService
from expense_App.entity.models import ImportBatch, ImportRow, User
from expense_App.exception import NotFoundException
from expense_App.schemas.balance import (
    BalanceSkippedRowResponse,
    BalanceTraceResponse,
    ImportBalanceResponse,
    PersonBalanceResponse,
)


CENTS = Decimal("0.01")
CALCULABLE_ROW_STATUSES = {"ready_to_import", "approved_for_import"}


class BalanceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def calculate_import_balances(
        self,
        group_id: int,
        import_batch_id: int,
        current_user: User,
    ) -> ImportBalanceResponse:
        GroupService(self.db).get_owned_group(group_id, current_user)
        statement = (
            select(ImportBatch)
            .where(ImportBatch.id == import_batch_id, ImportBatch.group_id == group_id)
            .options(selectinload(ImportBatch.rows))
        )
        batch = self.db.execute(statement).scalar_one_or_none()
        if not batch:
            raise NotFoundException(
                message="Import batch was not found.",
                error_code="import_batch_not_found",
                details={"group_id": group_id, "import_batch_id": import_batch_id},
            )

        paid: dict[str, Decimal] = {}
        owed: dict[str, Decimal] = {}
        people: set[str] = set()
        traces: list[BalanceTraceResponse] = []
        skipped_rows: list[BalanceSkippedRowResponse] = []
        included_row_count = 0
        excluded_row_count = 0

        for row in sorted(batch.rows, key=lambda item: item.raw_row_number):
            data = row.normalized_data
            people.update(data.get("participants") or [])
            if data.get("paid_by_normalized"):
                people.add(data["paid_by_normalized"])

            if row.status not in CALCULABLE_ROW_STATUSES:
                excluded_row_count += 1
                continue

            row_traces, reason = self._build_row_traces(row)
            if reason:
                skipped_rows.append(
                    BalanceSkippedRowResponse(
                        raw_row_number=row.raw_row_number,
                        description=data.get("description_raw") or "",
                        row_status=row.status,
                        reason=reason,
                    )
                )
                continue

            included_row_count += 1
            payer = data["paid_by_normalized"]
            amount_inr = money(data["amount_inr"])
            paid[payer] = paid.get(payer, Decimal("0.00")) + amount_inr

            for trace in row_traces:
                traces.append(trace)
                owed[trace.participant] = (
                    owed.get(trace.participant, Decimal("0.00")) + trace.share_amount_inr
                )

        balances = [
            PersonBalanceResponse(
                person=person,
                paid_inr=paid.get(person, Decimal("0.00")).quantize(CENTS),
                owed_inr=owed.get(person, Decimal("0.00")).quantize(CENTS),
                net_balance_inr=(
                    paid.get(person, Decimal("0.00")) - owed.get(person, Decimal("0.00"))
                ).quantize(CENTS),
            )
            for person in sorted(people)
        ]

        return ImportBalanceResponse(
            group_id=group_id,
            import_batch_id=import_batch_id,
            included_row_count=included_row_count,
            excluded_row_count=excluded_row_count,
            skipped_row_count=len(skipped_rows),
            balances=balances,
            traces=traces,
            skipped_rows=skipped_rows,
        )

    def _build_row_traces(
        self,
        row: ImportRow,
    ) -> tuple[list[BalanceTraceResponse], str | None]:
        data = row.normalized_data
        amount_inr = money(data.get("amount_inr"))
        if amount_inr is None:
            return [], "Amount could not be converted to INR."
        if not data.get("paid_by_normalized"):
            return [], "Missing payer."

        split_type = data.get("split_type")
        participants = data.get("participants") or []
        details = data.get("split_details_parsed") or []

        if split_type == "equal":
            if not participants:
                return [], "Equal split has no participants."
            people = participants
            shares = allocate_weighted_amount(amount_inr, [Decimal("1")] * len(people))
        elif split_type == "share":
            people, weights = people_and_values(details)
            if not people or sum(weights) <= 0:
                return [], "Share split details are missing or invalid."
            shares = allocate_weighted_amount(amount_inr, weights)
        elif split_type == "percentage":
            people, percentages = people_and_values(details)
            if not people or sum(percentages) != Decimal("100"):
                return [], f"Percentage split sums to {sum(percentages) if percentages else 0}%, not 100%."
            shares = allocate_weighted_amount(amount_inr, percentages)
        elif split_type == "unequal":
            people, original_currency_amounts = people_and_values(details)
            fx_rate = money(data.get("fx_rate_to_inr"))
            if not people or fx_rate is None:
                return [], "Unequal split details or FX rate are missing."
            shares = [
                (share * fx_rate).quantize(CENTS, rounding=ROUND_HALF_UP)
                for share in original_currency_amounts
            ]
            if sum(shares) != amount_inr:
                return [], f"Unequal split sums to INR {sum(shares)}, amount is INR {amount_inr}."
        else:
            return [], f"Unsupported split type {split_type!r}."

        traces = [
            BalanceTraceResponse(
                raw_row_number=row.raw_row_number,
                description=data.get("description_raw") or "",
                paid_by=data["paid_by_normalized"],
                participant=person,
                expense_amount_inr=amount_inr,
                share_amount_inr=share,
                split_type=split_type,
                row_status=row.status,
            )
            for person, share in zip(people, shares)
        ]
        return traces, None


def money(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def people_and_values(details: list[dict[str, Any]]) -> tuple[list[str], list[Decimal]]:
    people = []
    values = []
    for detail in details:
        person = detail.get("person")
        value = detail.get("value")
        if not person or value is None:
            continue
        people.append(person)
        values.append(Decimal(str(value)))
    return people, values


def allocate_weighted_amount(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    if not weights or sum(weights) <= 0:
        return []

    sign = -1 if total < 0 else 1
    total_cents = int((abs(total) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    weight_total = sum(weights)
    exact_cents = [Decimal(total_cents) * weight / weight_total for weight in weights]
    base_cents = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in exact_cents]
    remainder = total_cents - sum(base_cents)

    ranked_indexes = sorted(
        range(len(weights)),
        key=lambda index: (exact_cents[index] - Decimal(base_cents[index]), -index),
        reverse=True,
    )
    for index in ranked_indexes[:remainder]:
        base_cents[index] += 1

    return [
        (Decimal(sign * cents) / Decimal(100)).quantize(CENTS)
        for cents in base_cents
    ]
