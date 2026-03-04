from fastapi.testclient import TestClient

_GRAPHQL_URL = "/graphql"


def test_get_calibration(test_client: TestClient, hardware_model_uuid: str):
    """
    Test that we can retrieve a hardware model calibration by its UUID and that the returned data matches what we
    expect.
    """
    query = """
        query GetCalibration($id: UUID!) {
            getCalibration(id: $id) {
                id
                version
                calibrationId
                logicalConnectivity
                qubits {
                    edges {
                        node {
                            uuid
                            qubitKey
                            meanZMapArgs
                            discriminatorReal
                            discriminatorImag
                            directXPi
                            phaseCompXPi2
                            resUuid
                            physicalChannels {
                                edges {
                                    node {
                                        uuid
                                        channelKind
                                        nameIndex
                                        blockSize
                                        defaultAmplitude
                                        switchBox
                                        swapReadoutIq
                                        basebandUuid
                                        basebandFrequency
                                        basebandIfFrequency
                                        iqBias
                                    }
                                }
                            }
                            pulseChannels {
                                edges {
                                    node {
                                        uuid
                                        channelRole
                                        frequency
                                        imbalance
                                        phaseIqOffset
                                        scaleReal
                                        scaleImag
                                        ssActive
                                        ssDelay
                                        fsActive
                                        fsAmp
                                        fsPhase
                                        acqDelay
                                        acqWidth
                                        acqSync
                                        acqUseWeights
                                        resetDelay
                                        pulse {
                                            id
                                            waveformType
                                            width
                                            amp
                                            phase
                                            drag
                                            rise
                                            ampSetup
                                            stdDev
                                        }
                                        pulseXPi {
                                            id
                                            waveformType
                                            width
                                        }
                                    }
                                }
                            }
                            crossResonanceChannels {
                                edges {
                                    node {
                                        uuid
                                        role
                                        auxiliaryQubit
                                        frequency
                                        imbalance
                                        phaseIqOffset
                                        scaleReal
                                        scaleImag
                                        zxPi4Pulse {
                                            id
                                            waveformType
                                            width
                                        }
                                    }
                                }
                            }
                            crossResonanceCancellationChannels {
                                edges {
                                    node {
                                        uuid
                                        role
                                        auxiliaryQubit
                                        frequency
                                        imbalance
                                        phaseIqOffset
                                        scaleReal
                                        scaleImag
                                    }
                                }
                            }
                            zxPi4Comps {
                                edges {
                                    node {
                                        uuid
                                        auxiliaryQubit
                                        phaseCompTargetZxPi4
                                        pulseZxPi4TargetRotaryAmp
                                        precompActive
                                        postcompActive
                                        useSecondState
                                        useRotary
                                        pulsePrecomp {
                                            id
                                            waveformType
                                            width
                                        }
                                        pulsePostcomp {
                                            id
                                            waveformType
                                            width
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    payload = {
        "query": query,
        "variables": {"id": hardware_model_uuid},
    }

    response = test_client.post(_GRAPHQL_URL, json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "errors" not in data, f"GraphQL errors: {data.get('errors')}"
    calibration = data["data"]["getCalibration"]
    assert calibration is not None
    assert calibration["id"] == hardware_model_uuid

    qubit_nodes = calibration["qubits"]["edges"]
    assert len(qubit_nodes) > 0

    first_qubit = qubit_nodes[0]["node"]

    channels_by_role = {n["node"]["channelRole"]: n["node"] for n in first_qubit["pulseChannels"]["edges"]}

    drive = channels_by_role["drive"]
    assert drive["frequency"] is not None
    assert drive["pulse"] is not None

    second_state = channels_by_role["second_state"]
    assert second_state["pulse"] is not None

    reset_qubit = channels_by_role["reset_qubit"]
    assert reset_qubit["pulse"] is not None

    reset_resonator = channels_by_role["reset_resonator"]
    assert reset_resonator["pulse"] is not None

    assert first_qubit["phaseCompXPi2"] is not None
    assert first_qubit["resUuid"] is not None
    assert len(first_qubit["zxPi4Comps"]["edges"]) > 0

    # Both physical channels (qubit + resonator) should be present
    pc_nodes = first_qubit["physicalChannels"]["edges"]
    assert len(pc_nodes) == 2
    pc_kinds = {n["node"]["channelKind"] for n in pc_nodes}
    assert pc_kinds == {"qubit", "resonator"}


def test_get_all_calibrations(test_client: TestClient, hardware_model_uuid: str):
    """
    Test that get_all_calibrations returns a list of calibrations, each with an id and calibrationId,
    and that the seeded calibration is present.
    """
    query = """
        query {
            getAllCalibrations {
                id
                calibrationId
            }
        }
    """
    response = test_client.post(_GRAPHQL_URL, json={"query": query})

    assert response.status_code == 200
    data = response.json()
    assert "errors" not in data, f"GraphQL errors: {data.get('errors')}"
    calibrations = data["data"]["getAllCalibrations"]
    assert isinstance(calibrations, list)
    assert len(calibrations) > 0

    ids = [c["id"] for c in calibrations]
    assert hardware_model_uuid in ids

    for calibration in calibrations:
        assert "id" in calibration
        assert "calibrationId" in calibration
        assert calibration["id"] is not None
        assert calibration["calibrationId"] is not None


def test_get_all_hardware_model_ids(test_client: TestClient, hardware_model_uuid: str):
    """
    Test that we can retrieve a list of all hardware model UUIDs and that it contains the UUID of the model we created.
    """
    query = """
        query {
            getAllHardwareModelIds
        }
    """
    response = test_client.post(_GRAPHQL_URL, json={"query": query})

    assert response.status_code == 200
    data = response.json()
    assert "errors" not in data, f"GraphQL errors: {data.get('errors')}"
    ids = data["data"]["getAllHardwareModelIds"]
    assert isinstance(ids, list)
    assert hardware_model_uuid in ids
