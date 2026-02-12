"""
test_model.py

Unit tests for the Digital Product Passport model using pytest.

Tests:
    - Creation of example layer instances (IdentityLayer, StructureLayer, etc.)
    - Aggregation into a DigitalProductPassport object
    - Serialization of the full model to dict/JSON

To run:
    pytest tests/test_model.py

Author: Anmol Kumar, NMIS
"""

import pytest
from nmis_dpp.model import (
    IdentityLayer, StructureLayer, LifecycleLayer, RiskLayer,
    SustainabilityLayer, ProvenanceLayer, DigitalProductPassport
)
from nmis_dpp.part_class import (
    Actuator, Sensor, PowerConversion
)
from nmis_dpp.utils import to_dict, to_json

def sample_layers():
    """
    Helper function to return example instances for all passport layers.

    Returns:
        Tuple of layer instances in canonical order.
    """
    identity = IdentityLayer(
        global_ids={"gtin": "1234567890", "serial": "XYZ123"},
        make_model={"brand": "ACME", "model": "DPPX", "hw_rev": "1.0", "fw_rev": "1.2"},
        ownership={"manufacturer": "ACME", "owner": "Bob", "operator": "Carol", "location": "Warehouse"},
        conformity=["CE", "RoHS"]
    )
    # Example parts of various class types
    motor = Actuator(part_id="A1", name="Drive Motor", type="Actuator", torque=1.5, speed=2000, voltage=48)
    sensor = Sensor(part_id="S1", name="Thermal Sensor", type="Sensor", sensor_type="temperature", range_min=-20, range_max=120)
    psu = PowerConversion(part_id="P1", name="PSU", type="PowerConversion", input_voltage=230, output_voltage=48)
    structure = StructureLayer(
        hierarchy={"product": "DPPX Unit", "components": [motor, sensor, psu]},
        parts=[motor, sensor, psu],
        interfaces=[{"type": "electrical", "details": {"voltage": 48}}],
        materials=[{"cas": "7439-97-6", "%mass": 60.0, "recyclable": "yes"}],
        bom_refs=["REF-X"]
    )
    lifecycle = LifecycleLayer(
        manufacture={"lot": "L001", "factory": "ACME-Fac", "date": "2025-05-01", "process": "CNC"},
        use={"counters": {"hours": 250}, "telemetry": {"max_temp": 74.5}},
        serviceability={"schedule": {"interval": "6M"}, "repairability_score": 8},
        events=[{"event_type": "install", "timestamp": "2025-05-10"}],
        end_of_life={"disassembly": ["Remove housing"], "hazards": [], "recovery_routes": ["Recycle"]}
    )
    risk = RiskLayer(
        criticality={"levels": "Mission", "llp": False, "mtbf": 500000},
        fmea=[{"failure_mode": "open", "effect": "system halt", "mitigation": "replace"}],
        security={"sbom": None, "vulnerabilities": [], "signing_keys": ["key-abc"]}
    )
    sustainability = SustainabilityLayer(
        mass=4.3,
        energy={"standby": 0.5, "active": 11.2, "water_use": 0.0},
        recycled_content={"pcr_percent": 40.0, "bio": 0.0},
        remanufacture={"eligible": True}
    )
    provenance = ProvenanceLayer(
        signatures=[{"type": "service", "certificate": "EASA123"}],
        trace_links=["EPCIS:modA"]
    )
    return identity, structure, lifecycle, risk, sustainability, provenance

def test_layer_creation():
    """
    Test that all Digital Product Passport layers can be created with valid data.
    """
    identity, structure, lifecycle, risk, sustainability, provenance = sample_layers()
    assert identity.global_ids["gtin"] == "1234567890"
    assert structure.parts[0].type == "Actuator"
    assert lifecycle.manufacture["factory"] == "ACME-Fac"
    assert isinstance(risk.fmea, list)
    assert sustainability.mass > 0
    assert provenance.signatures[0]["type"] == "service"

def test_dpp_aggregation():
    """
    Test that a DigitalProductPassport can be built from layers and exposes correct attributes.
    """
    layers = sample_layers()
    dpp = DigitalProductPassport(*layers)
    assert isinstance(dpp.identity, IdentityLayer)
    assert dpp.structure.hierarchy["product"] == "DPPX Unit"
    assert dpp.lifecycle.serviceability["repairability_score"] == 8
    assert "Mission" in dpp.risk.criticality["levels"]

def test_to_dict_and_json():
    """
    Test that DigitalProductPassport can be successfully serialized to dict and JSON.
    """
    dpp = DigitalProductPassport(*sample_layers())
    dpp_dict = to_dict(dpp)
    dpp_json = to_json(dpp)
    assert isinstance(dpp_dict, dict)
    assert isinstance(dpp_json, str)
    assert "DPPX Unit" in dpp_json
    assert dpp_dict["structure"]["parts"][1]["name"] == "Thermal Sensor"

