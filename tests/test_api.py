"""
test_api.py

Integration tests for the nmis_dpp.api facade:
  create_dpp(), list_input_schemas(), list_output_schemas()
"""

from __future__ import annotations

import csv
import textwrap
from pathlib import Path

import pytest
import yaml

from nmis_dpp.api import create_dpp, list_input_schemas, list_output_schemas

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

# Real ECLASS 16 XML files shipped with the package.
# The domain-scoring algorithm needs a corpus of at least ~3 files to fire;
# using SG_13–SG_15 gives 6 parts and keeps the test fast.
_ECLASS_DIR = (
    Path(__file__).parent.parent
    / "nmis_dpp"
    / "ontology_data"
    / "eclass_16"
    / "dictionary_assets_en"
)
ECLASS_XMLS = sorted(_ECLASS_DIR.glob("ECLASS16_0_ASSET_EN_SG_1[345].xml"))



@pytest.fixture
def csv_dir(tmp_path: Path) -> Path:
    """
    Create a minimal CSV + mapping.yml in a temporary directory.
    The CSV has a manufacturer column so identity.ownership is populated,
    and a gtin column (the 'id' field) so ISA-95 identity.ID is also set.
    Returns the directory path.
    """
    # --- CSV file ---
    rows = [
        {"id": "ROW-001", "name": "Battery Cell", "type": "EnergyStorage",
         "chemistry": "Li-ion", "capacity": "50.0", "voltage": "3.7",
         "manufacturer": "TestCo"},
        {"id": "ROW-002", "name": "Motor Driver", "type": "Actuator",
         "chemistry": "", "capacity": "", "voltage": "24.0",
         "manufacturer": "TestCo"},
    ]
    fieldnames = ["id", "name", "type", "chemistry", "capacity", "voltage", "manufacturer"]
    csv_path = tmp_path / "parts.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # --- mapping.yml ---
    # identity.global_ids / ownership map field→column_name
    # parts sub-dict maps part_id/name/type to columns; properties is a list
    # of {column, key} pairs.
    mapping = {
        "identity": {
            "global_ids": {"gtin": "id"},
            "make_model": {"model": "name"},
            "ownership":  {"manufacturer": "manufacturer"},
        },
        "parts": {
            "part_id":    "id",
            "name":       "name",
            "type":       "type",
            "properties": [
                {"column": "chemistry", "key": "chemistry"},
                {"column": "capacity",  "key": "capacity"},
                {"column": "voltage",   "key": "voltage"},
            ],
        },
    }
    mapping_path = tmp_path / "mapping.yml"
    with mapping_path.open("w", encoding="utf-8") as fh:
        yaml.dump(mapping, fh)

    return tmp_path


# ---------------------------------------------------------------------------
# test_create_dpp_eclass_to_eclass  (round-trip)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    len(ECLASS_XMLS) < 3,
    reason="ECLASS XML ontology files SG_13/14/15 not present",
)
def test_create_dpp_eclass_to_eclass(tmp_path):
    """
    End-to-end round-trip: real ECLASS XML → DPP → ECLASS output schema.

    Three files are needed so the domain-scoring algorithm fires and produces
    at least one part.  A minimal eclass_config.yml supplies the manufacturer
    identity required by the ECLASS mapper validator.
    """
    cfg = {
        "identity": {
            "ownership":  {"manufacturer": "NMIS-Test"},
            "global_ids": {"serial": "SN-ECLASS-TEST-001"},
        }
    }
    (tmp_path / "eclass_config.yml").write_text(yaml.dump(cfg), encoding="utf-8")

    result = create_dpp(
        input_schema="ECLASS",
        output_schema="ECLASS",
        files=ECLASS_XMLS,
        config_dir=tmp_path,
    )
    assert result["schema"] == "ECLASS"
    assert "identity" in result
    assert result["identity"]["manufacturerId"] == "NMIS-Test"
    assert "structure" in result
    assert len(result["structure"]["components"]) >= 1


# ---------------------------------------------------------------------------
# test_create_dpp_csv_to_eclass
# ---------------------------------------------------------------------------

def test_create_dpp_csv_to_eclass(csv_dir: Path):
    """CSV + mapping.yml → ECLASS output; parts appear in structure.components."""
    result = create_dpp(
        input_schema="CSV",
        output_schema="ECLASS",
        files=[csv_dir / "parts.csv"],
        config_dir=csv_dir,
    )
    assert result["schema"] == "ECLASS"
    components = result["structure"]["components"]
    assert len(components) == 2
    ids = [c["id"] for c in components]
    assert "ROW-001" in ids
    assert "ROW-002" in ids


# ---------------------------------------------------------------------------
# test_create_dpp_csv_to_isa95
# ---------------------------------------------------------------------------

def test_create_dpp_csv_to_isa95(csv_dir: Path):
    """CSV + mapping.yml → ISA-95 output; parts appear as NestedEquipment."""
    result = create_dpp(
        input_schema="csv",          # case-insensitive alias
        output_schema="ISA-95",
        files=[csv_dir / "parts.csv"],
        config_dir=csv_dir,
    )
    assert result["schema"] == "ISA-95"
    nested = result["structure"]["NestedEquipment"]
    assert len(nested) == 2


# ---------------------------------------------------------------------------
# test_create_dpp_unknown_input_schema
# ---------------------------------------------------------------------------

def test_create_dpp_unknown_input_schema(csv_dir: Path):
    """An unrecognised input_schema raises ValueError naming the bad value."""
    with pytest.raises(ValueError, match="Unknown input_schema"):
        create_dpp(
            input_schema="STEP-XML",
            output_schema="ECLASS",
            files=[csv_dir / "parts.csv"],
            config_dir=csv_dir,
        )


# ---------------------------------------------------------------------------
# test_create_dpp_unknown_output_schema
# ---------------------------------------------------------------------------

def test_create_dpp_unknown_output_schema(csv_dir: Path):
    """An unrecognised output_schema propagates KeyError from the registry."""
    with pytest.raises(KeyError):
        create_dpp(
            input_schema="CSV",
            output_schema="NO_SUCH_SCHEMA",
            files=[csv_dir / "parts.csv"],
            config_dir=csv_dir,
        )


# ---------------------------------------------------------------------------
# test_create_dpp_csv_missing_mapping_yml
# ---------------------------------------------------------------------------

def test_create_dpp_csv_missing_mapping_yml(tmp_path: Path):
    """config_dir that contains no mapping.yml raises ValueError."""
    csv_path = tmp_path / "parts.csv"
    csv_path.write_text("id,name,type\nR1,Part,Actuator\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mapping.yml"):
        create_dpp(
            input_schema="CSV",
            output_schema="ECLASS",
            files=[csv_path],
            config_dir=tmp_path,   # no mapping.yml here
        )


def test_create_dpp_csv_none_config_dir():
    """config_dir=None for CSV input raises ValueError."""
    with pytest.raises(ValueError, match="config_dir is required"):
        create_dpp(
            input_schema="CSV",
            output_schema="ECLASS",
            files=[Path("irrelevant.csv")],
            config_dir=None,
        )


# ---------------------------------------------------------------------------
# test_list_input_schemas
# ---------------------------------------------------------------------------

def test_list_input_schemas():
    schemas = list_input_schemas()
    assert "ECLASS" in schemas
    assert "ISA-95" in schemas
    assert "CSV" in schemas


# ---------------------------------------------------------------------------
# test_list_output_schemas
# ---------------------------------------------------------------------------

def test_list_output_schemas():
    schemas = list_output_schemas()
    assert "ECLASS" in schemas
    assert "ISA-95" in schemas
    assert "BatteryDPP" in schemas
