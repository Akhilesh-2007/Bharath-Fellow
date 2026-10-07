from unittest.mock import patch

from app.generator import create_certificate as actual_create_certificate
from app.services import process_job

VALID_PAYLOAD = {"certificate_title": "Python Fundamentals", "issuer": "Acme Academy", "recipients": [{"name": "Ada Lovelace", "email": "ada@example.com"}, {"name": "Grace Hopper", "email": "grace@example.com"}]}


def test_create_job_status_and_retrieve_certificate(client):
    response = client.post("/jobs", json=VALID_PAYLOAD)
    assert response.status_code == 202
    job = response.json()
    assert job["status"] == "queued"
    assert job["total_recipients"] == 2
    retrieved = client.get(f"/jobs/{job['id']}")
    assert retrieved.status_code == 200
    job = retrieved.json()
    assert job["status"] == "completed"
    assert job["generated_count"] == 2
    download = client.get(job["certificates"][0]["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/pdf")
    assert download.content.startswith(b"%PDF")


def test_input_validation_rejects_invalid_recipient(client):
    response = client.post("/jobs", json={**VALID_PAYLOAD, "recipients": [{"name": "", "email": "not-an-email"}]})
    assert response.status_code == 422


def test_individual_failure_does_not_stop_remaining_certificates(client):
    calls = 0
    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("renderer unavailable")
        return actual_create_certificate(*args, **kwargs)

    with patch("app.main.process_job", lambda job_id: None):
        created = client.post("/jobs", json=VALID_PAYLOAD).json()
    with patch("app.services.create_certificate", side_effect=fail_once):
        process_job(created["id"])
    job = client.get(f"/jobs/{created['id']}").json()
    assert job["status"] == "completed_with_errors"
    assert job["failed_count"] == 1
    assert job["generated_count"] == 1
    failed = next(item for item in job["certificates"] if item["status"] == "failed")
    assert "renderer unavailable" in failed["error_message"]
