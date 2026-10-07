from pathlib import Path

from sqlalchemy import select

from .database import SessionLocal
from .generator import create_certificate
from .models import Certificate, CertificateStatus, GenerationJob, JobStatus, utcnow

CERTIFICATE_DIR = Path(__file__).resolve().parent.parent / "storage" / "certificates"


def process_job(job_id: str) -> None:
    """Generate independently so one bad record cannot stop a job."""
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            return
        job.status = JobStatus.processing
        db.commit()
        certificates = db.scalars(select(Certificate).where(Certificate.job_id == job_id)).all()
        for certificate in certificates:
            try:
                output_path = CERTIFICATE_DIR / job_id / f"{certificate.id}.pdf"
                create_certificate(output_path, certificate.recipient_name, job.title, job.issuer)
                certificate.file_path = str(output_path.resolve())
                certificate.status = CertificateStatus.generated
                certificate.error_message = None
            except Exception as exc:
                certificate.status = CertificateStatus.failed
                certificate.error_message = f"Generation failed: {exc}"
            finally:
                db.commit()
        has_failure = db.scalar(select(Certificate.id).where(Certificate.job_id == job_id, Certificate.status == CertificateStatus.failed).limit(1))
        job.status = JobStatus.completed_with_errors if has_failure else JobStatus.completed
        job.completed_at = utcnow()
        db.commit()
    finally:
        db.close()


def job_to_response(job: GenerationJob, base_url: str = "") -> dict:
    certificates = []
    generated = failed = pending = 0
    for item in job.certificates:
        if item.status == CertificateStatus.generated:
            generated += 1
        elif item.status == CertificateStatus.failed:
            failed += 1
        else:
            pending += 1
        certificates.append({"id": item.id, "recipient_name": item.recipient_name, "recipient_email": item.recipient_email, "status": item.status, "error_message": item.error_message, "download_url": f"{base_url}/certificates/{item.id}/download" if item.status == CertificateStatus.generated else None})
    return {"id": job.id, "certificate_title": job.title, "issuer": job.issuer, "status": job.status, "total_recipients": job.total_recipients, "generated_count": generated, "failed_count": failed, "pending_count": pending, "created_at": job.created_at, "completed_at": job.completed_at, "certificates": certificates}
