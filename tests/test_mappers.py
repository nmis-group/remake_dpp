"""
test_mappers.py

Tests for ECLASS and ISA-95 mappers — existing happy-path tests plus
new coverage for previously-stub methods (risk, sustainability, provenance)
and strengthened validate_mapping logic.
"""

import pytest
from nmis_dpp.mappers.eclass_mapper import ECLASSMapper
from nmis_dpp.mappers.isa95_mapper import ISA95Mapper
from nmis_dpp.model import (
    DigitalProductPassport, IdentityLayer, StructureLayer, LifecycleLayer,
    RiskLayer, SustainabilityLayer, ProvenanceLayer,
)
from nmis_dpp.part_class import PartClass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_dpp():
    """Minimal DPP with one Actuator part — used by existing tests."""
    part = PartClass(part_id="P1", name="Part1", type="Actuator", properties={"torque": 10})
    return DigitalProductPassport(
        identity=IdentityLayer(
            global_ids={"gtin": "123"},
            make_model={"brand": "BrandX", "model": "Mod1"},
            ownership={"manufacturer": "MfgCo"},
            conformity=[],
        ),
        structure=StructureLayer(
            hierarchy={},
            parts=[part],
            interfaces=[],
            materials=[],
            bom_refs=[],
        ),
        lifecycle=LifecycleLayer(
            manufacture={"date": "2023-01-01", "lot": "L1"},
            use={},
            serviceability={},
            events=[],
            end_of_life={},
        ),
        risk=RiskLayer(criticality={}, fmea=[], security={}),
        sustainability=SustainabilityLayer(
            mass=1.0,
            energy={},
            recycled_content={},
            remanufacture={},
        ),
        provenance=ProvenanceLayer(signatures=[], trace_links=[]),
    )


@pytest.fixture
def rich_risk():
    return RiskLayer(
        criticality={"safety_level": "SIL-2", "mtbf": 50000, "llp": True},
        fmea=[{"mode": "Overheating", "effect": "Shutdown", "mitigation": "Thermal fuse"}],
        security={"sbom": "sbom-v1.json", "vulnerabilities": ["CVE-2024-001"], "signing_key": "key-abc"},
    )


@pytest.fixture
def rich_provenance():
    return ProvenanceLayer(
        signatures=[{"signed_by": "NMIS QA", "certificate": "ISO-9001", "date": "2024-01-15"}],
        trace_links=["epcis://event/001", "epcis://event/002"],
    )


@pytest.fixture
def rich_sustainability():
    return SustainabilityLayer(
        mass=12.5,
        energy={"standby_w": 2.0, "active_w": 150.0},
        recycled_content={"pcr_percent": 30.0, "restricted_substances": ["Pb"]},
        remanufacture={"eligible": True, "grade": "A"},
    )


# ---------------------------------------------------------------------------
# Existing happy-path tests (unchanged)
# ---------------------------------------------------------------------------

def test_eclass_mapper(sample_dpp):
    mapper = ECLASSMapper(config={})
    assert mapper.get_schema_name() == "ECLASS"

    mapped = mapper.map_dpp(sample_dpp)

    assert mapped["schema"] == "ECLASS"
    assert mapped["identity"]["manufacturerId"] == "MfgCo"

    parts = mapped["structure"]["components"]
    assert len(parts) == 1
    assert parts[0]["name"] == "Part1"
    assert parts[0].get("attributes", {}).get("torque") == 10


def test_isa95_mapper(sample_dpp):
    mapper = ISA95Mapper(config={})
    assert mapper.get_schema_name() == "ISA-95"

    mapped = mapper.map_dpp(sample_dpp)

    assert mapped["schema"] == "ISA-95"
    assert mapped["identity"]["ID"] == "123"

    nested = mapped["structure"]["NestedEquipment"]
    assert len(nested) == 1
    assert nested[0]["ID"] == "P1"


# ---------------------------------------------------------------------------
# ECLASS — map_risk_layer
# ---------------------------------------------------------------------------

def test_eclass_map_risk_layer_empty():
    mapper = ECLASSMapper(config={})
    result = mapper.map_risk_layer(RiskLayer(criticality={}, fmea=[], security={}))
    assert "criticality" in result
    assert "fmea" in result
    assert result["fmea"] == []
    assert "security" in result


def test_eclass_map_risk_layer_with_data(rich_risk):
    mapper = ECLASSMapper(config={})
    result = mapper.map_risk_layer(rich_risk)

    assert result["criticality"]["safetyLevel"] == "SIL-2"
    assert result["criticality"]["mtbf"] == 50000
    assert result["criticality"]["isLifeLimitedPart"] is True

    assert len(result["fmea"]) == 1
    assert result["fmea"][0]["failureMode"] == "Overheating"
    assert result["fmea"][0]["effect"] == "Shutdown"
    assert result["fmea"][0]["mitigation"] == "Thermal fuse"

    assert result["security"]["sbom"] == "sbom-v1.json"
    assert "CVE-2024-001" in result["security"]["vulnerabilities"]


# ---------------------------------------------------------------------------
# ECLASS — map_provenance_layer
# ---------------------------------------------------------------------------

def test_eclass_map_provenance_layer_empty():
    mapper = ECLASSMapper(config={})
    result = mapper.map_provenance_layer(ProvenanceLayer(signatures=[], trace_links=[]))
    assert result["signatures"] == []
    assert result["traceLinks"] == []


def test_eclass_map_provenance_layer_with_data(rich_provenance):
    mapper = ECLASSMapper(config={})
    result = mapper.map_provenance_layer(rich_provenance)

    assert len(result["signatures"]) == 1
    assert result["signatures"][0]["signedBy"] == "NMIS QA"
    assert result["signatures"][0]["certificate"] == "ISO-9001"

    assert "epcis://event/001" in result["traceLinks"]
    assert "epcis://event/002" in result["traceLinks"]


# ---------------------------------------------------------------------------
# ECLASS — validate_mapping
# ---------------------------------------------------------------------------

def test_eclass_validate_mapping_valid(sample_dpp):
    mapper = ECLASSMapper(config={})
    mapped = mapper.map_dpp(sample_dpp)
    # map_dpp calls validate internally; reaching here means it passed
    assert mapped["schema"] == "ECLASS"


def test_eclass_validate_mapping_schema_mismatch():
    mapper = ECLASSMapper(config={})
    valid, errors = mapper.validate_mapping({"schema": "WRONG"})
    assert not valid
    assert any("mismatch" in e.lower() for e in errors)


def test_eclass_validate_mapping_missing_identity():
    mapper = ECLASSMapper(config={})
    valid, errors = mapper.validate_mapping({
        "schema": "ECLASS",
        "identity": {},
        "structure": {"components": [{"id": "P1"}]},
        "lifecycle": {},
    })
    assert not valid
    assert any("manufacturerId" in e or "serialNumber" in e for e in errors)


def test_eclass_validate_mapping_empty_components():
    mapper = ECLASSMapper(config={})
    valid, errors = mapper.validate_mapping({
        "schema": "ECLASS",
        "identity": {"manufacturerId": "NMIS"},
        "structure": {"components": []},
        "lifecycle": {},
    })
    assert not valid
    assert any("components" in e for e in errors)


# ---------------------------------------------------------------------------
# ISA-95 — map_risk_layer
# ---------------------------------------------------------------------------

def test_isa95_map_risk_layer_empty():
    mapper = ISA95Mapper(config={})
    result = mapper.map_risk_layer(RiskLayer(criticality={}, fmea=[], security={}))
    assert "MaintenanceInfo" in result
    assert result["FMEA"] == []
    assert "Security" in result


def test_isa95_map_risk_layer_with_data(rich_risk):
    mapper = ISA95Mapper(config={})
    result = mapper.map_risk_layer(rich_risk)

    assert result["MaintenanceInfo"]["SafetyLevel"] == "SIL-2"
    assert result["MaintenanceInfo"]["MTBF"] == 50000
    assert result["MaintenanceInfo"]["IsLifeLimitedPart"] is True

    assert len(result["FMEA"]) == 1
    assert result["FMEA"][0]["FailureMode"] == "Overheating"

    assert result["Security"]["SBOM"] == "sbom-v1.json"
    assert result["Security"]["SigningKey"] == "key-abc"


# ---------------------------------------------------------------------------
# ISA-95 — map_sustainability_layer
# ---------------------------------------------------------------------------

def test_isa95_map_sustainability_layer_mass_only():
    mapper = ISA95Mapper(config={})
    layer = SustainabilityLayer(mass=5.0, energy={}, recycled_content={}, remanufacture={})
    result = mapper.map_sustainability_layer(layer)
    props = result["PhysicalAssetProperty"]
    mass_prop = next(p for p in props if p["ID"] == "mass_kg")
    assert mass_prop["Value"] == "5.0"
    assert mass_prop["UnitOfMeasure"] == "kg"


def test_isa95_map_sustainability_layer_full(rich_sustainability):
    mapper = ISA95Mapper(config={})
    result = mapper.map_sustainability_layer(rich_sustainability)
    props = result["PhysicalAssetProperty"]
    ids = [p["ID"] for p in props]
    assert "mass_kg" in ids
    assert "standby_w" in ids
    assert "active_w" in ids
    assert "recycled_content_pct" in ids
    assert "remanufacture_eligible" in ids


# ---------------------------------------------------------------------------
# ISA-95 — map_provenance_layer
# ---------------------------------------------------------------------------

def test_isa95_map_provenance_layer_empty():
    mapper = ISA95Mapper(config={})
    result = mapper.map_provenance_layer(ProvenanceLayer(signatures=[], trace_links=[]))
    assert result["WorkCertificate"] == []
    assert result["OperationsEventRecord"] == []


def test_isa95_map_provenance_layer_with_data(rich_provenance):
    mapper = ISA95Mapper(config={})
    result = mapper.map_provenance_layer(rich_provenance)

    assert len(result["WorkCertificate"]) == 1
    cert = result["WorkCertificate"][0]
    assert cert["IssuedBy"] == "NMIS QA"
    assert cert["CertificateType"] == "ISO-9001"

    assert "epcis://event/001" in result["OperationsEventRecord"]


# ---------------------------------------------------------------------------
# ISA-95 — validate_mapping
# ---------------------------------------------------------------------------

def test_isa95_validate_mapping_valid(sample_dpp):
    mapper = ISA95Mapper(config={})
    mapped = mapper.map_dpp(sample_dpp)
    assert mapped["schema"] == "ISA-95"


def test_isa95_validate_mapping_schema_mismatch():
    mapper = ISA95Mapper(config={})
    valid, errors = mapper.validate_mapping({"schema": "WRONG"})
    assert not valid
    assert any("mismatch" in e.lower() for e in errors)


def test_isa95_validate_mapping_missing_id():
    mapper = ISA95Mapper(config={})
    valid, errors = mapper.validate_mapping({
        "schema": "ISA-95",
        "identity": {"ID": ""},
        "structure": {"NestedEquipment": [{"ID": "P1"}]},
        "lifecycle": {},
    })
    assert not valid
    assert any("ID" in e for e in errors)


def test_isa95_validate_mapping_missing_structure():
    mapper = ISA95Mapper(config={})
    valid, errors = mapper.validate_mapping({
        "schema": "ISA-95",
        "identity": {"ID": "EQ-001"},
        "structure": {},
        "lifecycle": {},
    })
    assert not valid
    assert any("Hierarchy" in e or "NestedEquipment" in e for e in errors)

