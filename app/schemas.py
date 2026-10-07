from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import CertificateStatus, JobStatus


class RecipientInput(BaseModel):
    name: str = Field(min_length=1, max_length=200, description="Name printed on the certificate")
    email: EmailStr


class CreateJobRequest(BaseModel):
    certificate_title: str = Field(min_length=1, max_length=200)
    issuer: str = Field(min_length=1, max_length=200)
    recipients: list[RecipientInput] = Field(min_length=1, max_length=10_000)


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    recipient_name: str
    recipient_email: str
    status: CertificateStatus
    error_message: str | None
    download_url: str | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    certificate_title: str
    issuer: str
    status: JobStatus
    total_recipients: int
    generated_count: int
    failed_count: int
    pending_count: int
    created_at: datetime
    completed_at: datetime | None
    certificates: list[CertificateResponse]
