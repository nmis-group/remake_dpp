"""
eclass_mapper.py

Implementation of SchemaMapper for ECLASS 16.
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


class ECLASSMapper(SchemaMapper):
    """
    Mapper for ECLASS 16.0 — Generic DPP (ECLASS vocabulary) JSON-LD.
    """

    def get_schema_name(self) -> str:
        return "ECLASS"

    def get_schema_version(self) -> str:
        return "16.0"

    def get_context(self) -> Dict[str, Any]:
        """
        Return JSON-LD @context for ECLASS 16.0.

        Covers:
        - Core ECLASS namespace and IRDI property prefix.
        - schema.org terms reused for common identity/lifecycle fields.
        - @vocab fallback so any unmapped key is scoped to the ECLASS namespace.
        """
        return {
            "@vocab": "https://eclass.eu/eclass-standard/v16-0/",
            "eclass": "https://eclass.eu/eclass-standard/v16-0/",
            "irdi": "https://eclass.eu/irdi/0173-1#02-",
            "schema": "https://schema.org/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            # Identity
            "manufacturerId":   "eclass:manufacturerId",
            "manufacturerPartId": "eclass:manufacturerPartId",
            "serialNumber":     "schema:serialNumber",
            "gtin":             "schema:gtin",
            # Structure
            "components":       "eclass:components",
            "eclassIrdi":       "eclass:classificationCode",
            "attributes":       "eclass:attributes",
            # Lifecycle
            "manufactureDate":  "schema:dateCreated",
            "batchId":          "eclass:batchId",
            # Risk
            "safetyLevel":      "eclass:safetyLevel",
            "mtbf":             "eclass:mtbf",
            "failureMode":      "eclass:failureMode",
            "sbom":             "eclass:sbom",
            # Sustainability
            "mass":             "eclass:mass",
            "energy":           "eclass:energy",
            "recycledContent":  "eclass:recycledContent",
            # Provenance
            "signatures":       "eclass:signatures",
            "traceLinks":       "eclass:traceLinks",
        }

    def map_identity_layer(self, layer: IdentityLayer) -> Dict[str, Any]:
        """
        Map IdentityLayer to ECLASS identity properties.
        """
        return {
            "manufacturerId":    layer.ownership.get("manufacturer"),
            "manufacturerPartId": layer.global_ids.get("manufacturer_pn"),
            "serialNumber":      layer.global_ids.get("serial"),
            "gtin":              layer.global_ids.get("gtin"),
            "conformity":        layer.conformity,
        }

    def map_structure_layer(self, layer: StructureLayer) -> Dict[str, Any]:
        """
        Map StructureLayer, converting each PartClass via map_part_class.
        """
        mapped_parts = [self.map_part_class(p) for p in layer.parts]
        return {
            "hierarchy":  layer.hierarchy,
            "components": mapped_parts,
            "bomRefs":    layer.bom_refs,
        }

    def map_lifecycle_layer(self, layer: LifecycleLayer) -> Dict[str, Any]:
        return {
            "manufactureDate": layer.manufacture.get("date"),
            "batchId":         layer.manufacture.get("lot"),
            "factory":         layer.manufacture.get("factory"),
        }

    def map_risk_layer(self, layer: RiskLayer) -> Dict[str, Any]:
        """
        Map RiskLayer to ECLASS risk/reliability properties.

        criticality  → safetyLevel, mtbf
        fmea entries → list of {failureMode, effect, mitigation}
        security     → {sbom, vulnerabilities, signingKey, updatePolicy}
        """
        criticality = layer.criticality or {}
        security = layer.security or {}

        fmea_mapped = [
            {
                "failureMode": entry.get("mode") or entry.get("failureMode", ""),
                "effect":      entry.get("effect", ""),
                "mitigation":  entry.get("mitigation", ""),
            }
            for entry in (layer.fmea or [])
        ]

        return {
            "criticality": {
                "safetyLevel": criticality.get("safety_level") or criticality.get("safetyLevel"),
                "missionLevel": criticality.get("mission_level") or criticality.get("missionLevel"),
                "isLifeLimitedPart": criticality.get("llp", False),
                "mtbf": criticality.get("mtbf"),
            },
            "fmea": fmea_mapped,
            "security": {
                "sbom":          security.get("sbom"),
                "vulnerabilities": security.get("vulnerabilities", []),
                "signingKey":    security.get("signing_key") or security.get("signingKey"),
                "updatePolicy":  security.get("update_policy") or security.get("updatePolicy"),
            },
        }

    def map_sustainability_layer(self, layer: SustainabilityLayer) -> Dict[str, Any]:
        """
        Map SustainabilityLayer to ECLASS sustainability properties.
        """
        recycled = layer.recycled_content or {}
        remanufacture = layer.remanufacture or {}
        return {
            "mass": layer.mass,
            "energy": layer.energy,
            "recycledContent": {
                "postConsumerRecycled": recycled.get("pcr_percent") or recycled.get("postConsumerRecycled"),
                "bioBased":             recycled.get("bio_based_percent") or recycled.get("bioBased"),
                "restrictedSubstances": recycled.get("restricted_substances", []),
            },
            "remanufacture": {
                "eligible": remanufacture.get("eligible"),
                "grade":    remanufacture.get("grade"),
            },
        }

    def map_provenance_layer(self, layer: ProvenanceLayer) -> Dict[str, Any]:
        """
        Map ProvenanceLayer to ECLASS provenance properties.

        signatures  → list of {signedBy, certificate, date}
        trace_links → pass-through list
        """
        signatures_mapped = [
            {
                "signedBy":    sig.get("signed_by") or sig.get("signedBy", ""),
                "certificate": sig.get("certificate", ""),
                "date":        sig.get("date", ""),
            }
            for sig in (layer.signatures or [])
        ]

        return {
            "signatures": signatures_mapped,
            "traceLinks": list(layer.trace_links or []),
        }

    def map_part_class(self, part: PartClass) -> Dict[str, Any]:
        """
        Map a PartClass instance to an ECLASS component representation.

        Resolution order for eclassIrdi:
        1. Explicit ECLASS OntologyBinding on the part.
        2. Config domain_mappings lookup by part.type.
        """
        binding = part.get_binding("ECLASS")

        eclass_classification = None
        if binding and binding.class_ids:
            eclass_classification = binding.class_ids[0]

        if not eclass_classification:
            domain_mappings = self.config.get("domain_mappings", {})
            domain_map = domain_mappings.get(part.type)
            if domain_map:
                classes = domain_map.get("eclass_classes", {})
                if classes:
                    eclass_classification = list(classes.keys())[0]

        if not eclass_classification:
            logger.warning(
                "No ECLASS IRDI resolved for part '%s' (type=%s).",
                part.part_id, part.type,
            )

        return {
            "id":         part.part_id,
            "name":       part.name,
            "type":       part.type,
            "eclassIrdi": eclass_classification,
            "attributes": part.properties,
        }

    def validate_mapping(self, mapped_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a mapped ECLASS DPP document against PRD-required fields.

        Hard errors (return False):
          - schema field must equal "ECLASS".
          - identity must contain manufacturerId or serialNumber.
          - structure.components must be a non-empty list.

        Warnings (logged, do not fail):
          - lifecycle.manufactureDate absent.
        """
        errors: List[str] = []

        # Schema identity check
        if mapped_data.get("schema") != "ECLASS":
            errors.append(
                f"Schema mismatch: expected 'ECLASS', got {mapped_data.get('schema')!r}."
            )

        # Required identity fields
        identity = mapped_data.get("identity") or {}
        if not identity.get("manufacturerId") and not identity.get("serialNumber"):
            errors.append(
                "identity: at least one of 'manufacturerId' or 'serialNumber' is required."
            )

        # Required structure
        structure = mapped_data.get("structure") or {}
        components = structure.get("components")
        if not components:
            errors.append("structure.components must be a non-empty list.")

        # Non-blocking warnings
        lifecycle = mapped_data.get("lifecycle") or {}
        if not lifecycle.get("manufactureDate"):
            logger.warning(
                "ECLASS validate_mapping: lifecycle.manufactureDate is absent "
                "(recommended for EU DPP compliance)."
            )

        return len(errors) == 0, errors
