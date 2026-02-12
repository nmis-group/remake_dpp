"""
nmis_dpp package initializer.

This module exposes key Digital Product Passport layers and universal part classes
for easy import, along with serialization utilities and the schema registry.
"""

from .model import (
    IdentityLayer, StructureLayer, LifecycleLayer, RiskLayer,
    SustainabilityLayer, ProvenanceLayer, DigitalProductPassport
)
from .part_class import (
    PartClass, PowerConversion, EnergyStorage, Actuator, Sensor,
    ControlUnit, UserInterface, Thermal, Fluidics, Structural,
    Transmission, Protection, Connectivity, SoftwareModule,
    Consumable, Fastener
)
from .utils import to_dict, to_json, validate_part_class

# Import registry and default registration
from .schema_registry import (
    SchemaRegistry, get_global_registry, register_default_mappers
)

# Import build mapping modules (requested to be available)
from . import eclass_build_mapping
from . import isa95_build_mapping

# Register built-in mappers by default
register_default_mappers()

__all__ = [
    # Layers
    "IdentityLayer", "StructureLayer", "LifecycleLayer", "RiskLayer",
    "SustainabilityLayer", "ProvenanceLayer", "DigitalProductPassport",
    # Part classes
    "PartClass", "PowerConversion", "EnergyStorage", "Actuator", "Sensor",
    "ControlUnit", "UserInterface", "Thermal", "Fluidics", "Structural",
    "Transmission", "Protection", "Connectivity", "SoftwareModule",
    "Consumable", "Fastener",
    # Utils
    "to_dict", "to_json", "validate_part_class",
    # Registry
    "SchemaRegistry", "get_global_registry", "register_default_mappers",
    # Build mappings
    "eclass_build_mapping", "isa95_build_mapping"
]
