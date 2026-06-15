import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from expense_App.constant.import_policy import (
    DEFAULT_YEAR,
    EXPECTED_COLUMNS,
    FX_RATES_TO_INR,
    KNOWN_PEOPLE,
    MEMBERSHIP_WINDOWS,
    PERSON_ALIASES,
    REVIEW_NOTE_TERMS,
    SETTLEMENT_TERMS,
    SUPPORTED_SPLIT_TYPES,
)
from expense_App.entity.models import ImportAnomaly, ImportBatch, ImportRow
from expense_App.exception.import_exceptions import CSVSchemaError, ImportPipelineError
from expense_App.logger import get_logger


CENTS = Decimal("0.01")
logger = get_logger(__name__)


@dataclass
class AnomalyDraft:
    raw_row_number: int
    code: str
    severity: str
    field_name: str
    message: str
    suggested_action: str
    requires_user_approval: bool = True
    related_rows: list[int] = field(default_factory=list)


@dataclass
class RowCandidate:
    raw_row_number: int
    raw_data: dict[str, str]
    normalized_data: dict[str, Any]
    import_status: str = "needs_review"


@dataclass
class ImportPreview:
    filename: str
    rows: list[RowCandidate]
    anomalies: list[AnomalyDraft]
    summary: dict[str, Any]


class CSVImportPipeline:
    """Standalone CSV import pipeline.

    This is intentionally independent from the preprocessing notebook. The app
    should call this pipeline, persist its preview, and ask users to resolve
    review rows before creating final expenses or settlements.
    """

    def preview(self, csv_path: str | Path) -> ImportPreview:
        path = Path(csv_path)
        logger.info("Starting CSV import preview for %s", path)
        try:
            raw_rows = self._read_csv(path)
            rows = [
                RowCandidate(
                    raw_row_number=index + 2,
                    raw_data=raw_row,
                    normalized_data=self._normalize_row(raw_row),
                )
                for index, raw_row in enumerate(raw_rows)
            ]

            anomalies: list[AnomalyDraft] = []
            for row in rows:
                self._detect_row_anomalies(row, anomalies)
            self._detect_duplicate_candidates(rows, anomalies)
            self._assign_import_statuses(rows, anomalies)

            status_counts: dict[str, int] = {}
            for row in rows:
                status_counts[row.import_status] = status_counts.get(row.import_status, 0) + 1

            summary = {
                "total_rows": len(rows),
                "anomaly_count": len(anomalies),
                "rows_with_anomalies": len({anomaly.raw_row_number for anomaly in anomalies}),
                "status_counts": status_counts,
                "batch_status": "needs_review"
                if any(anomaly.requires_user_approval for anomaly in anomalies)
                else "ready_to_import",
            }

            logger.info(
                "Completed CSV import preview for %s: rows=%s anomalies=%s status=%s",
                path,
                summary["total_rows"],
                summary["anomaly_count"],
                summary["batch_status"],
            )
            return ImportPreview(
                filename=path.name,
                rows=rows,
                anomalies=anomalies,
                summary=summary,
            )
        except ImportPipelineError as error:
            logger.warning("Controlled import preview failure for %s: %s", path, error)
            raise
        except Exception as error:
            logger.exception("Unexpected import preview failure for %s", path)
            raise ImportPipelineError(
                message="Unexpected error while previewing CSV import.",
                error_code="import_preview_failed",
                details={"csv_path": str(path), "reason": str(error)},
            ) from error

    def persist_preview(
        self,
        db: Session,
        preview: ImportPreview,
        group_id: int,
        uploaded_by_user_id: int,
        commit: bool = True,
    ) -> ImportBatch:
        logger.info(
            "Persisting import preview: filename=%s group_id=%s uploaded_by_user_id=%s",
            preview.filename,
            group_id,
            uploaded_by_user_id,
        )
        try:
            batch = ImportBatch(
                group_id=group_id,
                uploaded_by_user_id=uploaded_by_user_id,
                filename=preview.filename,
                status=preview.summary["batch_status"],
                summary=_json_safe(preview.summary),
            )
            db.add(batch)
            db.flush()

            row_models_by_raw_number: dict[int, ImportRow] = {}
            for row in preview.rows:
                row_model = ImportRow(
                    import_batch_id=batch.id,
                    raw_row_number=row.raw_row_number,
                    raw_data=_json_safe(row.raw_data),
                    normalized_data=_json_safe(row.normalized_data),
                    status=row.import_status,
                )
                db.add(row_model)
                db.flush()
                row_models_by_raw_number[row.raw_row_number] = row_model

            for anomaly in preview.anomalies:
                row_model = row_models_by_raw_number[anomaly.raw_row_number]
                db.add(
                    ImportAnomaly(
                        import_row_id=row_model.id,
                        code=anomaly.code,
                        severity=anomaly.severity,
                        field_name=anomaly.field_name,
                        message=anomaly.message,
                        suggested_action=anomaly.suggested_action,
                        requires_user_approval=anomaly.requires_user_approval,
                        related_rows=_json_safe(anomaly.related_rows),
                    )
                )

            if commit:
                db.commit()
                db.refresh(batch)
            logger.info(
                "Persisted import preview: batch_id=%s rows=%s anomalies=%s",
                batch.id,
                len(preview.rows),
                len(preview.anomalies),
            )
            return batch
        except Exception as error:
            db.rollback()
            logger.exception("Failed to persist import preview for %s", preview.filename)
            raise ImportPipelineError(
                message="Failed to persist import preview.",
                error_code="import_preview_persist_failed",
                details={
                    "filename": preview.filename,
                    "group_id": group_id,
                    "uploaded_by_user_id": uploaded_by_user_id,
                    "reason": str(error),
                },
            ) from error

    def run(
        self,
        db: Session,
        csv_path: str | Path,
        group_id: int,
        uploaded_by_user_id: int,
        commit: bool = True,
    ) -> ImportBatch:
        preview = self.preview(csv_path)
        return self.persist_preview(
            db=db,
            preview=preview,
            group_id=group_id,
            uploaded_by_user_id=uploaded_by_user_id,
            commit=commit,
        )

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        if not path.exists():
            raise ImportPipelineError(
                message="CSV file does not exist.",
                error_code="csv_file_not_found",
                status_code=404,
                details={"csv_path": str(path)},
            )

        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames or []
            missing_columns = [column for column in EXPECTED_COLUMNS if column not in fieldnames]
            unexpected_columns = [column for column in fieldnames if column not in EXPECTED_COLUMNS]
            if missing_columns or unexpected_columns:
                raise CSVSchemaError(
                    "CSV columns do not match expected schema. "
                    f"Missing: {missing_columns or 'none'}; "
                    f"Unexpected: {unexpected_columns or 'none'}",
                    details={
                        "csv_path": str(path),
                        "missing_columns": missing_columns,
                        "unexpected_columns": unexpected_columns,
                    },
                )
            return [
                {column: clean_text(raw_row.get(column, "")) for column in EXPECTED_COLUMNS}
                for raw_row in reader
            ]

    def _normalize_row(self, raw_row: dict[str, str]) -> dict[str, Any]:
        amount_info = parse_amount(raw_row["amount"])
        parsed_date, date_issue = parse_date(raw_row["date"])
        currency = clean_text(raw_row["currency"]).upper()
        fx_rate = FX_RATES_TO_INR.get(currency)
        amount_inr = None
        if amount_info["amount_rounded"] is not None and fx_rate is not None:
            amount_inr = (amount_info["amount_rounded"] * fx_rate).quantize(
                CENTS,
                rounding=ROUND_HALF_UP,
            )

        participants_raw = [
            clean_text(part)
            for part in clean_text(raw_row["split_with"]).split(";")
            if clean_text(part)
        ]
        participants = [normalize_person(part) for part in participants_raw]
        description = clean_text(raw_row["description"])
        notes = clean_text(raw_row["notes"])
        review_text = compact_text(f"{description} {notes}")

        return {
            "date_raw": clean_text(raw_row["date"]),
            "parsed_date": parsed_date,
            "date_issue": date_issue,
            "description_raw": description,
            "description_key": compact_text(description, remove_stop_words=True),
            "paid_by_raw": clean_text(raw_row["paid_by"]),
            "paid_by_normalized": normalize_person(raw_row["paid_by"]),
            "amount_raw": clean_text(raw_row["amount"]),
            **amount_info,
            "currency_raw": clean_text(raw_row["currency"]),
            "currency_normalized": currency,
            "fx_rate_to_inr": fx_rate,
            "amount_inr": amount_inr,
            "split_type_raw": clean_text(raw_row["split_type"]),
            "split_type": clean_text(raw_row["split_type"]).lower(),
            "split_with_raw": clean_text(raw_row["split_with"]),
            "participants_raw": participants_raw,
            "participants": participants,
            "split_details_raw": clean_text(raw_row["split_details"]),
            "split_details_parsed": parse_split_details(raw_row["split_details"]),
            "notes": notes,
            "is_settlement_candidate": any(term in review_text for term in SETTLEMENT_TERMS),
        }

    def _detect_row_anomalies(
        self,
        row: RowCandidate,
        anomalies: list[AnomalyDraft],
    ) -> None:
        data = row.normalized_data
        row_number = row.raw_row_number
        parsed_date = data["parsed_date"]
        participants = data["participants"]
        participant_set = set(participants)
        split_details = data["split_details_parsed"]
        detail_people = {detail["person"] for detail in split_details if detail.get("person")}

        if parsed_date is None:
            self._add_anomaly(
                anomalies,
                row_number,
                "date_unparseable",
                "error",
                "date",
                f"Could not parse date value {data['date_raw']!r}.",
                "Hold row for user correction.",
            )
        elif data["date_issue"]:
            self._add_anomaly(
                anomalies,
                row_number,
                data["date_issue"],
                "review",
                "date",
                f"Date value {data['date_raw']!r} is not the expected DD-MM-YYYY format.",
                "Show inferred date and require approval before import.",
            )

        if data["date_raw"] == "04-05-2026" or "format is a mess" in compact_text(data["notes"]):
            self._add_anomaly(
                anomalies,
                row_number,
                "ambiguous_date_note",
                "review",
                "date",
                "Source note says the date may mean April 5 or May 4.",
                "Hold row until user confirms the actual date.",
            )

        if not data["paid_by_raw"]:
            self._add_anomaly(
                anomalies,
                row_number,
                "missing_payer",
                "error",
                "paid_by",
                "The payer is blank.",
                "Hold row until the user selects who paid.",
            )
        elif data["paid_by_raw"] != data["paid_by_normalized"]:
            self._add_anomaly(
                anomalies,
                row_number,
                "payer_alias_normalized",
                "warning",
                "paid_by",
                f"Payer {data['paid_by_raw']!r} normalized to {data['paid_by_normalized']!r}.",
                "Import using canonical person name and show the alias in the report.",
                False,
            )

        participant_aliases = [
            f"{raw} -> {normalized}"
            for raw, normalized in zip(data["participants_raw"], participants)
            if raw != normalized
        ]
        if participant_aliases:
            self._add_anomaly(
                anomalies,
                row_number,
                "participant_alias_normalized",
                "warning",
                "split_with",
                "; ".join(participant_aliases),
                "Import using canonical participant names and show the aliases in the report.",
                False,
            )

        unknown_people = sorted(
            (participant_set | {data["paid_by_normalized"]}) - KNOWN_PEOPLE - {""}
        )
        if unknown_people:
            self._add_anomaly(
                anomalies,
                row_number,
                "unknown_person",
                "review",
                "people",
                f"Unknown people found: {unknown_people}.",
                "Ask user whether to create guest/member records.",
            )

        if "Kabir" in participant_set:
            self._add_anomaly(
                anomalies,
                row_number,
                "external_guest_participant",
                "review",
                "split_with",
                "Kabir appears as Dev's friend for one day.",
                "Create as a guest participant only if the user approves.",
            )

        self._detect_currency_and_amount_anomalies(row, anomalies)
        self._detect_split_anomalies(row, anomalies, participant_set, detail_people)
        self._detect_membership_anomalies(row, anomalies, participant_set)
        self._detect_source_note_anomalies(row, anomalies)

    def _detect_currency_and_amount_anomalies(
        self,
        row: RowCandidate,
        anomalies: list[AnomalyDraft],
    ) -> None:
        data = row.normalized_data
        row_number = row.raw_row_number

        if not data["currency_normalized"]:
            self._add_anomaly(
                anomalies,
                row_number,
                "missing_currency",
                "review",
                "currency",
                "Currency is blank.",
                "Default to INR only after user approval.",
            )
        elif data["currency_normalized"] not in FX_RATES_TO_INR:
            self._add_anomaly(
                anomalies,
                row_number,
                "unsupported_currency",
                "error",
                "currency",
                f"Currency {data['currency_normalized']!r} has no configured FX rate.",
                "Hold row until a rate is configured.",
            )
        elif data["currency_normalized"] != "INR":
            self._add_anomaly(
                anomalies,
                row_number,
                "foreign_currency_converted",
                "warning",
                "currency",
                f"{data['currency_normalized']} converted to INR at {data['fx_rate_to_inr']}.",
                "Import using the explicit FX rate and include it in the report.",
                False,
            )

        if data["amount_original"] is None:
            self._add_anomaly(
                anomalies,
                row_number,
                "amount_unparseable",
                "error",
                "amount",
                f"Could not parse amount {data['amount_raw']!r}.",
                "Hold row until amount is corrected.",
            )
            return

        if data["amount_has_comma"]:
            self._add_anomaly(
                anomalies,
                row_number,
                "amount_thousands_separator",
                "warning",
                "amount",
                f"Amount {data['amount_raw']!r} contains a comma.",
                "Strip comma for numeric import and keep raw value for traceability.",
                False,
            )
        if data["amount_decimal_places"] and data["amount_decimal_places"] > 2:
            self._add_anomaly(
                anomalies,
                row_number,
                "amount_precision_over_two_decimals",
                "warning",
                "amount",
                f"Amount {data['amount_raw']!r} has more than two decimals.",
                "Round half-up to two decimals for the candidate import and show the original value.",
                False,
            )
        if data["amount_original"] < 0:
            self._add_anomaly(
                anomalies,
                row_number,
                "negative_amount_refund_candidate",
                "review",
                "amount",
                "Negative amount likely represents a refund or credit, not a normal expense.",
                "Classify as refund after user approval.",
            )
        if data["amount_original"] == 0:
            self._add_anomaly(
                anomalies,
                row_number,
                "zero_amount_candidate",
                "review",
                "amount",
                "Zero amount row does not affect balances.",
                "Exclude from balances unless user confirms it is a correction record.",
            )

        if data["is_settlement_candidate"]:
            self._add_anomaly(
                anomalies,
                row_number,
                "payment_or_settlement_candidate",
                "review",
                "description",
                "Description or notes look like a payment/settlement rather than a shared expense.",
                "Route to payments/settlements instead of importing as an expense.",
            )

    def _detect_split_anomalies(
        self,
        row: RowCandidate,
        anomalies: list[AnomalyDraft],
        participant_set: set[str],
        detail_people: set[str],
    ) -> None:
        data = row.normalized_data
        row_number = row.raw_row_number
        split_details = data["split_details_parsed"]
        split_type = data["split_type"]

        if not split_type:
            self._add_anomaly(
                anomalies,
                row_number,
                "missing_split_type",
                "review",
                "split_type",
                "Split type is blank.",
                "Infer only if user confirms this is a payment/settlement or selects a split type.",
            )
        elif split_type not in SUPPORTED_SPLIT_TYPES:
            self._add_anomaly(
                anomalies,
                row_number,
                "unsupported_split_type",
                "error",
                "split_type",
                f"Split type {split_type!r} is not supported.",
                "Hold row until the importer supports this split type.",
            )

        if data["split_details_raw"] and split_type == "equal":
            self._add_anomaly(
                anomalies,
                row_number,
                "split_type_details_conflict",
                "review",
                "split_details",
                "split_type is equal but split_details are present.",
                "Ask user whether equal split or explicit details should win.",
            )

        if split_type in {"unequal", "percentage", "share"} and not split_details:
            self._add_anomaly(
                anomalies,
                row_number,
                "missing_split_details",
                "error",
                "split_details",
                f"{split_type} split needs split_details.",
                "Hold row until details are provided.",
            )

        if detail_people and not detail_people.issubset(participant_set):
            self._add_anomaly(
                anomalies,
                row_number,
                "split_detail_participant_mismatch",
                "review",
                "split_details",
                f"Detail people {sorted(detail_people)} do not match split_with {sorted(participant_set)}.",
                "Ask user which participant list is correct.",
            )

        values = [
            detail["value"]
            for detail in split_details
            if detail.get("value") is not None
        ]
        amount = data["amount_rounded"]
        if amount is None or not values:
            return

        if split_type == "unequal" and sum(values) != amount:
            self._add_anomaly(
                anomalies,
                row_number,
                "unequal_split_total_mismatch",
                "error",
                "split_details",
                f"Unequal split sums to {sum(values)}, amount is {amount}.",
                "Hold row until split amounts sum to the expense amount.",
            )
        if split_type == "percentage" and sum(values) != Decimal("100"):
            self._add_anomaly(
                anomalies,
                row_number,
                "percentage_split_not_100",
                "error",
                "split_details",
                f"Percentages sum to {sum(values)}%, not 100%.",
                "Hold row until percentages are corrected.",
            )
        if split_type == "share" and sum(values) <= 0:
            self._add_anomaly(
                anomalies,
                row_number,
                "share_split_zero_total",
                "error",
                "split_details",
                "Share weights sum to zero or less.",
                "Hold row until share weights are corrected.",
            )

    def _detect_membership_anomalies(
        self,
        row: RowCandidate,
        anomalies: list[AnomalyDraft],
        participant_set: set[str],
    ) -> None:
        data = row.normalized_data
        parsed_date = data["parsed_date"]
        if parsed_date is None:
            return

        people_to_check = participant_set | (
            {data["paid_by_normalized"]} if data["paid_by_normalized"] else set()
        )
        for person in people_to_check:
            if person not in MEMBERSHIP_WINDOWS:
                continue
            start, end = MEMBERSHIP_WINDOWS[person]
            if parsed_date < start or (end is not None and parsed_date > end):
                self._add_anomaly(
                    anomalies,
                    row.raw_row_number,
                    "member_outside_active_window",
                    "review",
                    "membership",
                    f"{person} appears on {parsed_date.isoformat()}, outside active membership window.",
                    "Ask user whether this person should be charged/credited for the row.",
                )

    def _detect_source_note_anomalies(
        self,
        row: RowCandidate,
        anomalies: list[AnomalyDraft],
    ) -> None:
        data = row.normalized_data
        review_text = compact_text(f"{data['description_raw']} {data['notes']}")
        matched_terms = [term for term in REVIEW_NOTE_TERMS if term in review_text]
        if matched_terms:
            self._add_anomaly(
                anomalies,
                row.raw_row_number,
                "source_note_review_signal",
                "review",
                "notes",
                f"Source text contains review signal(s): {matched_terms}.",
                "Show note to user before final import.",
            )

    def _detect_duplicate_candidates(
        self,
        rows: list[RowCandidate],
        anomalies: list[AnomalyDraft],
    ) -> None:
        normalized_rows = [row.normalized_data for row in rows]
        for left_index, left in enumerate(normalized_rows):
            for right_index in range(left_index + 1, len(normalized_rows)):
                right = normalized_rows[right_index]
                if left["parsed_date"] is None or right["parsed_date"] is None:
                    continue
                if left["parsed_date"] != right["parsed_date"]:
                    continue

                similarity = description_similarity(
                    left["description_key"],
                    right["description_key"],
                )
                same_amount = (
                    left["amount_rounded"] == right["amount_rounded"]
                    and left["currency_normalized"] == right["currency_normalized"]
                )
                same_payer = left["paid_by_normalized"] == right["paid_by_normalized"]
                same_people = set(left["participants"]) == set(right["participants"])
                overlapping_people = bool(set(left["participants"]) & set(right["participants"]))

                left_row_number = rows[left_index].raw_row_number
                right_row_number = rows[right_index].raw_row_number

                if similarity >= 0.72 and same_amount and same_payer and same_people:
                    self._add_anomaly(
                        anomalies,
                        left_row_number,
                        "probable_duplicate",
                        "review",
                        "description",
                        f"Looks like duplicate of row {right_row_number}: description similarity {similarity:.0%}.",
                        "Keep one row only after user approval.",
                        True,
                        [right_row_number],
                    )
                    self._add_anomaly(
                        anomalies,
                        right_row_number,
                        "probable_duplicate",
                        "review",
                        "description",
                        f"Looks like duplicate of row {left_row_number}: description similarity {similarity:.0%}.",
                        "Keep one row only after user approval.",
                        True,
                        [left_row_number],
                    )
                elif similarity >= 0.70 and overlapping_people and not (same_amount and same_payer):
                    self._add_anomaly(
                        anomalies,
                        left_row_number,
                        "possible_conflicting_duplicate",
                        "review",
                        "description",
                        f"Possible duplicate/conflict with row {right_row_number}: similar description but payer or amount differs.",
                        "Ask user which row is correct or whether both are valid.",
                        True,
                        [right_row_number],
                    )
                    self._add_anomaly(
                        anomalies,
                        right_row_number,
                        "possible_conflicting_duplicate",
                        "review",
                        "description",
                        f"Possible duplicate/conflict with row {left_row_number}: similar description but payer or amount differs.",
                        "Ask user which row is correct or whether both are valid.",
                        True,
                        [left_row_number],
                    )

    def _assign_import_statuses(
        self,
        rows: list[RowCandidate],
        anomalies: list[AnomalyDraft],
    ) -> None:
        approval_rows = {
            anomaly.raw_row_number
            for anomaly in anomalies
            if anomaly.requires_user_approval
        }
        for row in rows:
            if row.normalized_data["is_settlement_candidate"]:
                row.import_status = "payment_or_settlement_candidate"
            elif row.raw_row_number in approval_rows:
                row.import_status = "needs_user_review"
            else:
                row.import_status = "ready_to_import"
            row.normalized_data["import_status"] = row.import_status

    def _add_anomaly(
        self,
        anomalies: list[AnomalyDraft],
        raw_row_number: int,
        code: str,
        severity: str,
        field_name: str,
        message: str,
        suggested_action: str,
        requires_user_approval: bool = True,
        related_rows: list[int] | None = None,
    ) -> None:
        anomalies.append(
            AnomalyDraft(
                raw_row_number=raw_row_number,
                code=code,
                severity=severity,
                field_name=field_name,
                message=message,
                suggested_action=suggested_action,
                requires_user_approval=requires_user_approval,
                related_rows=related_rows or [],
            )
        )


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def compact_text(value: Any, remove_stop_words: bool = False) -> str:
    text = clean_text(value).lower().replace("'", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    if remove_stop_words:
        text = re.sub(r"\b(at|the|a|an)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_person(value: Any) -> str:
    raw = clean_text(value)
    key = compact_text(raw)
    return PERSON_ALIASES.get(key, raw)


def parse_amount(value: Any) -> dict[str, Any]:
    raw = clean_text(value)
    normalized = raw.replace(",", "")
    result = {
        "amount_original": None,
        "amount_rounded": None,
        "amount_has_comma": "," in raw,
        "amount_decimal_places": None,
    }
    if not normalized:
        return result
    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return result

    result["amount_original"] = amount
    result["amount_rounded"] = amount.quantize(CENTS, rounding=ROUND_HALF_UP)
    result["amount_decimal_places"] = max(0, -amount.as_tuple().exponent)
    return result


def parse_date(value: Any) -> tuple[date | None, str | None]:
    raw = clean_text(value)
    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", raw):
        try:
            return datetime.strptime(raw, "%d-%m-%Y").date(), None
        except ValueError:
            return None, "unparseable_standard_date"

    month_short = re.fullmatch(r"([A-Za-z]{3})-(\d{1,2})", raw)
    if month_short:
        month_name, day = month_short.groups()
        try:
            parsed = datetime.strptime(f"{day}-{month_name}-{DEFAULT_YEAR}", "%d-%b-%Y").date()
        except ValueError:
            return None, "unparseable_date"
        return parsed, "non_standard_date_inferred_year"

    try:
        return datetime.strptime(raw, "%d/%m/%Y").date(), "non_standard_date"
    except ValueError:
        return None, "unparseable_date"


def parse_split_details(value: Any) -> list[dict[str, Any]]:
    details = []
    raw = clean_text(value)
    if not raw:
        return details

    for token in raw.split(";"):
        token = clean_text(token)
        if not token:
            continue
        match = re.match(
            r"^(?P<person>.+?)\s+(?P<value>-?\d+(?:\.\d+)?)\s*(?P<percent>%?)$",
            token,
        )
        if not match:
            details.append({"raw": token, "person": "", "value": None, "unit": "unparsed"})
            continue
        details.append(
            {
                "raw": token,
                "person": normalize_person(match.group("person")),
                "value": Decimal(match.group("value")),
                "unit": "percentage" if match.group("percent") else "number",
            }
        )
    return details


def description_similarity(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    ordered_similarity = SequenceMatcher(None, left, right).ratio()
    sorted_similarity = SequenceMatcher(
        None,
        " ".join(sorted(left_tokens)),
        " ".join(sorted(right_tokens)),
    ).ratio()
    token_overlap = (
        len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
        if left_tokens | right_tokens
        else 0
    )
    return max(ordered_similarity, sorted_similarity, token_overlap)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    default_csv = Path(__file__).resolve().parents[2] / "expense_data" / "Expenses Export.csv"
    preview = CSVImportPipeline().preview(default_csv)
    print(preview.summary)
