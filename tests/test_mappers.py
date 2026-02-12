"""
test_mappers.py

Tests for ECLASS and ISA-95 mappers.
"""

import pytest
from nmis_dpp.mappers.eclass_mapper import ECLASSMapper
from nmis_dpp.mappers.isa95_mapper import ISA95Mapper
from nmis_dpp.model import (
    DigitalProductPassport, IdentityLayer, StructureLayer, LifecycleLayer, 
    RiskLayer, SustainabilityLayer, ProvenanceLayer
)
from nmis_dpp.part_class import PartClass

@pytest.fixture
def sample_dpp():
    part = PartClass(part_id="P1", name="Part1", type="Actuator", properties={"torque": 10})
    return DigitalProductPassport(
        identity=IdentityLayer(
            global_ids={"gtin": "123"}, 
            make_model={"brand": "BrandX", "model": "Mod1"}, 
            ownership={"manufacturer": "MfgCo"}, 
            conformity=[]
        ),
        structure=StructureLayer(
            hierarchy={}, 
            parts=[part], 
            interfaces=[], 
            materials=[], 
            bom_refs=[]
        ),
        lifecycle=LifecycleLayer(
            manufacture={"date": "2023-01-01", "lot": "L1"}, 
            use={}, 
            serviceability={}, 
            events=[], 
            end_of_life={}
        ),
        risk=RiskLayer(criticality={}, fmea=[], security={}),
        sustainability=SustainabilityLayer(
            mass=1.0, 
            energy={}, 
            recycled_content={}, 
            remanufacture={}
        ),
        provenance=ProvenanceLayer(signatures=[], trace_links=[])
    )

def test_eclass_mapper(sample_dpp):
    # Empty config for test
    mapper = ECLASSMapper(config={})
    assert mapper.get_schema_name() == "ECLASS"
    
    mapped = mapper.map_dpp(sample_dpp)
    
    assert mapped["schema"] == "ECLASS"
    assert mapped["identity"]["manufacturerId"] == "MfgCo"
    
    # Check parts mapping
    parts = mapped["structure"]["components"]
    assert len(parts) == 1
    assert parts[0]["name"] == "Part1"
    # Without config or binding, eclassIrdi should be None or derived from minimal config logic
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
    
