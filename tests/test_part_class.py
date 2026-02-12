"""
test_part_class.py

Unit tests for universal PartClass subclasses in the Digital Product Passport system.

Covers:
    - Instantiation of each primary part class with sample attributes
    - Property correctness and type checks
    - Dictionary serialization of each part for Digital Product Passport integration

To run:
    pytest tests/test_part_class.py

Author: Anmol Kumar, NMIS
"""

import pytest
from nmis_dpp.part_class import (
    PowerConversion, EnergyStorage, Actuator, Sensor, ControlUnit,
    UserInterface, Thermal, Fluidics, Structural, Transmission,
    Protection, Connectivity, SoftwareModule, Consumable, Fastener
)
from nmis_dpp.utils import to_dict

def test_power_conversion():
    """
    Test instantiation and properties of PowerConversion class.
    """
    part = PowerConversion(
        part_id="PC1",
        name="Inverter",
        type="PowerConversion",
        input_voltage=230,
        output_voltage=24,
        power_rating=500,
        efficiency=0.95
    )
    assert part.input_voltage == 230
    assert part.output_voltage == 24
    assert part.power_rating == 500
    assert part.efficiency == 0.95

def test_sensor():
    """
    Test Sensor part class, including optional attributes.
    """
    part = Sensor(
        part_id="SENS1",
        name="Pressure Sensor",
        type="Sensor",
        sensor_type="pressure",
        range_min=0,
        range_max=10,
        accuracy=0.02,
        drift=0.001,
        response_time=5
    )
    assert part.sensor_type == "pressure"
    assert part.range_min == 0
    assert part.range_max == 10
    assert part.accuracy == 0.02
    assert part.drift == 0.001
    assert part.response_time == 5

def test_actuator():
    """
    Test the Actuator part class and its mechanical properties.
    """
    part = Actuator(
        part_id="ACT1",
        name="Servo Motor",
        type="Actuator",
        torque=2.5,
        speed=1800,
        duty_cycle=0.75,
        voltage=24,
        actuation_type="electric"
    )
    assert part.torque == 2.5
    assert part.speed == 1800
    assert part.voltage == 24
    assert part.duty_cycle == 0.75
    assert part.actuation_type == "electric"

def test_control_unit():
    """
    Ensure proper instantiation of ControlUnit parts.
    """
    part = ControlUnit(
        part_id="CU1",
        name="ECU Board",
        type="ControlUnit",
        cpu_type="ARM Cortex-M",
        memory=128,
        firmware_version="1.0.3",
        io_count=16
    )
    assert part.cpu_type == "ARM Cortex-M"
    assert part.memory == 128
    assert part.firmware_version == "1.0.3"
    assert part.io_count == 16

def test_user_interface():
    """
    Test UserInterface component instantiation.
    """
    part = UserInterface(
        part_id="UI1",
        name="Touch HMI",
        type="UserInterface",
        ui_type="touchscreen",
        display_size=7.0,
        input_methods=["touch", "button"],
        indicator_count=3
    )
    assert part.display_size == 7.0
    assert "touch" in part.input_methods
    assert part.indicator_count == 3

def test_thermal():
    """
    Validate properties for Thermal part class.
    """
    part = Thermal(
        part_id="THERM1",
        name="Blower Fan",
        type="Thermal",
        power=50,
        delta_t=30,
        airflow=120
    )
    assert part.power == 50
    assert part.delta_t == 30
    assert part.airflow == 120

def test_fluidics():
    """
    Confirm Fluidics device instantiation and field typing.
    """
    part = Fluidics(
        part_id="FLD1",
        name="Water Pump",
        type="Fluidics",
        flow_rate=15,
        pressure=2.5,
        fluid_type="water",
        volume=2.0
    )
    assert part.flow_rate == 15
    assert part.pressure == 2.5
    assert part.fluid_type == "water"
    assert part.volume == 2.0

def test_structural():
    """
    Ensure Structural elements accept valid attributes.
    """
    part = Structural(
        part_id="STR1",
        name="Main Frame",
        type="Structural",
        material="Aluminum",
        mass=4.0,
        dimensions={"length": 100.0, "width": 20.0},
        load_rating=2000
    )
    assert part.material == "Aluminum"
    assert part.mass == 4.0
    assert part.dimensions["length"] == 100.0
    assert part.load_rating == 2000

def test_transmission():
    """
    Transmission class instantiation and core attribute check.
    """
    part = Transmission(
        part_id="TRAN1",
        name="Gearbox",
        type="Transmission",
        torque_rating=300,
        speed_rating=6000,
        transmission_type="gear"
    )
    assert part.torque_rating == 300
    assert part.speed_rating == 6000
    assert part.transmission_type == "gear"

def test_protection():
    """
    Validate Protection part instantiation for fuses or breakers.
    """
    part = Protection(
        part_id="PROT1",
        name="Fuse",
        type="Protection",
        protection_type="fuse",
        rating=10,
        response_time=0.5
    )
    assert part.protection_type == "fuse"
    assert part.rating == 10
    assert part.response_time == 0.5

def test_connectivity():
    """
    Test for Connectivity devices like harnesses/connectors.
    """
    part = Connectivity(
        part_id="CONN1",
        name="Data Bus",
        type="Connectivity",
        interface_type="data",
        connector_standard="Ethernet",
        pin_count=8
    )
    assert part.interface_type == "data"
    assert part.connector_standard == "Ethernet"
    assert part.pin_count == 8

def test_software_module():
    """
    Test for the SoftwareModule class with standard software fields.
    """
    part = SoftwareModule(
        part_id="SW1",
        name="MCU Firmware",
        type="SoftwareModule",
        version="3.2.0",
        language="C",
        license="MIT",
        checksums={"sha256": "abcd1234"}
    )
    assert part.version == "3.2.0"
    assert part.language == "C"
    assert part.license == "MIT"
    assert part.checksums["sha256"] == "abcd1234"

def test_consumable():
    """
    Validate Consumable construction (e.g. filters, oils).
    """
    part = Consumable(
        part_id="CONS1",
        name="Grease Cartridge",
        type="Consumable",
        consumable_type="grease",
        capacity=500,
        replacement_interval="12M"
    )
    assert part.consumable_type == "grease"
    assert part.capacity == 500
    assert part.replacement_interval == "12M"

def test_fastener():
    """
    Test the Fastener class for correct field usage.
    """
    part = Fastener(
        part_id="FST1",
        name="Rivet",
        type="Fastener",
        fastener_type="rivet",
        material="Steel",
        diameter=5,
        length=12,
        strength=1500
    )
    assert part.fastener_type == "rivet"
    assert part.material == "Steel"
    assert part.diameter == 5
    assert part.length == 12
    assert part.strength == 1500

def test_serialization_to_dict():
    """
    Check that all part classes can be converted to dict for serialization.
    """
    part = Actuator(
        part_id="A_TEST",
        name="Test Actuator",
        type="Actuator",
        torque=1.1,
        speed=1000
    )
    part_dict = to_dict(part)
    assert isinstance(part_dict, dict)
    assert part_dict["type"] == "Actuator"
    assert "name" in part_dict and part_dict["name"] == "Test Actuator"

