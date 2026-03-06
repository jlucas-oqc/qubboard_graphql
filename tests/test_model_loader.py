"""Validation tests for loading hardware model fixtures."""

from qupboard_graphql.schemas.hardware_model import HardwareModel


def test_load_model(hardware_model: HardwareModel):
    """Test that the fixture model loads and validates successfully."""
    assert hardware_model.version == "0.0.1"
