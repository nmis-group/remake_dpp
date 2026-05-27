"""
test_battery_dpp_mapper.py

Tests for BatteryDPPMapper — all layer mapping methods, validate_mapping
(valid case + each mandatory field failure), and registry integration.
"""

import pytest
from nmis_dpp.mappers.battery_dpp_mapper import BatteryDPPMapper
from nmis_dpp.model import (
    DigitalProductPassport, IdentityLayer, StructureLayer, LifecycleLayer,
    RiskLayer, SustainabilityLayer, ProvenanceLayer,
)
from nmis_dpp.part_class import Actuator, EnergyStorage, PartClass
from nmis_dpp.schema_registry import get_global_registry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def battery_part():
    return EnergyStorage(
        part_id="BAT-001",
        name="Main Battery Pack",
        type="EnergyStorage",
        chemistry="Li-ion",
        capacity=100.0,
        voltage=48.0,
        recharge_cycles=1000,
    )


@pytest.fixture
def non_battery_part():
    return Actuator(
        part_id="ACT-001",
        name="Cooling Fan",
        type="Actuator",
        voltage=24.0,
    )


@pytest.fixture
def full_dpp(battery_part, non_battery_part):
    """A complete, valid Battery DPP with all mandatory fields populated."""
    return DigitalProductPassport(
        identity=IdentityLayer(
            global_ids={"serial": "SN-2024-001", "gtin": "00-BAT-001"},
            make_model={"brand": "NMIS Energy", "model": "PowerPack Pro"},
            ownership={"manufacturer": "NMIS Ltd"},
            conformity=["CE", "UN 38.3"],
        ),
        structure=StructureLayer(
            hierarchy={"product": "PowerPack Pro"},
            parts=[battery_part, non_battery_part],
            interfaces=[],
            materials=[],
            bom_refs=[],
        ),
        lifecycle=LifecycleLayer(
            manufacture={"date": "2024-03-01", "factory": "Plant-Glasgow"},
            use={"state_of_health": 0.98, "cycles": 12},
            serviceability={"replacement_interval": "5 years"},
            events=[],
            end_of_life={},
        ),
        risk=RiskLayer(
            criticality={"safety_instructions": ["Do not short circuit"]},
            fmea=[{"substance": "Lithium", "hazard_class": "Flammable", "concentration": 0.05}],
            security={},
        ),
        sustainability=SustainabilityLayer(
            mass=8.5,
            energy={"standby_w": 0.5},
            recycled_content={
                "co2e": 75.0,
                "cobalt_pct": 12.0,
                "lithium_pct": 5.0,
                "pcr_percent": 20.0,
            },
            remanufacture={"eligible": True},
        ),
        provenance=ProvenanceLayer(
            signatures=[{"signed_by": "NMIS QA", "certificate": "EU-DoC-2024", "date": "2024-03-15"}],
            trace_links=["epcis://batch/SN-2024-001"],
        ),
    )


@pytest.fixture
def mapper():
    return BatteryDPPMapper(config={})


# ---------------------------------------------------------------------------
# Schema metadata
# ---------------------------------------------------------------------------

def test_schema_name(mapper):
    assert mapper.get_schema_name() == "BatteryDPP"


def test_schema_version(mapper):
    assert mapper.get_schema_version() == "EU-2023/1542"


def test_get_context(mapper):
    ctx = mapper.get_context()
    assert "@vocab" in ctx
    assert "batteryModel" in ctx
    assert "carbonFootprint" in ctx
    assert "recycledContent" in ctx
    assert "manufacturerIdentification" in ctx


# ---------------------------------------------------------------------------
# map_identity_layer
# ---------------------------------------------------------------------------

def test_map_identity_layer(mapper, full_dpp):
    result = mapper.map_identity_layer(full_dpp.identity)
    assert result["batteryModel"] == "PowerPack Pro"
    assert result["manufacturerIdentification"] == "NMIS Ltd"
    assert result["productIdentifier"] == "SN-2024-001"
    assert "CE" in result["conformityCertification"]
    assert "UN 38.3" in result["conformityCertification"]


def test_map_identity_layer_gtin_fallback(mapper):
    layer = IdentityLayer(
        global_ids={"gtin": "00-BAT-999"},
        make_model={"model": "X"},
        ownership={"manufacturer": "Co"},
        conformity=[],
    )
    result = mapper.map_identity_layer(layer)
    assert result["productIdentifier"] == "00-BAT-999"


# ---------------------------------------------------------------------------
# map_structure_layer
# ---------------------------------------------------------------------------

def test_map_structure_layer_energy_storage_elevated(mapper, full_dpp):
    result = mapper.map_structure_layer(full_dpp.structure)
    components = result["componentsList"]
    assert len(components) == 2

    bat = next(c for c in components if c["id"] == "BAT-001")
    assert bat["chemistry"] == "Li-ion"
    assert bat["capacity"] == 100.0
    assert bat["voltage"] == 48.0
    assert bat["rechargeCycles"] == 1000


def test_map_structure_layer_non_battery_part(mapper, full_dpp):
    result = mapper.map_structure_layer(full_dpp.structure)
    components = result["componentsList"]
    act = next(c for c in components if c["id"] == "ACT-001")
    assert act["type"] == "Actuator"
    assert "attributes" in act
    # EnergyStorage-specific fields must NOT appear on non-battery part
    assert "chemistry" not in act
    assert "capacity" not in act


# ---------------------------------------------------------------------------
# map_lifecycle_layer
# ---------------------------------------------------------------------------

def test_map_lifecycle_layer(mapper, full_dpp):
    result = mapper.map_lifecycle_layer(full_dpp.lifecycle)
    assert result["manufacturingDate"] == "2024-03-01"
    assert result["placeOfManufacturing"] == "Plant-Glasgow"
    assert result["stateOfHealth"] == 0.98
    assert result["cycleCount"] == 12
    assert result["expectedLifetime"] == "5 years"


def test_map_lifecycle_layer_empty():
    mapper = BatteryDPPMapper(config={})
    layer = LifecycleLayer(manufacture={}, use={}, serviceability={}, events=[], end_of_life={})
    result = mapper.map_lifecycle_layer(layer)
    assert result["manufacturingDate"] is None
    assert result["stateOfHealth"] is None
    assert result["cycleCount"] is None


# ---------------------------------------------------------------------------
# map_risk_layer
# ---------------------------------------------------------------------------

def test_map_risk_layer_hazardous_substances(mapper, full_dpp):
    result = mapper.map_risk_layer(full_dpp.risk)
    hazardous = result["hazardousSubstances"]
    assert len(hazardous) == 1
    assert hazardous[0]["substanceName"] == "Lithium"
    assert hazardous[0]["hazardClass"] == "Flammable"
    assert hazardous[0]["concentration"] == 0.05


def test_map_risk_layer_safety_instructions(mapper, full_dpp):
    result = mapper.map_risk_layer(full_dpp.risk)
    assert "Do not short circuit" in result["safetyInstructions"]


def test_map_risk_layer_empty():
    mapper = BatteryDPPMapper(config={})
    result = mapper.map_risk_layer(RiskLayer(criticality={}, fmea=[], security={}))
    assert result["hazardousSubstances"] == []
    assert result["safetyInstructions"] == []


def test_map_risk_layer_fmea_without_substance_excluded(mapper):
    """FMEA entries without a 'substance' or 'hazard_class' key must not appear."""
    layer = RiskLayer(
        criticality={},
        fmea=[{"mode": "Overheating", "effect": "Shutdown", "mitigation": "Fuse"}],
        security={},
    )
    result = mapper.map_risk_layer(layer)
    assert result["hazardousSubstances"] == []


# ---------------------------------------------------------------------------
# map_sustainability_layer
# ---------------------------------------------------------------------------

def test_map_sustainability_layer(mapper, full_dpp):
    result = mapper.map_sustainability_layer(full_dpp.sustainability)
    assert result["carbonFootprint"] == 75.0
    assert result["mass"] == 8.5
    assert result["recycledContent"]["cobalt"] == 12.0
    assert result["recycledContent"]["lithium"] == 5.0
    assert result["recycledContent"]["postConsumerRecycled"] == 20.0


def test_map_sustainability_layer_missing_co2e():
    mapper = BatteryDPPMapper(config={})
    layer = SustainabilityLayer(mass=1.0, energy={}, recycled_content={}, remanufacture={})
    result = mapper.map_sustainability_layer(layer)
    assert result["carbonFootprint"] is None


def test_map_sustainability_layer_co2e_from_config():
    mapper = BatteryDPPMapper(config={"carbon_footprint": 50.0})
    layer = SustainabilityLayer(mass=1.0, energy={}, recycled_content={}, remanufacture={})
    result = mapper.map_sustainability_layer(layer)
    assert result["carbonFootprint"] == 50.0


# ---------------------------------------------------------------------------
# map_provenance_layer
# ---------------------------------------------------------------------------

def test_map_provenance_layer(mapper, full_dpp):
    result = mapper.map_provenance_layer(full_dpp.provenance)
    decls = result["conformityDeclaration"]
    assert len(decls) == 1
    assert decls[0]["issuedBy"] == "NMIS QA"
    assert decls[0]["certificateType"] == "EU-DoC-2024"
    assert "epcis://batch/SN-2024-001" in result["supplyChainInfo"]


def test_map_provenance_layer_empty():
    mapper = BatteryDPPMapper(config={})
    result = mapper.map_provenance_layer(ProvenanceLayer(signatures=[], trace_links=[]))
    assert result["conformityDeclaration"] == []
    assert result["supplyChainInfo"] == []


# ---------------------------------------------------------------------------
# validate_mapping — valid case
# ---------------------------------------------------------------------------

def test_validate_mapping_valid(mapper, full_dpp):
    mapped = mapper.map_dpp(full_dpp)
    assert mapped["schema"] == "BatteryDPP"


# ---------------------------------------------------------------------------
# validate_mapping — each required field missing is a hard error
# ---------------------------------------------------------------------------

def _base_valid_mapped():
    """Return a minimal structurally valid mapped Battery DPP dict."""
    return {
        "schema": "BatteryDPP",
        "identity": {
            "batteryModel": "PowerPack Pro",
            "manufacturerIdentification": "NMIS Ltd",
        },
        "structure": {
            "componentsList": [{"id": "BAT-001", "type": "EnergyStorage", "chemistry": "Li-ion"}],
        },
        "sustainability": {
            "carbonFootprint": 75.0,
            "recycledContent": {"cobalt": 12.0},
        },
        "lifecycle": {},
        "risk": {},
        "provenance": {},
    }


def test_validate_mapping_schema_mismatch():
    mapper = BatteryDPPMapper(config={})
    data = _base_valid_mapped()
    data["schema"] = "WRONG"
    valid, errors = mapper.validate_mapping(data)
    assert not valid
    assert any("mismatch" in e.lower() for e in errors)


def test_validate_mapping_missing_manufacturer():
    mapper = BatteryDPPMapper(config={})
    data = _base_valid_mapped()
    data["identity"]["manufacturerIdentification"] = None
    valid, errors = mapper.validate_mapping(data)
    assert not valid
    assert any("manufacturerIdentification" in e for e in errors)


def test_validate_mapping_missing_battery_model():
    mapper = BatteryDPPMapper(config={})
    data = _base_valid_mapped()
    data["identity"]["batteryModel"] = None
    valid, errors = mapper.validate_mapping(data)
    assert not valid
    assert any("batteryModel" in e for e in errors)


def test_validate_mapping_missing_carbon_footprint():
    mapper = BatteryDPPMapper(config={})
    data = _base_valid_mapped()
    data["sustainability"]["carbonFootprint"] = None
    valid, errors = mapper.validate_mapping(data)
    assert not valid
    assert any("carbonFootprint" in e for e in errors)


def test_validate_mapping_non_numeric_carbon_footprint():
    mapper = BatteryDPPMapper(config={})
    data = _base_valid_mapped()
    data["sustainability"]["carbonFootprint"] = "lots"
    valid, errors = mapper.validate_mapping(data)
    assert not valid
    assert any("numeric" in e for e in errors)


def test_validate_mapping_missing_recycled_content():
    mapper = BatteryDPPMapper(config={})
    data = _base_valid_mapped()
    data["sustainability"]["recycledContent"] = {}
    valid, errors = mapper.validate_mapping(data)
    assert not valid
    assert any("recycledContent" in e for e in errors)


def test_validate_mapping_no_energy_storage_part():
    mapper = BatteryDPPMapper(config={})
    data = _base_valid_mapped()
    data["structure"]["componentsList"] = [{"id": "ACT-001", "type": "Actuator"}]
    valid, errors = mapper.validate_mapping(data)
    assert not valid
    assert any("EnergyStorage" in e for e in errors)


def test_validate_mapping_multiple_errors():
    """Missing manufacturer AND carbonFootprint should both appear in errors."""
    mapper = BatteryDPPMapper(config={})
    data = _base_valid_mapped()
    data["identity"]["manufacturerIdentification"] = None
    data["sustainability"]["carbonFootprint"] = None
    valid, errors = mapper.validate_mapping(data)
    assert not valid
    assert len(errors) >= 2


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------

def test_battery_dpp_registered_in_registry():
    registry = get_global_registry()
    assert "BatteryDPP" in registry.list_schemas()


def test_battery_dpp_aliases():
    registry = get_global_registry()
    mapper_by_alias = registry.get_mapper("battery")
    assert mapper_by_alias.get_schema_name() == "BatteryDPP"


def test_registry_map_dpp_battery(full_dpp):
    registry = get_global_registry()
    mapped = registry.map_dpp("BatteryDPP", full_dpp)
    assert mapped["schema"] == "BatteryDPP"
    assert mapped["identity"]["batteryModel"] == "PowerPack Pro"
