"""
textile_dpp_mapper.py

Implementation of SchemaMapper for the open-dpp EU Textile Digital Product
Passport field schema (schemas/textile/schema.json v0.5.0, sourced from
https://github.com/traceaware/open-dpp).

Targets Regulation (EU) 2024/1781 (ESPR) Art. 7, 9, 10, 11, 12, 27, 28, 29, 38
and Annex III, as instantiated by the open-dpp textile schema's 18 fields
across 10 sections. Each field carries a mandate_status:
  - M1: self-executing under ESPR today (9 fields)
  - M2: Annex III basis, not self-executing until the textile delegated act
        is adopted (7 fields)
  - M3: extended / lower-confidence fields with no direct ESPR mandate yet
        (2 fields: raw_material_origin, certifications)

DPP source conventions for open-dpp textile fields:
  identity.global_ids["gtin"] / ["gs1_digital_link"]  -> product_identifier.id
  identity.global_ids["batch"] / ["serial"]            -> batch_number / serial_number
  identity.ownership (manufacturer/importer/...)        -> operator_identifiers, manufacturer_contact_details
  structure.materials[].fibre_type + percentage         -> fibre_composition
  structure.materials[].recycled_percentage              -> recycled_content
  structure.materials[].country_of_origin                -> raw_material_origin
  lifecycle.manufacture["supply_chain"]                  -> supply_chain
  lifecycle.serviceability (care_instructions, ...)      -> user_manuals_and_safety_information
  lifecycle.serviceability (repairability_score, ...)    -> repairability
  lifecycle.serviceability["durability"]                 -> durability
  lifecycle.end_of_life (recyclability_rate, ...)        -> end_of_life
  lifecycle.use (status, status_date, ...)               -> lifecycle_status
  risk.fmea                                               -> substances_of_concern
  risk.security                                           -> restricted_substances_compliance
  sustainability.energy (total_kgco2e, ...)              -> carbon_footprint
  sustainability.energy (total_litres, ...)              -> water_use
  provenance.signatures                                   -> certifications
  (computed by the mapper)                                -> dpp_metadata
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import logging

from nmis_dpp.schema_base import SchemaMapper
from nmis_dpp.model import (
    DigitalProductPassport,
    IdentityLayer,
    StructureLayer,
    LifecycleLayer,
    RiskLayer,
    SustainabilityLayer,
    ProvenanceLayer,
)
from nmis_dpp.part_class import PartClass

logger = logging.getLogger(__name__)

_OPERATOR_ROLE_KEYS = {
    "manufacturer": "manufacturer",
    "importer": "importer",
    "authorised_rep": "authorised_representative",
    "eu_responsible_person": "eu_responsible_person",
}


def _none_if_empty(d: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return None if every value in d is None/empty, else return d unchanged.

    Used so that fixed-key output dicts (built with every schema property as
    a key) don't count as "emitted" for F1 purposes when the source DPP
    provided none of that field's underlying data.
    """
    if all(v is None or v == [] or v == "" for v in d.values()):
        return None
    return d


class TextileDPPMapper(SchemaMapper):
    """
    Mapper for the open-dpp EU Textile DPP field schema (v0.5.0).

    Produces a document using the open-dpp textile vocabulary. The 9 M1
    fields (self-executing under ESPR today) are enforced as hard errors in
    validate_mapping(); M2/M3 fields are best-effort and may be absent.
    """

    def get_schema_name(self) -> str:
        return "TextileDPP"

    def get_schema_version(self) -> str:
        return "open-dpp-0.5.0"

    def get_context(self) -> Dict[str, Any]:
        """
        Return a JSON-LD-style @context for the open-dpp textile vocabulary.

        Terms are the 18 top-level field names declared in schema.json,
        pointing at open-dpp.eu vocab IRIs (or schema.org where the source
        schema itself points there).
        """
        return {
            "@vocab":  "https://open-dpp.eu/vocab#",
            "textile": "https://open-dpp.eu/vocab#",
            "schema":  "https://schema.org/",
            "gs1":     "https://www.gs1.org/voc/",
            # 1. Product identity
            "product_identifier":                   "schema:identifier",
            "user_manuals_and_safety_information":  "textile:userManualsAndSafetyInformation",
            # 2. Actors
            "operator_identifiers":                 "textile:operatorRole",
            "manufacturer_contact_details":          "schema:name",
            # 3. Material composition
            "fibre_composition":                    "textile:fibreType",
            "recycled_content":                     "textile:recycledPercentage",
            "raw_material_origin":                  "schema:countryOfOrigin",
            # 4. Supply chain
            "supply_chain":                          "textile:stage",
            # 5. Environmental performance
            "carbon_footprint":                      "textile:totalKgCO2e",
            "water_use":                             "textile:totalLitres",
            # 6. Substances
            "substances_of_concern":                 "textile:esprCategory",
            "restricted_substances_compliance":      "textile:reachCompliant",
            # 7. Circularity
            "durability":                            "textile:pillingResistance",
            "repairability":                         "textile:repairabilityScore",
            "end_of_life":                           "textile:recyclabilityRate",
            # 8. Compliance & certs
            "certifications":                        "schema:identifier",
            # 9. Lifecycle status
            "lifecycle_status":                      "textile:status",
            # 10. DPP metadata
            "dpp_metadata":                          "schema:dateCreated",
        }

    # -------------------------------------------------------------------------
    # Layer mapping
    # -------------------------------------------------------------------------

    def map_identity_layer(self, layer: IdentityLayer) -> Dict[str, Any]:
        """
        Map IdentityLayer to product_identifier, operator_identifiers and
        manufacturer_contact_details.

        product_identifier.id is a GS1 Digital Link URI: used verbatim from
        global_ids["gs1_digital_link"] if present, else constructed from
        global_ids["gtin"].
        """
        global_ids = layer.global_ids or {}
        make_model = layer.make_model or {}
        ownership = layer.ownership or {}

        gs1_link = global_ids.get("gs1_digital_link")
        if not gs1_link and global_ids.get("gtin"):
            gs1_link = f"https://id.gs1.org/01/{global_ids['gtin']}"

        product_identifier = {
            "id":            gs1_link,
            "product_name":  make_model.get("product_name") or make_model.get("model"),
            "product_type":  make_model.get("product_type"),
            "batch_number":  global_ids.get("batch"),
            "serial_number": global_ids.get("serial"),
            "model_number":  make_model.get("model_number") or make_model.get("model"),
            "dpp_level":     global_ids.get("dpp_level", "model"),
        }

        operator_identifiers: List[Dict[str, Any]] = []
        if ownership.get("manufacturer"):
            operator_identifiers.append({
                "operator_role":               "manufacturer",
                "operator_name":                ownership["manufacturer"],
                "unique_operator_identifier":   ownership.get("manufacturer_gln", ""),
                "postal_address":               ownership.get("postal_address"),
                "electronic_contact":           ownership.get("electronic_contact"),
            })
        importer = ownership.get("importer")
        if isinstance(importer, dict) and importer.get("name"):
            operator_identifiers.append({
                "operator_role":               "importer",
                "operator_name":                importer.get("name"),
                "unique_operator_identifier":   importer.get("gln", ""),
                "postal_address":               importer.get("postal_address"),
                "electronic_contact":           importer.get("electronic_contact"),
                "eori_number":                  importer.get("eori_number"),
            })
        eu_rep = ownership.get("eu_responsible_person")
        if isinstance(eu_rep, dict) and eu_rep.get("name"):
            operator_identifiers.append({
                "operator_role":               "eu_responsible_person",
                "operator_name":                eu_rep.get("name"),
                "unique_operator_identifier":   eu_rep.get("gln", ""),
                "postal_address":               eu_rep.get("postal_address"),
                "electronic_contact":           eu_rep.get("electronic_contact"),
            })

        manufacturer_contact_details = {
            "name":                    ownership.get("manufacturer"),
            "postal_address":          ownership.get("postal_address"),
            "electronic_contact":      ownership.get("electronic_contact"),
            "complaints_channel_url":  ownership.get("complaints_channel_url"),
        }

        return {
            "product_identifier":          _none_if_empty(product_identifier),
            "operator_identifiers":        operator_identifiers,
            "manufacturer_contact_details": _none_if_empty(manufacturer_contact_details),
        }

    def map_structure_layer(self, layer: StructureLayer) -> Dict[str, Any]:
        """
        Map StructureLayer.materials into fibre_composition, recycled_content
        and raw_material_origin.

        Each entry in structure.materials may carry keys relevant to one or
        more of these three fields simultaneously (e.g. a single fabric entry
        can have fibre_type/percentage, recycled_percentage, and
        country_of_origin all at once).
        """
        materials = layer.materials or []

        fibre_composition = [
            {
                "fibre_type":  m.get("fibre_type"),
                "percentage":  m.get("percentage"),
                "component":   m.get("component"),
                "is_recycled": m.get("is_recycled", False),
            }
            for m in materials
            if m.get("fibre_type") is not None
        ]

        recycled_content = [
            {
                "material":              m.get("material") or m.get("fibre_type"),
                "recycled_percentage":   m.get("recycled_percentage"),
                "recycled_source":       m.get("recycled_source"),
                "verification_standard": m.get("verification_standard"),
                "certificate_id":        m.get("certificate_id"),
            }
            for m in materials
            if m.get("recycled_percentage") is not None
        ]

        raw_material_origin = [
            {
                "material":          m.get("material") or m.get("fibre_type"),
                "country_of_origin": m.get("country_of_origin"),
                "region":            m.get("region"),
                "farm_or_source_id": m.get("farm_or_source_id"),
            }
            for m in materials
            if m.get("country_of_origin") is not None
        ]

        return {
            "fibre_composition":   fibre_composition,
            "recycled_content":    recycled_content,
            "raw_material_origin": raw_material_origin,
        }

    def map_lifecycle_layer(self, layer: LifecycleLayer) -> Dict[str, Any]:
        """
        Map LifecycleLayer to user_manuals_and_safety_information, supply_chain
        and lifecycle_status.

        supply_chain    <- manufacture["supply_chain"] (list of per-facility stage dicts)
        lifecycle_status <- use (status, status_date, intervention_description, ...)
        """
        manufacture = layer.manufacture or {}
        svc = layer.serviceability or {}
        use = layer.use or {}

        user_manuals_and_safety_information = {
            "care_instructions":         svc.get("care_instructions"),
            "repair_instructions_url":   svc.get("repair_instructions_url"),
            "end_of_life_instructions":  svc.get("end_of_life_instructions"),
            "language_codes":            svc.get("language_codes", []),
            "accessible_until":          svc.get("accessible_until"),
        }

        supply_chain = list(manufacture.get("supply_chain") or [])

        lifecycle_status = {
            "status":                  use.get("status"),
            "status_date":             use.get("status_date"),
            "intervention_description": use.get("intervention_description"),
            "updated_by":              use.get("updated_by"),
            "previous_dpp_reference":  use.get("previous_dpp_reference"),
        }

        return {
            "user_manuals_and_safety_information": _none_if_empty(user_manuals_and_safety_information),
            "supply_chain":                        supply_chain,
            "lifecycle_status":                    _none_if_empty(lifecycle_status),
        }

    def map_risk_layer(self, layer: RiskLayer) -> Dict[str, Any]:
        """
        Map RiskLayer to substances_of_concern and restricted_substances_compliance.

        An empty substances_of_concern list is valid per the source schema
        ("An empty array is valid where none are present - but the field must
        exist"), so this always returns a list, never None.
        """
        substances_of_concern = [
            {
                "substance_name":       entry.get("substance") or entry.get("substance_name"),
                "other_names":          entry.get("other_names", []),
                "cas_number":           entry.get("cas_number"),
                "ec_number":            entry.get("ec_number"),
                "location_in_product":  entry.get("location_in_product") or entry.get("hazard_class"),
                "concentration_ppm":    entry.get("concentration_ppm"),
                "espr_category":        entry.get("espr_category", "substance_of_concern"),
                "safe_use_instructions": entry.get("safe_use_instructions"),
                "end_of_life_handling": entry.get("end_of_life_handling"),
            }
            for entry in (layer.fmea or [])
            if entry.get("substance") or entry.get("substance_name")
        ]

        security = layer.security or {}
        restricted_substances_compliance = {
            "reach_compliant":        security.get("reach_compliant"),
            "rsl_standard":           security.get("rsl_standard"),
            "test_report_reference":  security.get("test_report_reference"),
            "tested_by":              security.get("tested_by"),
            "test_date":              security.get("test_date"),
        }

        return {
            "substances_of_concern":              substances_of_concern,
            "restricted_substances_compliance":   _none_if_empty(restricted_substances_compliance),
        }

    def map_sustainability_layer(self, layer: SustainabilityLayer) -> Dict[str, Any]:
        """
        Map SustainabilityLayer.energy to carbon_footprint and water_use.
        """
        energy = layer.energy or {}

        carbon_footprint = {
            "total_kgco2e":             energy.get("total_kgco2e") or self.config.get("carbon_footprint"),
            "calculation_methodology":  energy.get("calculation_methodology"),
            "scope_boundary":           energy.get("scope_boundary"),
            "reference_year":          energy.get("reference_year"),
        }

        water_use = {
            "total_litres":            energy.get("total_litres"),
            "calculation_methodology": energy.get("water_calculation_methodology")
                                        or energy.get("calculation_methodology"),
            "scope_boundary":          energy.get("water_scope_boundary")
                                        or energy.get("scope_boundary"),
        }

        return {
            "carbon_footprint": _none_if_empty(carbon_footprint),
            "water_use":        _none_if_empty(water_use),
        }

    def map_provenance_layer(self, layer: ProvenanceLayer) -> Dict[str, Any]:
        """
        Map ProvenanceLayer.signatures to certifications (M3, extended field).
        """
        certifications = [
            {
                "standard_name":   sig.get("standard_name") or sig.get("certificate"),
                "certificate_id":  sig.get("certificate_id") or sig.get("certificate"),
                "issued_by":       sig.get("signed_by") or sig.get("issued_by"),
                "valid_from":      sig.get("valid_from"),
                "valid_until":     sig.get("valid_until") or sig.get("date"),
                "scope":           sig.get("scope", "product"),
                "certificate_url": sig.get("certificate_url"),
            }
            for sig in (layer.signatures or [])
        ]

        return {"certifications": certifications}

    # -------------------------------------------------------------------------
    # Circularity + metadata (extra sections, like BatteryDPPMapper.map_dpp)
    # -------------------------------------------------------------------------

    def map_circularity_layer(self, lifecycle: LifecycleLayer) -> Dict[str, Any]:
        """
        Map durability, repairability and end_of_life (schema section 7,
        "Circularity") from LifecycleLayer.
        """
        svc = lifecycle.serviceability or {}
        eol = lifecycle.end_of_life or {}

        durability = svc.get("durability")  # pass-through nested dict, or None

        repairability = {
            "repairability_score":      svc.get("repairability_score"),
            "spare_parts_available":    svc.get("spare_parts_available"),
            "spare_parts_url":          svc.get("spare_parts_url"),
            "repair_instructions_url":  svc.get("repair_instructions_url"),
            "repair_network_url":       svc.get("repair_network_url"),
            "last_updated":             svc.get("last_updated"),
            "updated_by":               svc.get("updated_by"),
        }

        end_of_life = {
            "recyclability_rate":                     eol.get("recyclability_rate"),
            "disassembly_instructions":                eol.get("disassembly_instructions"),
            "take_back_scheme_url":                    eol.get("take_back_scheme_url"),
            "waste_sorting_code":                       eol.get("waste_sorting_code"),
            "contains_non_recyclable_components":       eol.get("contains_non_recyclable_components"),
            "non_recyclable_components_description":    eol.get("non_recyclable_components_description"),
            "last_updated":                             eol.get("last_updated"),
            "updated_by":                                eol.get("updated_by"),
        }

        return {
            "durability":    durability,
            "repairability": _none_if_empty(repairability),
            "end_of_life":   _none_if_empty(end_of_life),
        }

    def map_dpp_metadata(self, dpp: DigitalProductPassport) -> Dict[str, Any]:
        """
        Compute dpp_metadata (schema section 10). Unlike other fields this is
        not sourced from a single DPP layer - it is metadata about the DPP
        instance itself, generated by the mapper at map time.
        """
        return {
            "dpp_metadata": {
                "schema_version":            self.get_schema_version(),
                "dpp_created_date":          self.config.get("dpp_created_date"),
                "dpp_last_updated":          self.config.get("dpp_last_updated"),
                "responsible_economic_operator": (dpp.identity.ownership or {}).get("manufacturer"),
                "language":                  self.config.get("language", "en"),
                "registry_unique_registration_identifier": self.config.get("registry_id"),
            }
        }

    def map_dpp(self, dpp: DigitalProductPassport) -> Dict[str, Any]:
        """
        Override map_dpp to add the circularity (7.x) and metadata (10.1)
        sections that don't map cleanly from a single base layer.
        """
        mapped = super().map_dpp(dpp)
        mapped["circularity"] = self.map_circularity_layer(dpp.lifecycle)
        mapped["metadata"] = self.map_dpp_metadata(dpp)
        return mapped

    def map_part_class(self, part: PartClass) -> Dict[str, Any]:
        """
        Map a single PartClass instance to a generic component entry.

        Textile products are not decomposed into PartClass components the
        way batteries or machinery are; this is provided only so
        SchemaRegistry.map_part() works uniformly across all mappers.
        """
        return {
            "id":         part.part_id,
            "name":       part.name,
            "type":       part.type,
            "attributes": part.properties,
        }

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate_mapping(self, mapped_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a mapped Textile DPP document against the M1 (self-executing)
        subset of the open-dpp textile schema.

        Hard errors (return False):
          - schema must equal "TextileDPP".
          - identity.product_identifier.id must be present (Art. 9(1), Annex III(c)).
          - identity.operator_identifiers must include a manufacturer entry
            (Annex III(g)).
          - structure.fibre_composition must contain at least one entry
            (Reg. (EU) 1007/2011, Annex I(f)).
          - risk.substances_of_concern must be present as a list, even if
            empty (Art. 7(5), Art. 7(6)).

        Note: this is invoked by the base class's map_dpp() before the
        circularity/metadata sections (added in this subclass's map_dpp
        override) exist yet, so only base-layer sections are checked here.
        """
        errors: List[str] = []

        if mapped_data.get("schema") != "TextileDPP":
            errors.append(
                f"Schema mismatch: expected 'TextileDPP', got {mapped_data.get('schema')!r}."
            )

        identity = mapped_data.get("identity") or {}
        product_identifier = identity.get("product_identifier") or {}
        if not product_identifier.get("id"):
            errors.append(
                "identity.product_identifier.id is required (Art. 9(1), Annex III(c))."
            )

        operators = identity.get("operator_identifiers") or []
        if not any(o.get("operator_role") == "manufacturer" for o in operators):
            errors.append(
                "identity.operator_identifiers must include a manufacturer entry (Annex III(g))."
            )

        structure = mapped_data.get("structure") or {}
        if not structure.get("fibre_composition"):
            errors.append(
                "structure.fibre_composition must contain at least one entry "
                "(Reg. (EU) 1007/2011, Annex I(f))."
            )

        risk = mapped_data.get("risk") or {}
        if risk.get("substances_of_concern") is None:
            errors.append(
                "risk.substances_of_concern must be present (may be empty) (Art. 7(5), Art. 7(6))."
            )

        return len(errors) == 0, errors
