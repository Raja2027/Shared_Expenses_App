from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from expense_App.components.group_service import GroupService
from expense_App.components.import_pipeline import CSVImportPipeline
from expense_App.entity.models import ImportAnomaly, ImportBatch, ImportRow, User
from expense_App.exception import DatabaseException, NotFoundException
from expense_App.logger import get_logger
from expense_App.schemas.import_report import (
    ImportAnomalyResponse,
    ImportBatchResponse,
    ImportReportResponse,
    ImportRowResponse,
)


logger = get_logger(__name__)


class ImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pipeline = CSVImportPipeline()

    def create_import_preview(
        self,
        group_id: int,
        uploaded_by: User,
        csv_path: str | Path,
        filename: str,
    ) -> ImportReportResponse:
        GroupService(self.db).get_owned_group(group_id, uploaded_by)
        preview = self.pipeline.preview(csv_path)
        preview.filename = filename
        batch = self.pipeline.persist_preview(
            db=self.db,
            preview=preview,
            group_id=group_id,
            uploaded_by_user_id=uploaded_by.id,
        )
        return self.get_import_report(group_id, batch.id, uploaded_by)

    def list_import_batches(
        self,
        group_id: int,
        current_user: User,
    ) -> list[ImportBatch]:
        GroupService(self.db).get_owned_group(group_id, current_user)
        statement = (
            select(ImportBatch)
            .where(ImportBatch.group_id == group_id)
            .order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc())
        )
        return list(self.db.execute(statement).scalars().all())

    def get_import_report(
        self,
        group_id: int,
        import_batch_id: int,
        current_user: User,
    ) -> ImportReportResponse:
        GroupService(self.db).get_owned_group(group_id, current_user)
        statement = (
            select(ImportBatch)
            .where(ImportBatch.id == import_batch_id, ImportBatch.group_id == group_id)
            .options(selectinload(ImportBatch.rows).selectinload(ImportRow.anomalies))
        )
        batch = self.db.execute(statement).scalar_one_or_none()
        if not batch:
            raise NotFoundException(
                message="Import batch was not found.",
                error_code="import_batch_not_found",
                details={"group_id": group_id, "import_batch_id": import_batch_id},
            )
        return self._build_report(batch)

    def resolve_anomaly(
        self,
        group_id: int,
        import_batch_id: int,
        anomaly_id: int,
        resolution_status: str,
        current_user: User,
    ) -> ImportReportResponse:
        GroupService(self.db).get_owned_group(group_id, current_user)
        statement = (
            select(ImportAnomaly)
            .join(ImportRow, ImportRow.id == ImportAnomaly.import_row_id)
            .join(ImportBatch, ImportBatch.id == ImportRow.import_batch_id)
            .where(
                ImportBatch.id == import_batch_id,
                ImportBatch.group_id == group_id,
                ImportAnomaly.id == anomaly_id,
            )
            .options(selectinload(ImportAnomaly.row).selectinload(ImportRow.anomalies))
        )
        anomaly = self.db.execute(statement).scalar_one_or_none()
        if not anomaly:
            raise NotFoundException(
                message="Import anomaly was not found.",
                error_code="import_anomaly_not_found",
                details={
                    "group_id": group_id,
                    "import_batch_id": import_batch_id,
                    "anomaly_id": anomaly_id,
                },
            )

        anomaly.resolution_status = resolution_status
        anomaly.resolved_by_user_id = current_user.id
        anomaly.resolved_at = datetime.now(timezone.utc)
        self._refresh_row_status(anomaly.row)

        try:
            batch = self.db.get(ImportBatch, import_batch_id)
            self._refresh_batch_status(batch)
            self.db.commit()
        except SQLAlchemyError as error:
            self.db.rollback()
            logger.exception("Failed to resolve import anomaly id=%s", anomaly_id)
            raise DatabaseException(message="Failed to resolve import anomaly.") from error

        return self.get_import_report(group_id, import_batch_id, current_user)

    def _refresh_row_status(self, row: ImportRow) -> None:
        required_anomalies = [
            anomaly for anomaly in row.anomalies if anomaly.requires_user_approval
        ]
        if any(anomaly.resolution_status == "rejected" for anomaly in required_anomalies):
            row.status = "rejected"
            row.normalized_data = {**row.normalized_data, "import_status": row.status}
            return

        has_open_required = any(
            anomaly.resolution_status == "open" for anomaly in required_anomalies
        )
        if has_open_required:
            return

        if row.normalized_data.get("is_settlement_candidate"):
            row.status = "payment_or_settlement_approved"
        elif required_anomalies:
            row.status = "approved_for_import"
        else:
            row.status = "ready_to_import"
        row.normalized_data = {**row.normalized_data, "import_status": row.status}

    def _refresh_batch_status(self, batch: ImportBatch | None) -> None:
        if batch is None:
            return
        rows = list(batch.rows)
        if any(row.status in {"needs_user_review", "payment_or_settlement_candidate"} for row in rows):
            batch.status = "needs_review"
        elif any(row.status == "rejected" for row in rows):
            batch.status = "has_rejections"
        else:
            batch.status = "ready_to_import"

    def _build_report(self, batch: ImportBatch) -> ImportReportResponse:
        rows = sorted(batch.rows, key=lambda row: row.raw_row_number)
        anomaly_responses = []
        row_responses = []

        for row in rows:
            row_anomalies = sorted(row.anomalies, key=lambda anomaly: anomaly.id)
            row_anomaly_responses = [
                self._anomaly_response(anomaly, row.raw_row_number)
                for anomaly in row_anomalies
            ]
            anomaly_responses.extend(row_anomaly_responses)
            row_responses.append(
                ImportRowResponse(
                    id=row.id,
                    raw_row_number=row.raw_row_number,
                    status=row.status,
                    raw_data=row.raw_data,
                    normalized_data=row.normalized_data,
                    anomalies=row_anomaly_responses,
                    created_at=row.created_at,
                )
            )

        anomaly_responses.sort(key=lambda anomaly: (anomaly.raw_row_number, anomaly.id))
        live_summary = self._live_summary(batch, rows, anomaly_responses)
        return ImportReportResponse(
            batch=ImportBatchResponse.model_validate(batch),
            rows=row_responses,
            anomalies=anomaly_responses,
            summary=live_summary,
        )

    def _anomaly_response(
        self,
        anomaly: ImportAnomaly,
        raw_row_number: int,
    ) -> ImportAnomalyResponse:
        return ImportAnomalyResponse(
            id=anomaly.id,
            import_row_id=anomaly.import_row_id,
            raw_row_number=raw_row_number,
            code=anomaly.code,
            severity=anomaly.severity,
            field_name=anomaly.field_name,
            message=anomaly.message,
            suggested_action=anomaly.suggested_action,
            requires_user_approval=anomaly.requires_user_approval,
            resolution_status=anomaly.resolution_status,
            resolved_by_user_id=anomaly.resolved_by_user_id,
            resolved_at=anomaly.resolved_at,
            related_rows=anomaly.related_rows,
            created_at=anomaly.created_at,
        )

    def _live_summary(
        self,
        batch: ImportBatch,
        rows: list[ImportRow],
        anomalies: list[ImportAnomalyResponse],
    ) -> dict:
        row_status_counts: dict[str, int] = {}
        anomaly_resolution_counts: dict[str, int] = {}
        for row in rows:
            row_status_counts[row.status] = row_status_counts.get(row.status, 0) + 1
        for anomaly in anomalies:
            anomaly_resolution_counts[anomaly.resolution_status] = (
                anomaly_resolution_counts.get(anomaly.resolution_status, 0) + 1
            )
        open_required = sum(
            1
            for anomaly in anomalies
            if anomaly.requires_user_approval and anomaly.resolution_status == "open"
        )
        return {
            **batch.summary,
            "batch_status": batch.status,
            "row_status_counts": row_status_counts,
            "anomaly_resolution_counts": anomaly_resolution_counts,
            "open_required_anomalies": open_required,
        }
