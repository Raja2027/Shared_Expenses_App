from datetime import datetime

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    timestamp: datetime


class ReadinessResponse(BaseModel):
    status: str
    service: str
    database: str
    timestamp: datetime
