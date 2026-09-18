"""Tests des exports PDF, DOCX et ZIP."""

from __future__ import annotations

import io
import zipfile

from tests.conftest import job_result


def _generate(client, headers, project_id, document_type="SHORT_SYNOPSIS"):
    return client.post(
        f"/api/v1/projects/{project_id}/documents/{document_type}/generate",
        json={"language": "fr", "overwrite": True},
        headers=headers,
    )


def test_pdf_export_requires_at_least_one_document(client, auth_headers, project):
    empty = client.get(f"/api/v1/projects/{project['id']}/export/pdf", headers=auth_headers)
    assert empty.status_code == 400
    assert empty.json()["code"] == "nothing_to_export"

    _generate(client, auth_headers, project["id"])
    response = client.get(f"/api/v1/projects/{project['id']}/export/pdf", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_docx_export(client, auth_headers, project):
    document = job_result(_generate(client, auth_headers, project["id"]))["document"]
    response = client.get(
        f"/api/v1/projects/{project['id']}/export/docx/{document['id']}", headers=auth_headers
    )
    assert response.status_code == 200
    # Un .docx est une archive ZIP contenant word/document.xml.
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert "word/document.xml" in archive.namelist()


def test_zip_export_contains_documents_and_project_sheet(client, auth_headers, project):
    _generate(client, auth_headers, project["id"])
    response = client.get(f"/api/v1/projects/{project['id']}/export/zip", headers=auth_headers)
    assert response.status_code == 200

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
    assert any(name.endswith("PROJET.md") for name in names)
    assert any(name.endswith("Dossier_complet.pdf") for name in names)
    assert any(name.endswith(".docx") for name in names)


def test_export_is_scoped_to_the_owner(client, make_user):
    alice, _ = make_user("alice@example.com", plan="PRO_AUTHOR")
    bob, _ = make_user("bob@example.com", plan="PRO_AUTHOR")
    project_id = client.post(
        "/api/v1/projects",
        json={"title": "Projet d'Alice", "project_type": "DOCUMENTARY"},
        headers=alice,
    ).json()["id"]

    assert client.get(f"/api/v1/projects/{project_id}/export/zip", headers=bob).status_code == 404
