"""
test_registry_extended.py

Extended tests for SchemaRegistry covering:
- Lazy loading (success/failure)
- Alias resolution
- Metadata inspection (info)
"""

import pytest
from unittest.mock import patch, MagicMock
from nmis_dpp.schema_registry import SchemaRegistry
from nmis_dpp.schema_base import SchemaMapper

class MockMapper(SchemaMapper):
    def get_schema_name(self): return "MOCK"
    def get_schema_version(self): return "1.0"
    def get_context(self): return {}
    def map_identity_layer(self, l): return {}
    def map_structure_layer(self, l): return {}
    def map_lifecycle_layer(self, l): return {}
    def map_risk_layer(self, l): return {}
    def map_sustainability_layer(self, l): return {}
    def map_provenance_layer(self, l): return {}
    def validate_mapping(self, d): return True, []

@pytest.fixture
def registry():
    return SchemaRegistry()

def test_lazy_loading_success(registry):
    """Test that register_lazy correctly imports and instantiates a mapper."""
    # Patch builtins.__import__ to intercept the import call inside lazy_loader
    with patch("builtins.__import__") as mock_import:
        mock_module = MagicMock()
        mock_module.MyMapper = MockMapper
        mock_import.return_value = mock_module

        registry.register_lazy(
            canonical_name="MOCK_SCHEMA",
            module_path="dummy.module",
            class_name="MyMapper"
        )

        # Trigger load
        mapper = registry.get_mapper("MOCK_SCHEMA")
        
        # Verify it called __import__ with correct args
        mock_import.assert_called_with("dummy.module", fromlist=["MyMapper"])
        assert isinstance(mapper, MockMapper)
        assert mapper.get_schema_name() == "MOCK"

def test_lazy_loading_failure_module_not_found(registry):
    """Test failure when the module does not exist."""
    # We rely on the real import system failing for a non-existent module
    # No need to patch here if we use a name guaranteed not to exist
    registry.register_lazy("BAD_MODULE", "non.existent.module.xyz", "SomeClass")
    
    with pytest.raises(ImportError): # __import__ raises ModuleNotFoundError which inherits from ImportError
        registry.get_mapper("BAD_MODULE")

def test_lazy_loading_failure_class_not_found(registry):
    """Test failure when module exists but class does not."""
    with patch("builtins.__import__") as mock_import:
        mock_module = MagicMock()
        # To simulate class missing, ensure getattr fails or it's just not there.
        # MagicMock usually creates attributes on access.
        # We can explicitly set side_effect of getattr on the return value?
        # Or just use an object that is NOT a mock as the module.
        class EmptyModule: pass
        mock_import.return_value = EmptyModule()

        registry.register_lazy("MISSING_CLASS", "dummy.module", "MissingClass")

        with pytest.raises(AttributeError):
             registry.get_mapper("MISSING_CLASS")

def test_lazy_loading_failure_invalid_type(registry):
    """Test failure when the loaded class is not a SchemaMapper."""
    with patch("builtins.__import__") as mock_import:
        mock_module = MagicMock()
        class NotAMapper:
            def __init__(self, config=None): pass
        
        mock_module.NotAMapper = NotAMapper
        mock_import.return_value = mock_module

        registry.register_lazy("BAD_TYPE", "dummy.module", "NotAMapper")

        with pytest.raises(TypeError, match="is not a SchemaMapper"):
            registry.get_mapper("BAD_TYPE")

def test_alias_resolution(registry):
    """Test that we can retrieve a mapper by its aliases."""
    registry.register(MockMapper, aliases=["mock_alias", "mm"])
    
    # "MOCK" is the name returned by MockMapper.get_schema_name
    
    m1 = registry.get_mapper("MOCK") 
    m2 = registry.get_mapper("mock_alias")
    m3 = registry.get_mapper("mm")
    
    assert isinstance(m1, MockMapper)
    assert m1 is m2
    assert m2 is m3
    
    # Internal check utilizing private method (if we really want to be sure)
    assert registry._resolve_canonical_name("mock_alias") == "MOCK"

def test_list_aliases(registry):
    # Register purely via class
    registry.register(MockMapper, aliases=["a1", "a2"])
    
    aliases = registry.list_aliases("MOCK")
    assert "a1" in aliases
    assert "a2" in aliases

def test_info_metadata(registry):
    """Test the info() method."""
    registry.register(MockMapper, aliases=["alias1"])
    
    info = registry.info("MOCK")
    assert info["name"] == "MOCK"
    assert info["version"] == "1.0"
    assert "alias1" in info["aliases"]
    assert info["canonical_name"] == "MOCK"
    
    # Alias lookup
    info_alias = registry.info("alias1")
    assert info_alias == info

def test_info_missing(registry):
    """Test info() for unknown schema."""
    # The implementation returns a dict with 'error' key, does NOT raise
    result = registry.info("NON_EXISTENT")
    assert "error" in result
    assert "not registered" in result["error"]
