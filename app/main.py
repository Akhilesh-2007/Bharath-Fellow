from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload

from .database import Base, engine, get_db
from .models import Certificate, CertificateStatus, GenerationJob
from .schemas import CreateJobRequest, JobResponse
from .services import job_to_response, process_job

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Bulk Certificate Generator", version="1.0.0", description="Create PDF certificates for many recipients in one request.")


def load_job_or_404(db: Session, job_id: str) -> GenerationJob:
    job = db.query(GenerationJob).options(selectinload(GenerationJob.certificates)).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return job


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(payload: CreateJobRequest, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = GenerationJob(title=payload.certificate_title.strip(), issuer=payload.issuer.strip(), total_recipients=len(payload.recipients))
    db.add(job)
    db.flush()
    for recipient in payload.recipients:
        db.add(Certificate(job_id=job.id, recipient_name=recipient.name.strip(), recipient_email=str(recipient.email).lower()))
    db.commit()
    job = load_job_or_404(db, job.id)
    background_tasks.add_task(process_job, job.id)
    return job_to_response(job, str(request.base_url).rstrip("/"))


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, request: Request, db: Session = Depends(get_db)):
    return job_to_response(load_job_or_404(db, job_id), str(request.base_url).rstrip("/"))


@app.get("/certificates/{certificate_id}/download")
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    certificate = db.get(Certificate, certificate_id)
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if certificate.status != CertificateStatus.generated or not certificate.file_path:
        raise HTTPException(status_code=409, detail="Certificate is not ready for download")
    path = Path(certificate.file_path)
    if not path.is_file():
        raise HTTPException(status_code=410, detail="Certificate file is unavailable")
    return FileResponse(path, media_type="application/pdf", filename="certificate-" + certificate.recipient_name.replace(" ", "-") + ".pdf")
