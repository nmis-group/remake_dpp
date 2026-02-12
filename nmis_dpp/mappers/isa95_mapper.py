"""
isa95_mapper.py

Implementation of SchemaMapper for ISA-95 / B2MML.
"""

from typing import Dict, Any, List, Tuple
import logging

from nmis_dpp.schema_base import SchemaMapper
from nmis_dpp.model import (
    IdentityLayer,
    StructureLayer,
    LifecycleLayer,
    RiskLayer,
    SustainabilityLayer,
    ProvenanceLayer,
)
from nmis_dpp.part_class import PartClass

logger = logging.getLogger(__name__)

class ISA95Mapper(SchemaMapper):
    """
    Mapper for ISA-95 (IEC 62264).
    """

    def get_schema_name(self) -> str:
        return "ISA-95"

    def get_schema_version(self) -> str:
        # Assuming B2MML V0600 or similar based on loose context
        return "V0600"

    def get_context(self) -> Dict[str, Any]:
        """
        Return JSON-LD context for ISA-95.
        """
        return {
            "isa95": "http://www.mesa.org/xml/B2MML-V0600",
        }

    def map_identity_layer(self, layer: IdentityLayer) -> Dict[str, Any]:
        """
        Map to Equipment properties.
        """
        return {
            "ID": layer.global_ids.get("gtin") or layer.global_ids.get("serial"),
            "Description": f"{layer.make_model.get('brand')} {layer.make_model.get('model')}",
            "EquipmentLevel": "Unit", 
        }

    def map_structure_layer(self, layer: StructureLayer) -> Dict[str, Any]:
        mapped_parts = [self.map_part_class(p) for p in layer.parts]
        return {
            "Hierarchy": layer.hierarchy,
            "NestedEquipment": mapped_parts,
        }

    def map_lifecycle_layer(self, layer: LifecycleLayer) -> Dict[str, Any]:
        return {
            "WorkOrder": layer.manufacture.get("lot"),
            "ProductionDate": layer.manufacture.get("date"),
        }

    def map_risk_layer(self, layer: RiskLayer) -> Dict[str, Any]:
        return {}

    def map_sustainability_layer(self, layer: SustainabilityLayer) -> Dict[str, Any]:
        return {}

    def map_provenance_layer(self, layer: ProvenanceLayer) -> Dict[str, Any]:
        return {}

    def map_part_class(self, part: PartClass) -> Dict[str, Any]:
        """
        Map part to ISA-95 Equipment element.
        """
        binding = part.get_binding("ISA-95")
        
        equipment_class = None
        if binding and binding.class_ids:
            equipment_class = binding.class_ids[0]
        
        if not equipment_class:
            domain_mappings = self.config.get("domain_mappings", {})
            domain_map = domain_mappings.get(part.type)
            if domain_map:
                isa_types = domain_map.get("isa95_type_ids", [])
                if isa_types:
                    equipment_class = isa_types[0]

        return {
            "ID": part.part_id,
            "EquipmentClassID": equipment_class,
            "Description": part.name,
            # Map properties to EquipmentProperty
            "Properties": [
                {"ID": k, "Value": [str(v)]} 
                for k, v in part.properties.items()
            ]
        }

    def validate_mapping(self, mapped_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        if not mapped_data.get("schema") == "ISA-95":
             errors.append("Schema mismatch")
        return len(errors) == 0, errors
