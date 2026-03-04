from fastapi.testclient import TestClient

_GRAPHQL_URL = "/graphql"


def test_get_calibration(test_client: TestClient, hardware_model_uuid: str):
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
                            physicalChannel {
                                uuid
                                nameIndex
                                blockSize
                                defaultAmplitude
                                switchBox
                                baseband {
                                    uuid
                                    frequency
                                    ifFrequency
                                }
                                iqVoltageBias {
                                    id
                                    bias
                                }
                            }
                            pulseChannels {
                                uuid
                                drive {
                                    uuid
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
                                        amp
                                        phase
                                        drag
                                        rise
                                        ampSetup
                                        stdDev
                                    }
                                }
                                secondState {
                                    uuid
                                    role
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
                                }
                                freqShift {
                                    uuid
                                    role
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
                                }
                            }
                            crossResonanceChannels {
                                edges {
                                    node {
                                        uuid
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
                                            amp
                                            phase
                                            drag
                                            rise
                                            ampSetup
                                            stdDev
                                        }
                                    }
                                }
                            }
                            crossResonanceCancellationChannels {
                                edges {
                                    node {
                                        uuid
                                        auxiliaryQubit
                                        frequency
                                        imbalance
                                        phaseIqOffset
                                        scaleReal
                                        scaleImag
                                    }
                                }
                            }
                            resonator {
                                uuid
                                physicalChannel {
                                    uuid
                                    nameIndex
                                    blockSize
                                    defaultAmplitude
                                    switchBox
                                    swapReadoutIq
                                    baseband {
                                        uuid
                                        frequency
                                        ifFrequency
                                    }
                                    iqVoltageBias {
                                        id
                                        bias
                                    }
                                }
                                pulseChannels {
                                    uuid
                                    measure {
                                        uuid
                                        frequency
                                        imbalance
                                        phaseIqOffset
                                        scaleReal
                                        scaleImag
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
                                    }
                                    acquire {
                                        uuid
                                        frequency
                                        imbalance
                                        phaseIqOffset
                                        scaleReal
                                        scaleImag
                                        acquire {
                                            id
                                            delay
                                            width
                                            sync
                                            useWeights
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
