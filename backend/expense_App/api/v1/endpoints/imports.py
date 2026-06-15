from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from expense_App.components.balance_service import BalanceService
from expense_App.components.import_service import ImportService
from expense_App.dependencies import get_current_user, get_db_session
from expense_App.entity.models import ImportBatch, User
from expense_App.exception import ValidationException
from expense_App.schemas.import_report import (
    ImportAnomalyResolutionRequest,
    ImportBatchListResponse,
    ImportBatchResponse,
    ImportReportResponse,
)
from expense_App.schemas.balance import ImportBalanceResponse


router = APIRouter()


@router.post(
    "/{group_id}/imports",
    response_model=ImportReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CSV and create an import report",
)
async def upload_group_expenses_csv(
    group_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ImportReportResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise ValidationException(
            message="Only CSV files are supported.",
            error_code="unsupported_import_file",
            details={"filename": file.filename},
        )

    content = await file.read()
    if not content:
        raise ValidationException(
            message="Uploaded CSV file is empty.",
            error_code="empty_import_file",
            details={"filename": file.filename},
        )

    temp_path = None
    try:
        with NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        return ImportService(db).create_import_preview(
            group_id=group_id,
            uploaded_by=current_user,
            csv_path=temp_path,
            filename=file.filename,
        )
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@router.get(
    "/{group_id}/imports",
    response_model=ImportBatchListResponse,
    summary="List CSV import batches for a group",
)
def list_group_imports(
    group_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ImportBatchListResponse:
    batches: list[ImportBatch] = ImportService(db).list_import_batches(group_id, current_user)
    return ImportBatchListResponse(
        batches=[ImportBatchResponse.model_validate(batch) for batch in batches]
    )


@router.get(
    "/{group_id}/imports/{import_batch_id}/balances",
    response_model=ImportBalanceResponse,
    summary="Calculate traceable balances for an import batch",
)
def get_group_import_balances(
    group_id: int,
    import_batch_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ImportBalanceResponse:
    return BalanceService(db).calculate_import_balances(
        group_id=group_id,
        import_batch_id=import_batch_id,
        current_user=current_user,
    )


@router.get(
    "/{group_id}/imports/{import_batch_id}",
    response_model=ImportReportResponse,
    summary="Get a persisted import report",
)
def get_group_import_report(
    group_id: int,
    import_batch_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ImportReportResponse:
    return ImportService(db).get_import_report(group_id, import_batch_id, current_user)


@router.patch(
    "/{group_id}/imports/{import_batch_id}/anomalies/{anomaly_id}",
    response_model=ImportReportResponse,
    summary="Approve, reject, or ignore an import anomaly",
)
def resolve_import_anomaly(
    group_id: int,
    import_batch_id: int,
    anomaly_id: int,
    payload: ImportAnomalyResolutionRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ImportReportResponse:
    return ImportService(db).resolve_anomaly(
        group_id=group_id,
        import_batch_id=import_batch_id,
        anomaly_id=anomaly_id,
        resolution_status=payload.resolution_status,
        current_user=current_user,
    )
