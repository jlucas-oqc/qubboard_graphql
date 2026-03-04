from qupboard_graphql.schemas.hardware_model import HardwareModel


def test_load_model(hardware_model: HardwareModel):
    """Tests that the model can be loaded and validates."""
    assert hardware_model.version == "0.0.1"
