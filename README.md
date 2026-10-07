# Bulk Certificate Generator

A FastAPI backend that generates one PDF certificate per recipient from a single bulk request. It stores job metadata in SQLite and makes each successful certificate downloadable.

## Design

- **FastAPI + SQLite:** lightweight relational persistence with no external service required.
- **Background tasks:** `POST /jobs` returns `202 Accepted` immediately; generation then happens after the response. For production-scale or multi-worker deployments, replace this with a durable queue such as Celery/RQ.
- **Failure isolation:** every recipient is generated in its own `try` block. A failed PDF is recorded without preventing other certificates in the job.
- **One predefined template:** ReportLab produces a fixed A4 landscape certificate. There is intentionally no template editor.

## Setup and run

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive API documentation.

## Create a generation job

```powershell
$body = @{
  certificate_title = "Python Fundamentals"
  issuer = "Acme Academy"
  recipients = @(
    @{ name = "Ada Lovelace"; email = "ada@example.com" }
    @{ name = "Grace Hopper"; email = "grace@example.com" }
  )
} | ConvertTo-Json -Depth 3
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/jobs -ContentType application/json -Body $body
```

The response has the job ID, overall status, progress counts, per-recipient status, errors, and `download_url` for generated files.

## Check progress and download

```powershell
Invoke-RestMethod http://127.0.0.1:8000/jobs/<job-id>
Invoke-WebRequest http://127.0.0.1:8000/certificates/<certificate-id>/download -OutFile certificate.pdf
```

Job states: `queued`, `processing`, `completed`, and `completed_with_errors`. Certificate states: `pending`, `generated`, and `failed`.

## Test

```powershell
python -m pytest -q
```

The tests cover job creation, schema validation, PDF generation/status/download, and failure of an individual certificate while the others continue.
