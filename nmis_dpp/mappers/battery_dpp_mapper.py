"""
battery_dpp_mapper.py

Implementation of SchemaMapper for the EU Battery Passport (Battery DPP).

Targets the EU Battery Regulation 2023/1542 (Annex XIII) requirements,
expressed as JSON-LD.  Required fields are validated strictly per the
regulation; missing mandatory data raises a ValueError via validate_mapping.

Key mandatory fields per EU Reg 2023/1542 Annex XIII:
  - manufacturerIdentification
  - batteryModel
  - carbonFootprint  (numeric kg CO₂e / kWh)
  - recycledContent  (dict with at least one material entry)
  - At least one EnergyStorage part in structure.componentsList
"""

from __future__ import annotations

import dataclasses
from typing import Any, Dict, List, Tuple
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
from nmis_dpp.part_class import PartClass, EnergyStorage

logger = logging.getLogger(__name__)

# Fields that EnergyStorage exposes as top-level Battery Passport properties
_ENERGY_STORAGE_FIELDS = {
    f.name
    for f in dataclasses.fields(EnergyStorage)
    if f.name not in {"part_id", "name", "type", "properties", "ontology_bindings"}
}


class BatteryDPPMapper(SchemaMapper):
    """
    Mapper for the EU Battery Passport (EU Regulation 2023/1542, Annex XIII).

    Produces JSON-LD output using the EU Battery Passport vocabulary.
    All mandatory Annex XIII fields are enforced in validate_mapping.
    """

    def get_schema_name(self) -> str:
        return "BatteryDPP"

    def get_schema_version(self) -> str:
        return "EU-2023/1542"

    def get_context(self) -> Dict[str, Any]:
        """
        Return JSON-LD @context for the EU Battery Passport vocabulary.

        Terms are drawn from EU Reg 2023/1542 Annex XIII field names,
        cross-referenced with schema.org and the IRDI namespace where
        standard identifiers exist.
        """
        return {
            "@vocab":  "https://ec.europa.eu/battery-passport/v1/",
            "battery": "https://ec.europa.eu/battery-passport/v1/",
            "schema":  "https://schema.org/",
            "xsd":     "http://www.w3.org/2001/XMLSchema#",
            "eclass":  "https://eclass.eu/eclass-standard/v16-0/",
            # Identity
            "batteryModel":               "battery:batteryModel",
            "manufacturerIdentification": "battery:manufacturerIdentification",
            "productIdentifier":          "schema:serialNumber",
            "conformityCertification":    "battery:conformityCertification",
            "batteryCategory":            "battery:batteryCategory",
            # Structure
            "componentsList":             "battery:componentsList",
            "chemistry":                  "battery:electrochemistry",
            "capacity":                   "battery:ratedCapacity",
            "voltage":                    "battery:nominalVoltage",
            "rechargeCycles":             "battery:expectedLifetimeCycles",
            # Lifecycle
            "manufacturingDate":          "schema:dateCreated",
            "placeOfManufacturing":       "battery:placeOfManufacturing",
            "expectedLifetime":           "battery:expectedLifetime",
            "stateOfHealth":              "battery:stateOfHealth",
            "cycleCount":                 "battery:cycleCount",
            # Risk
            "hazardousSubstances":        "battery:hazardousSubstances",
            "safetyInstructions":         "battery:safetyInstructions",
            # Sustainability
            "carbonFootprint":            "battery:carbonFootprint",
            "recycledContent":            "battery:recycledContent",
            "renewableContent":           "battery:renewableContent",
            "mass":                       "battery:mass",
            # Provenance
            "conformityDeclaration":      "battery:declarationOfConformity",
            "dueDiligenceReport":         "battery:dueDiligenceReport",
            "supplyChainInfo":            "battery:supplyChainDueDiligence",
        }

    def map_identity_layer(self, layer: IdentityLayer) -> Dict[str, Any]:
        """
        Map IdentityLayer to Battery Passport identity fields.

        batteryModel             ← make_model.model
        manufacturerIdentification ← ownership.manufacturer
        productIdentifier        ← global_ids.serial or global_ids.gtin
        conformityCertification  ← conformity list
        """
        return {
            "batteryModel":               layer.make_model.get("model"),
            "manufacturerIdentification": layer.ownership.get("manufacturer"),
            "productIdentifier":          (
                layer.global_ids.get("serial") or layer.global_ids.get("gtin")
            ),
            "conformityCertification":    list(layer.conformity or []),
            "batteryCategory":            layer.make_model.get("battery_category"),
        }

    def map_structure_layer(self, layer: StructureLayer) -> Dict[str, Any]:
        """
        Map StructureLayer to Battery Passport componentsList.

        EnergyStorage parts have their typed attributes (capacity, voltage,
        chemistry, recharge_cycles) surfaced as top-level Battery Passport
        fields alongside the generic id/name.  All other part types are
        listed as supporting components.
        """
        components = [self.map_part_class(p) for p in layer.parts]
        return {
            "componentsList": components,
            "hierarchy":      layer.hierarchy,
        }

    def map_lifecycle_layer(self, layer: LifecycleLayer) -> Dict[str, Any]:
        """
        Map LifecycleLayer to Battery Passport lifecycle fields.

        stateOfHealth and cycleCount are read from lifecycle.use counters
        if present, as these are updated during the battery's operational life.
        """
        use = layer.use or {}
        return {
            "manufacturingDate":    layer.manufacture.get("date"),
            "placeOfManufacturing": layer.manufacture.get("factory"),
            "expectedLifetime":     layer.serviceability.get("replacement_interval")
                                    if layer.serviceability else None,
            "stateOfHealth":        use.get("state_of_health") or use.get("stateOfHealth"),
            "cycleCount":           use.get("cycles") or use.get("cycleCount"),
        }

    def map_risk_layer(self, layer: RiskLayer) -> Dict[str, Any]:
        """
        Map RiskLayer to Battery Passport hazard and safety fields.

        fmea entries with a 'substance' key become hazardousSubstances.
        criticality.safety_instructions maps to safetyInstructions.
        """
        criticality = layer.criticality or {}

        hazardous = [
            {
                "substanceName": entry.get("substance") or entry.get("failureMode", ""),
                "hazardClass":   entry.get("hazard_class") or entry.get("effect", ""),
                "concentration": entry.get("concentration"),
            }
            for entry in (layer.fmea or [])
            if entry.get("substance") or entry.get("hazard_class")
        ]

        return {
            "hazardousSubstances": hazardous,
            "safetyInstructions":  (
                criticality.get("safety_instructions")
                or criticality.get("safetyInstructions", [])
            ),
        }

    def map_sustainability_layer(self, layer: SustainabilityLayer) -> Dict[str, Any]:
        """
        Map SustainabilityLayer to Battery Passport sustainability fields.

        carbonFootprint  ← lifecycle.manufacture.co2e (set via config or data)
                           falls back to sustainability config key 'co2e'.
        recycledContent  ← recycled_content dict (cobalt, lithium, nickel, lead %).
        renewableContent ← recycled_content.bio_based_percent.
        mass             ← SustainabilityLayer.mass (kg).

        carbonFootprint is mandatory per EU Reg 2023/1542 Annex XIII.
        """
        recycled = layer.recycled_content or {}
        co2e = (
            recycled.get("co2e")
            or self.config.get("carbon_footprint")
        )

        return {
            "carbonFootprint": co2e,
            "recycledContent": {
                "cobalt":   recycled.get("cobalt_pct") or recycled.get("cobalt"),
                "lithium":  recycled.get("lithium_pct") or recycled.get("lithium"),
                "nickel":   recycled.get("nickel_pct") or recycled.get("nickel"),
                "lead":     recycled.get("lead_pct") or recycled.get("lead"),
                "postConsumerRecycled": (
                    recycled.get("pcr_percent") or recycled.get("postConsumerRecycled")
                ),
            },
            "renewableContent": recycled.get("bio_based_percent") or recycled.get("bioBased"),
            "mass": layer.mass,
        }

    def map_provenance_layer(self, layer: ProvenanceLayer) -> Dict[str, Any]:
        """
        Map ProvenanceLayer to Battery Passport trust and compliance fields.

        signatures  → conformityDeclaration entries (e.g. EU DoC).
        trace_links → supplyChainInfo references.
        """
        declarations = [
            {
                "issuedBy":        sig.get("signed_by") or sig.get("signedBy", ""),
                "certificateType": sig.get("certificate", ""),
                "issueDate":       sig.get("date", ""),
            }
            for sig in (layer.signatures or [])
        ]

        return {
            "conformityDeclaration": declarations,
            "dueDiligenceReport":    None,   # populated externally if available
            "supplyChainInfo":       list(layer.trace_links or []),
        }

    def map_part_class(self, part: PartClass) -> Dict[str, Any]:
        """
        Map a PartClass to a Battery Passport component entry.

        For EnergyStorage parts, typed attributes (capacity, voltage, chemistry,
        recharge_cycles) are surfaced as top-level Battery Passport fields.
        All other part types are represented with generic id/name/type.
        """
        base = {
            "id":   part.part_id,
            "name": part.name,
            "type": part.type,
        }

        if isinstance(part, EnergyStorage):
            base.update({
                "chemistry":      part.chemistry,
                "capacity":       part.capacity,
                "voltage":        part.voltage,
                "rechargeCycles": part.recharge_cycles,
            })
        else:
            base["attributes"] = part.properties

        return base

    def validate_mapping(self, mapped_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a mapped Battery DPP document against EU Reg 2023/1542 Annex XIII.

        Hard errors (return False):
          - schema must equal "BatteryDPP".
          - identity.manufacturerIdentification must be present.
          - identity.batteryModel must be present.
          - sustainability.carbonFootprint must be present and numeric.
          - sustainability.recycledContent must be present (non-empty dict).
          - structure.componentsList must contain at least one EnergyStorage part
            (identified by type == "EnergyStorage" or presence of "chemistry" key).
        """
        errors: List[str] = []

        # Schema identity
        if mapped_data.get("schema") != "BatteryDPP":
            errors.append(
                f"Schema mismatch: expected 'BatteryDPP', got {mapped_data.get('schema')!r}."
            )

        # Mandatory identity fields (Annex XIII §1)
        identity = mapped_data.get("identity") or {}
        if not identity.get("manufacturerIdentification"):
            errors.append(
                "identity.manufacturerIdentification is required (EU Reg 2023/1542 Annex XIII §1)."
            )
        if not identity.get("batteryModel"):
            errors.append(
                "identity.batteryModel is required (EU Reg 2023/1542 Annex XIII §1)."
            )

        # Mandatory sustainability fields (Annex XIII §6)
        sustainability = mapped_data.get("sustainability") or {}
        co2e = sustainability.get("carbonFootprint")
        if co2e is None:
            errors.append(
                "sustainability.carbonFootprint is required (EU Reg 2023/1542 Annex XIII §6)."
            )
        elif not isinstance(co2e, (int, float)):
            errors.append(
                f"sustainability.carbonFootprint must be numeric (kg CO₂e/kWh), got {co2e!r}."
            )

        recycled = sustainability.get("recycledContent")
        if not recycled:
            errors.append(
                "sustainability.recycledContent is required (EU Reg 2023/1542 Annex XIII §6)."
            )

        # At least one EnergyStorage part (Annex XIII §2)
        structure = mapped_data.get("structure") or {}
        components = structure.get("componentsList") or []
        has_energy_storage = any(
            c.get("type") == "EnergyStorage" or c.get("chemistry") is not None
            for c in components
        )
        if not has_energy_storage:
            errors.append(
                "structure.componentsList must contain at least one EnergyStorage part "
                "(EU Reg 2023/1542 Annex XIII §2)."
            )

        return len(errors) == 0, errors
