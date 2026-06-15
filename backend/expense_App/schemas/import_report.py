from datetime import datetime
from typing import Literal
from typing import Any

from pydantic import BaseModel, ConfigDict


class ImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    uploaded_by_user_id: int
    filename: str
    status: str
    summary: dict[str, Any]
    created_at: datetime


class ImportAnomalyResponse(BaseModel):
    id: int
    import_row_id: int
    raw_row_number: int
    code: str
    severity: str
    field_name: str
    message: str
    suggested_action: str
    requires_user_approval: bool
    resolution_status: str
    resolved_by_user_id: int | None
    resolved_at: datetime | None
    related_rows: list[int]
    created_at: datetime


class ImportRowResponse(BaseModel):
    id: int
    raw_row_number: int
    status: str
    raw_data: dict[str, Any]
    normalized_data: dict[str, Any]
    anomalies: list[ImportAnomalyResponse]
    created_at: datetime


class ImportReportResponse(BaseModel):
    batch: ImportBatchResponse
    rows: list[ImportRowResponse]
    anomalies: list[ImportAnomalyResponse]
    summary: dict[str, Any]


class ImportBatchListResponse(BaseModel):
    batches: list[ImportBatchResponse]


class ImportAnomalyResolutionRequest(BaseModel):
    resolution_status: Literal["approved", "rejected", "ignored"]
