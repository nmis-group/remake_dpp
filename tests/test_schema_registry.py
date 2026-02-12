"""
test_schema_registry.py

Tests for the SchemaRegistry class in nmis_dpp.schema_registry.

Goals:
- Verify default config_dir is derived correctly when not provided.
- Verify schema names are normalized to config filenames with
  schema_name.lower().replace('-', '') + "_mapping.yml".
- Verify YAML loading with yaml.safe_load:
  - Returns the parsed dict when the file exists and is valid.
  - Returns {} when the file is missing.
  - Returns {} when the file contains invalid YAML.
- Verify that get_mapper() passes the loaded config into the mapper instance.
"""

from pathlib import Path

import yaml

from nmis_dpp.schema_registry import SchemaRegistry
from nmis_dpp.schema_base import SchemaMapper


def test_schema_registry_default_config_dir():
    """
    Ensure that when SchemaRegistry is constructed with no config_dir,
    it derives the default directory as Path(__file__).parent / "config"
    inside the nmis_dpp package.

    We do not assert the full path, only the last parts, because the
    test environment/layout might differ, but the convention is that
    config_dir.name == "config" and its parent directory name is "nmis_dpp".
    """
    registry = SchemaRegistry()  # no explicit config_dir

    # Only check tail of the path to avoid test brittleness
    assert registry.config_dir.name == "config"
    assert registry.config_dir.parent.name == "nmis_dpp"


def test_schema_registry_normalizes_schema_name_to_config_filename(tmp_path):
    """
    Test that _load_config() normalizes the canonical schema name
    to the correct YAML filename using:

        file_stub = schema_name.lower().replace('-', '')
        filename = f"{file_stub}_mapping.yml"

    For the schema name "ISA-95", we expect "isa95_mapping.yml".
    """
    # Create a temporary config directory
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    # Expected filename for canonical name "ISA-95"
    config_file = cfg_dir / "isa95_mapping.yml"
    sample_cfg = {"schema_info": {"version": "1.0"}}
    config_file.write_text(yaml.safe_dump(sample_cfg), encoding="utf-8")

    # Initialize registry with our test config dir
    registry = SchemaRegistry(config_dir=cfg_dir)

    # Call the private method directly to test the normalization logic
    loaded = registry._load_config("ISA-95")

    # It should have loaded the YAML we wrote
    assert loaded == sample_cfg


def test_schema_registry_load_config_missing_file_returns_empty(tmp_path):
    """
    Test that _load_config() returns {} when there is no YAML file
    for the given schema.

    Here we do not create any file for "ECLASS", so we expect an empty dict.
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    registry = SchemaRegistry(config_dir=cfg_dir)

    loaded = registry._load_config("ECLASS")

    # No config file means the registry must return {}
    assert loaded == {}


def test_schema_registry_load_config_invalid_yaml_returns_empty(tmp_path):
    """
    Test that _load_config() returns {} when the YAML file is present
    but cannot be parsed by yaml.safe_load (invalid YAML).

    We write deliberately malformed YAML content to the config file
    and assert that the registry falls back to {} rather than raising.
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    bad_file = cfg_dir / "eclass_mapping.yml"
    # Intentionally malformed YAML (unclosed bracket, leading colon).
    # This is valid Python string, but invalid YAML.
    bad_file.write_text(":\n  - invalid: [", encoding="utf-8")

    registry = SchemaRegistry(config_dir=cfg_dir)

    loaded = registry._load_config("ECLASS")

    # On parse error, implementation logs a warning and returns {}
    assert loaded == {}


class DummyMapper(SchemaMapper):
    """
    Minimal concrete implementation of SchemaMapper used for testing.

    It defines the required abstract methods with no-op behaviour, and
    simply stores whatever config it receives. This lets us check that
    SchemaRegistry.get_mapper() passes the loaded configuration into
    the mapper constructor.
    """

    def get_schema_name(self) -> str:
        # This must match the canonical name used in tests ("ECLASS").
        return "ECLASS"

    def get_schema_version(self) -> str:
        return "1.0"

    def map_identity_layer(self, layer):
        # Not relevant for this test; return empty dict.
        return {}

    def map_structure_layer(self, layer):
        # Not relevant for this test; return empty dict.
        return {}

    def map_lifecycle_layer(self, layer):
        # Not relevant for this test; return empty dict.
        return {}

    def map_risk_layer(self, layer):
        # Not relevant for this test; return empty dict.
        return {}

    def map_sustainability_layer(self, layer):
        # Not relevant for this test; return empty dict.
        return {}

    def map_provenance_layer(self, layer):
        # Not relevant for this test; return empty dict.
        return {}

    def validate_mapping(self, mapped):
        # For testing, always treat mapping as valid.
        return True, []

    def get_context(self):
        # Minimal JSON-LD context stub.
        return {"@context": {}}


def test_get_mapper_uses_loaded_config(tmp_path):
    """
    Integration-style test:

    - Write a valid YAML config file for ECLASS.
    - Construct a SchemaRegistry pointing to that config directory.
    - Register DummyMapper (which reports its schema name as "ECLASS").
    - Call get_mapper("ECLASS").
    - Assert that the mapper instance's .config attribute contains the
      configuration we wrote.

    This verifies that:
    - SchemaRegistry looks up and loads the right YAML for "ECLASS".
    - The loaded config is passed into the mapper constructor.
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    cfg = {"schema_info": {"version": "X"}}
    (cfg_dir / "eclass_mapping.yml").write_text(
        yaml.safe_dump(cfg), encoding="utf-8"
    )

    registry = SchemaRegistry(config_dir=cfg_dir)
    registry.register(DummyMapper)

    mapper = registry.get_mapper("ECLASS")

    # The config passed to the mapper should be the same dict we wrote.
    assert mapper.config.get("schema_info", {}).get("version") == "X"
