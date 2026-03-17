"""Tests for protocol registry and factory."""
import pytest

from custom_components.govee_h6006.protocols import GoveeProtocol, H6006Protocol, get_protocol


def test_get_protocol_for_h6006_device():
    """get_protocol should return H6006Protocol for ihoment_ prefix"""
    protocol = get_protocol("ihoment_H6006_1234")
    assert isinstance(protocol, H6006Protocol)
    assert isinstance(protocol, GoveeProtocol)


def test_get_protocol_returns_new_instance():
    """Each call to get_protocol should return a new instance"""
    protocol1 = get_protocol("ihoment_H6006_1234")
    protocol2 = get_protocol("ihoment_H6006_5678")
    assert protocol1 is not protocol2


def test_get_protocol_matches_prefix_case_sensitive():
    """Protocol matching should be case-sensitive for the prefix"""
    # Valid prefix (lowercase 'ihoment_')
    protocol = get_protocol("ihoment_H6006_ABCD")
    assert isinstance(protocol, H6006Protocol)


def test_get_protocol_raises_for_unknown_device():
    """get_protocol should raise ValueError for unregistered device names"""
    with pytest.raises(ValueError) as exc_info:
        get_protocol("unknown_device_name")

    assert "No protocol registered for device 'unknown_device_name'" in str(exc_info.value)
    assert "ihoment_" in str(exc_info.value)  # Error should list supported prefixes


def test_get_protocol_raises_for_empty_device_name():
    """get_protocol should raise ValueError for empty device name"""
    with pytest.raises(ValueError) as exc_info:
        get_protocol("")

    assert "No protocol registered" in str(exc_info.value)


def test_get_protocol_raises_for_partial_match():
    """get_protocol should not match partial prefixes"""
    # "ihomen" is not "ihoment_" - should fail
    with pytest.raises(ValueError):
        get_protocol("ihomen_device")

    # "IHOMENT_" is uppercase - should fail (case-sensitive)
    with pytest.raises(ValueError):
        get_protocol("IHOMENT_H6006_1234")


def test_h6006_protocol_has_required_attributes():
    """H6006Protocol should define COMMAND_HEAD and REQUEST_HEAD"""
    protocol = get_protocol("ihoment_H6006_TEST")
    assert hasattr(protocol, "COMMAND_HEAD")
    assert hasattr(protocol, "REQUEST_HEAD")
    assert protocol.COMMAND_HEAD == 0x33
    assert protocol.REQUEST_HEAD == 0xAA


def test_h6006_protocol_implements_all_methods():
    """H6006Protocol should implement all abstract methods from GoveeProtocol"""
    protocol = get_protocol("ihoment_H6006_TEST")

    # Verify all abstract methods are implemented and callable
    assert callable(protocol.build_power_packet)
    assert callable(protocol.build_brightness_packet)
    assert callable(protocol.build_color_rgb_packet)
    assert callable(protocol.build_color_temp_packet)
    assert callable(protocol.parse_notification)
