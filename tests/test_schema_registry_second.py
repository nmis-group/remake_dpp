from pathlib import Path
import yaml

from nmis_dpp.schema_registry import SchemaRegistry
from nmis_dpp.schema_base import SchemaMapper


class RecordingMapper(SchemaMapper):
    """
    Simple mapper that just stores the config passed into __init__.
    Used to verify that SchemaRegistry.get_mapper() calls _load_config()
    and passes that config into the mapper.
    """
    def __init__(self, config=None):
        super().__init__(config=config)
        # Optionally keep a flag for test visibility
        self.init_called = True

    def get_schema_name(self) -> str:
        return "ECLASS"

    def get_schema_version(self) -> str:
        return "1.0"

    # Minimal no-op implementations for abstract methods:
    def map_identity_layer(self, layer): return {}
    def map_structure_layer(self, layer): return {}
    def map_lifecycle_layer(self, layer): return {}
    def map_risk_layer(self, layer): return {}
    def map_sustainability_layer(self, layer): return {}
    def map_provenance_layer(self, layer): return {}
    def validate_mapping(self, mapped): return True, []
    def get_context(self): return {"@context": {}}


def test_get_mapper_constructs_mapper_with_loaded_config(tmp_path):
    """
    Confirm that SchemaRegistry.get_mapper(schema_name) constructs the mapper
    with the config dictionary returned by _load_config(schema_name).

    Steps:
    - Create a temp config dir.
    - Write eclass_mapping.yml with a known value.
    - Create a SchemaRegistry pointing at that config dir.
    - Register RecordingMapper as the ECLASS mapper.
    - Call get_mapper("ECLASS").
    - Assert that mapper.config == the YAML content we wrote.
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    expected_config = {"schema_info": {"version": "X", "note": "test-config"}}
    (cfg_dir / "eclass_mapping.yml").write_text(
        yaml.safe_dump(expected_config),
        encoding="utf-8"
    )

    registry = SchemaRegistry(config_dir=cfg_dir)
    registry.register(RecordingMapper)

    mapper = registry.get_mapper("ECLASS")

    # Mapper should have been constructed with exactly what _load_config returned.
    assert mapper.config == expected_config
