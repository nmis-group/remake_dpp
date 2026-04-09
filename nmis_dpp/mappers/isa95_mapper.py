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
    Mapper for ISA-95 / B2MML (IEC 62264) — work-order / MES view.
    """

    def get_schema_name(self) -> str:
        return "ISA-95"

    def get_schema_version(self) -> str:
        return "V0600"

    def get_context(self) -> Dict[str, Any]:
        """
        Return JSON-LD @context for ISA-95 / B2MML V0600.

        Covers:
        - B2MML base namespace as @vocab so all unmapped keys are scoped there.
        - Explicit prefixes for ISA-95, ANSI/ISA, and schema.org cross-references.
        """
        return {
            "@vocab":  "http://www.mesa.org/xml/B2MML",
            "isa95":   "http://www.mesa.org/xml/B2MML",
            "b2mml":   "http://www.mesa.org/xml/B2MML",
            "ansi":    "http://www.isa.org/ISA95/",
            "schema":  "https://schema.org/",
            "xsd":     "http://www.w3.org/2001/XMLSchema#",
            # Identity
            "ID":                "isa95:ID",
            "Description":       "isa95:Description",
            "EquipmentLevel":    "isa95:EquipmentLevel",
            # Structure
            "Hierarchy":         "isa95:Hierarchy",
            "NestedEquipment":   "isa95:NestedEquipment",
            "EquipmentClassID":  "isa95:EquipmentClassID",
            # Lifecycle
            "WorkOrder":         "isa95:WorkOrder",
            "ProductionDate":    "schema:dateCreated",
            "Factory":           "isa95:OperationsLocation",
            # Risk
            "MaintenanceInfo":   "isa95:MaintenanceInformation",
            "SafetyLevel":       "ansi:SafetyLevel",
            "MTBF":              "ansi:MTBF",
            "FailureMode":       "ansi:FailureMode",
            # Sustainability (expressed as PhysicalAssetProperty)
            "PhysicalAssetProperty": "isa95:PhysicalAssetProperty",
            # Provenance
            "WorkCertificate":       "isa95:WorkCertificate",
            "OperationsEventRecord": "isa95:OperationsEventRecord",
        }

    def map_identity_layer(self, layer: IdentityLayer) -> Dict[str, Any]:
        """
        Map IdentityLayer to ISA-95 Equipment identity fields.
        """
        brand = layer.make_model.get("brand", "")
        model = layer.make_model.get("model", "")
        description = f"{brand} {model}".strip() or None

        return {
            "ID":             layer.global_ids.get("gtin") or layer.global_ids.get("serial"),
            "Description":    description,
            "EquipmentLevel": "Unit",
            "Manufacturer":   layer.ownership.get("manufacturer"),
            "Conformity":     layer.conformity,
        }

    def map_structure_layer(self, layer: StructureLayer) -> Dict[str, Any]:
        mapped_parts = [self.map_part_class(p) for p in layer.parts]
        return {
            "Hierarchy":       layer.hierarchy,
            "NestedEquipment": mapped_parts,
            "BOMRefs":         layer.bom_refs,
        }

    def map_lifecycle_layer(self, layer: LifecycleLayer) -> Dict[str, Any]:
        return {
            "WorkOrder":      layer.manufacture.get("lot"),
            "ProductionDate": layer.manufacture.get("date"),
            "Factory":        layer.manufacture.get("factory"),
        }

    def map_risk_layer(self, layer: RiskLayer) -> Dict[str, Any]:
        """
        Map RiskLayer to ISA-95 MaintenanceInformation vocabulary.

        criticality → SafetyLevel, MTBF expressed as MaintenanceInfo properties.
        fmea        → list of {FailureMode, Effect, Mitigation}.
        security    → {SBOM, Vulnerabilities, SigningKey, UpdatePolicy}.
        """
        criticality = layer.criticality or {}
        security = layer.security or {}

        fmea_mapped = [
            {
                "FailureMode": entry.get("mode") or entry.get("failureMode", ""),
                "Effect":      entry.get("effect", ""),
                "Mitigation":  entry.get("mitigation", ""),
            }
            for entry in (layer.fmea or [])
        ]

        return {
            "MaintenanceInfo": {
                "SafetyLevel":      criticality.get("safety_level") or criticality.get("safetyLevel"),
                "MissionLevel":     criticality.get("mission_level") or criticality.get("missionLevel"),
                "IsLifeLimitedPart": criticality.get("llp", False),
                "MTBF":             criticality.get("mtbf"),
            },
            "FMEA": fmea_mapped,
            "Security": {
                "SBOM":           security.get("sbom"),
                "Vulnerabilities": security.get("vulnerabilities", []),
                "SigningKey":      security.get("signing_key") or security.get("signingKey"),
                "UpdatePolicy":   security.get("update_policy") or security.get("updatePolicy"),
            },
        }

    def map_sustainability_layer(self, layer: SustainabilityLayer) -> Dict[str, Any]:
        """
        Map SustainabilityLayer using ISA-95 PhysicalAssetProperty elements.

        ISA-95 has no native sustainability layer, so sustainability data is
        expressed as a list of typed PhysicalAssetProperty entries — consistent
        with how equipment properties are handled elsewhere in B2MML.
        """
        properties: List[Dict[str, Any]] = [
            {"ID": "mass_kg", "Value": str(layer.mass), "UnitOfMeasure": "kg"},
        ]

        for key, value in (layer.energy or {}).items():
            properties.append({"ID": key, "Value": str(value)})

        recycled = layer.recycled_content or {}
        if recycled.get("pcr_percent") is not None or recycled.get("postConsumerRecycled") is not None:
            properties.append({
                "ID":    "recycled_content_pct",
                "Value": str(recycled.get("pcr_percent") or recycled.get("postConsumerRecycled")),
                "UnitOfMeasure": "%",
            })

        remanufacture = layer.remanufacture or {}
        if remanufacture.get("eligible") is not None:
            properties.append({
                "ID":    "remanufacture_eligible",
                "Value": str(remanufacture.get("eligible")),
            })

        return {"PhysicalAssetProperty": properties}

    def map_provenance_layer(self, layer: ProvenanceLayer) -> Dict[str, Any]:
        """
        Map ProvenanceLayer to ISA-95 certificate and event record vocabulary.

        signatures  → WorkCertificate entries.
        trace_links → OperationsEventRecord references.
        """
        certificates = [
            {
                "CertificateType": sig.get("certificate", ""),
                "IssuedBy":        sig.get("signed_by") or sig.get("signedBy", ""),
                "IssueDate":       sig.get("date", ""),
            }
            for sig in (layer.signatures or [])
        ]

        return {
            "WorkCertificate":       certificates,
            "OperationsEventRecord": list(layer.trace_links or []),
        }

    def map_part_class(self, part: PartClass) -> Dict[str, Any]:
        """
        Map a PartClass instance to an ISA-95 Equipment element.

        Resolution order for EquipmentClassID:
        1. Explicit ISA-95 OntologyBinding on the part.
        2. Config domain_mappings lookup by part.type.
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

        if not equipment_class:
            logger.warning(
                "No ISA-95 EquipmentClassID resolved for part '%s' (type=%s).",
                part.part_id, part.type,
            )

        return {
            "ID":              part.part_id,
            "EquipmentClassID": equipment_class,
            "Description":     part.name,
            "EquipmentType":   part.type,
            "Properties": [
                {"ID": k, "Value": [str(v)]}
                for k, v in part.properties.items()
            ],
        }

    def validate_mapping(self, mapped_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a mapped ISA-95 document against PRD-required fields.

        Hard errors (return False):
          - schema field must equal "ISA-95".
          - identity.ID must be present and non-empty.
          - structure must contain Hierarchy or NestedEquipment.

        Warnings (logged, do not fail):
          - Both lifecycle.WorkOrder and lifecycle.ProductionDate absent.
        """
        errors: List[str] = []

        # Schema identity check
        if mapped_data.get("schema") != "ISA-95":
            errors.append(
                f"Schema mismatch: expected 'ISA-95', got {mapped_data.get('schema')!r}."
            )

        # Required identity
        identity = mapped_data.get("identity") or {}
        if not identity.get("ID"):
            errors.append("identity.ID is required and must be non-empty.")

        # Required structure
        structure = mapped_data.get("structure") or {}
        if not structure.get("Hierarchy") and not structure.get("NestedEquipment"):
            errors.append(
                "structure must contain at least one of 'Hierarchy' or 'NestedEquipment'."
            )

        # Non-blocking warnings
        lifecycle = mapped_data.get("lifecycle") or {}
        if not lifecycle.get("WorkOrder") and not lifecycle.get("ProductionDate"):
            logger.warning(
                "ISA-95 validate_mapping: both WorkOrder and ProductionDate are absent "
                "(at least one is recommended for MES traceability)."
            )

        return len(errors) == 0, errors
