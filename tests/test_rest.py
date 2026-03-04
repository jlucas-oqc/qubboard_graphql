import uuid

_JSON_HEADERS = {"Content-Type": "application/json"}


def test_post_logical_hardware_returns_uuid(test_client, raw_calibration):
    """
    Test that posting a valid hardware model returns a 201 status code and a valid UUID string.
    :param test_client: fixture providing a TestClient instance for making requests to the API
    :param raw_calibration: fixture that loads the raw JSON string of a hardware model calibration from a file
    """
    response = test_client.post("/rest/logical-hardware", content=raw_calibration, headers=_JSON_HEADERS)
    assert response.status_code == 201
    returned_uuid = response.json()
    # Must be a valid UUID string
    uuid.UUID(returned_uuid)


def test_get_logical_hardware(test_client, hardware_model_uuid, hardware_model):
    """
    Test that we can retrieve a hardware model by its UUID and that the returned data matches what we expect.
    :param test_client: fixture providing a TestClient instance for making requests to the API
    :param hardware_model_uuid: fixture that creates a hardware model and returns its UUID
    :param hardware_model: fixture that provides the original HardwareModel instance that was created
    """
    # Retrieve it by UUID
    get_response = test_client.get(f"/rest/logical-hardware/{hardware_model_uuid}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["version"] == hardware_model.version
    assert body["calibration_id"] == hardware_model.calibration_id
    assert set(body["qubits"].keys()) == set(hardware_model.qubits.keys())


def test_get_logical_hardware_not_found(test_client):
    """
    Test that requesting a non-existent hardware model UUID returns a 404 status code.
    :param test_client: fixture providing a TestClient instance for making requests to the API
    """
    missing = uuid.uuid4()
    response = test_client.get(f"/rest/logical-hardware/{missing}")
    assert response.status_code == 404


def test_get_all_logical_hardware_ids(test_client, hardware_model_uuid):
    """
    Test that GET /rest/logical-hardware returns a list of UUIDs containing the created model's UUID.
    :param test_client: fixture providing a TestClient instance for making requests to the API
    :param hardware_model_uuid: fixture that creates a hardware model and returns its UUID
    """
    response = test_client.get("/rest/logical-hardware")
    assert response.status_code == 200
    ids = response.json()
    assert isinstance(ids, list)
    assert hardware_model_uuid in ids
