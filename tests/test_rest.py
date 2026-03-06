"""Integration tests for REST endpoints that manage hardware models."""

import uuid

_JSON_HEADERS = {"Content-Type": "application/json"}


def test_post_logical_hardware_returns_uuid(app_client, raw_calibration):
    """Posting a valid hardware model returns 201 and a UUID payload."""
    response = app_client.post("/rest/logical-hardware", content=raw_calibration, headers=_JSON_HEADERS)
    assert response.status_code == 201
    returned_uuid = response.json()
    # Must be a valid UUID string
    uuid.UUID(returned_uuid)


def test_get_logical_hardware(app_client, hardware_model_uuid, hardware_model):
    """Fetching a created model by UUID returns the expected payload fields."""
    # Retrieve it by UUID
    get_response = app_client.get(f"/rest/logical-hardware/{hardware_model_uuid}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["version"] == hardware_model.version
    assert body["calibration_id"] == hardware_model.calibration_id
    assert set(body["qubits"].keys()) == set(hardware_model.qubits.keys())


def test_get_logical_hardware_not_found(app_client):
    """Requesting a missing UUID returns 404."""
    missing = uuid.uuid4()
    response = app_client.get(f"/rest/logical-hardware/{missing}")
    assert response.status_code == 404


def test_post_logical_hardware_duplicate_returns_409(app_client, raw_calibration):
    """Posting the same model twice returns 409 on the second request."""
    first = app_client.post("/rest/logical-hardware", content=raw_calibration, headers=_JSON_HEADERS)
    assert first.status_code == 201

    second = app_client.post("/rest/logical-hardware", content=raw_calibration, headers=_JSON_HEADERS)
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


def test_upload_logical_hardware_duplicate_returns_409(app_client, raw_calibration):
    """Uploading the same model file twice returns 409 on the second request."""
    files = {"file": ("calibration.json", raw_calibration, "application/json")}
    first = app_client.post("/rest/logical-hardware/upload", files=files)
    assert first.status_code == 201

    files = {"file": ("calibration.json", raw_calibration, "application/json")}
    second = app_client.post("/rest/logical-hardware/upload", files=files)
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


def test_get_all_logical_hardware_ids(app_client, hardware_model_uuid):
    """Listing model IDs returns a list that includes the created model UUID."""
    response = app_client.get("/rest/logical-hardware")
    assert response.status_code == 200
    ids = response.json()
    assert isinstance(ids, list)
    assert hardware_model_uuid in ids
