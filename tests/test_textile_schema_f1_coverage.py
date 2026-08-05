"""
test_textile_schema_f1_coverage.py

Measures TextileDPPMapper schema coverage using information-retrieval metrics
(precision, recall, F1) and semantic field-type precision, mirroring
test_schema_f1_coverage.py (BatteryDPPMapper) so results are directly
comparable across the two sector mappers and against the same literature
baselines cited in the paper:

    Literature baseline 1 — expert-curated industrial ontology:
        structural F1 = 0.83  (P = 1.00, R = 0.71)          [ml_ontology_2026]

    Literature baseline 2 — ML-driven ontology-quality framework:
        structural P = 93.5%, semantic P = 90.2%, F1 ~ 0.90  [ontology_quality_2026]

Target schema
-------------
open-dpp EU Textile DPP field schema v0.5.0
(tests/open-dpp-main/schemas/textile/schema.json), instantiating
Regulation (EU) 2024/1781 (ESPR). 18 fields across 10 sections, each tagged:
  - M1 (9 fields):  self-executing under ESPR today
  - M2 (7 fields):  Annex III basis, pending the textile delegated act
  - M3 (2 fields):  extended / lower-confidence, no direct ESPR mandate yet

Metric definitions
------------------
Unlike BatteryPass (whose SAMM aspect properties are flat scalars), every
open-dpp textile field is itself a nested object or array. The "vocabulary"
here is therefore the 18 top-level field names rather than flattened
sub-properties — testing whether the mapper emits the field at all (with
schema-shaped content), not whether it flattens every leaf property.

valid_vocabulary (V)   The 18 field names declared in TextileDPPMapper.get_context().
emitted fields (E)     Section-level keys in the mapper output carrying a non-null,
                       non-empty value (8 output sections).
required fields (R)    16 fields = M1 + M2 (the schema's own "practical minimum
                       for a compliant, useful DPP today"), each with a
                       coverage detector (see FIELD_CHECKS below).

structural_precision  = |E ∩ V| / |E|
structural_recall     = |{r ∈ R : mapper covers r}| / |R|
structural_f1         = harmonic_mean(structural_precision, structural_recall)
semantic_precision    = |{covered r : value passes type/shape validator}| / |covered R|

Run with:
    pytest -v -s tests/test_textile_schema_f1_coverage.py
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Set

import pytest

from nmis_dpp.mappers.textile_dpp_mapper import TextileDPPMapper
from nmis_dpp.model import (
    DigitalProductPassport,
    IdentityLayer,
    StructureLayer,
    LifecycleLayer,
    RiskLayer,
    SustainabilityLayer,
    ProvenanceLayer,
)


# =============================================================================
# Vocabulary and metric infrastructure
# =============================================================================

# All 18 field names declared in schemas/textile/schema.json v0.5.0, exactly
# as surfaced by TextileDPPMapper.get_context() under the textile: namespace.
ALL_TEXTILE_FIELDS: Set[str] = {
    # 1. Product identity
    "product_identifier", "user_manuals_and_safety_information",
    # 2. Actors
    "operator_identifiers", "manufacturer_contact_details",
    # 3. Material composition
    "fibre_composition", "recycled_content", "raw_material_origin",
    # 4. Supply chain
    "supply_chain",
    # 5. Environmental performance
    "carbon_footprint", "water_use",
    # 6. Substances
    "substances_of_concern", "restricted_substances_compliance",
    # 7. Circularity
    "durability", "repairability", "end_of_life",
    # 8. Compliance & certs
    "certifications",
    # 9. Lifecycle status
    "lifecycle_status",
    # 10. DPP metadata
    "dpp_metadata",
}

# M3 fields (extended, no direct ESPR mandate yet) — excluded from FIELD_CHECKS.
_M3_FIELDS: Set[str] = {"raw_material_origin", "certifications"}

_SECTIONS = [
    "identity", "structure", "lifecycle", "risk",
    "sustainability", "provenance", "circularity", "metadata",
]

_ISO_DATE_RE   = re.compile(r"^\d{4}-\d{2}-\d{2}")
_URL_RE        = re.compile(r"^https?://")
_COUNTRY_RE    = re.compile(r"^[A-Z]{2}$")

_STAGE_ENUM   = {
    "raw_material_processing", "spinning", "weaving_knitting",
    "dyeing_finishing", "cut_make_trim", "final_assembly", "other",
}
_ESPR_CAT_ENUM = {"substance_of_concern", "svhc", "hazardous_substance", "other"}
_STATUS_ENUM   = {
    "new", "repaired", "refurbished", "repurposed",
    "remanufactured", "second_hand", "end_of_life",
}
_OPERATOR_ROLE_ENUM = {
    "manufacturer", "importer", "authorised_representative",
    "eu_responsible_person", "dpp_service_provider",
}
_SCOPE_BOUNDARY_ENUM = {"cradle_to_gate", "cradle_to_grave", "cradle_to_retailer"}


def _is_pct(v: Any) -> bool:
    return isinstance(v, (int, float)) and 0.0 <= float(v) <= 100.0


# Semantic validators: output_key -> validator(value) -> bool
# Every value here is a dict or list (per the source schema's own field
# shapes), so validators check structural shape, not scalar format.
SEMANTIC_VALIDATORS: Dict[str, Callable[[Any], bool]] = {
    "product_identifier": lambda v: (
        isinstance(v, dict) and bool(v.get("id")) and _URL_RE.match(v["id"]) is not None
    ),
    "user_manuals_and_safety_information": lambda v: (
        isinstance(v, dict)
        and any(v.get(k) for k in ("care_instructions", "end_of_life_instructions"))
    ),
    "operator_identifiers": lambda v: (
        isinstance(v, list) and len(v) > 0
        and all(
            e.get("operator_role") in _OPERATOR_ROLE_ENUM
            and e.get("operator_name")
            and e.get("unique_operator_identifier")
            for e in v
        )
    ),
    "manufacturer_contact_details": lambda v: isinstance(v, dict) and bool(v.get("name")),
    "fibre_composition": lambda v: (
        isinstance(v, list) and len(v) > 0
        and all(e.get("fibre_type") and _is_pct(e.get("percentage")) for e in v)
    ),
    "recycled_content": lambda v: (
        isinstance(v, list) and len(v) > 0
        and all(e.get("material") and _is_pct(e.get("recycled_percentage")) for e in v)
    ),
    "supply_chain": lambda v: (
        isinstance(v, list) and len(v) > 0
        and all(
            e.get("stage") in _STAGE_ENUM
            and e.get("facility_name")
            and _COUNTRY_RE.match(e.get("country") or "")
            for e in v
        )
    ),
    "carbon_footprint": lambda v: (
        isinstance(v, dict) and isinstance(v.get("total_kgco2e"), (int, float))
        and v["total_kgco2e"] >= 0
    ),
    "water_use": lambda v: (
        isinstance(v, dict) and isinstance(v.get("total_litres"), (int, float))
        and v["total_litres"] >= 0
    ),
    "substances_of_concern": lambda v: (
        isinstance(v, list) and (
            len(v) == 0
            or all(e.get("substance_name") and e.get("espr_category") in _ESPR_CAT_ENUM for e in v)
        )
    ),
    "restricted_substances_compliance": lambda v: (
        isinstance(v, dict) and isinstance(v.get("reach_compliant"), bool)
    ),
    "durability": lambda v: (
        isinstance(v, dict)
        and any(v.get(k) for k in (
            "pilling_resistance", "colourfastness_washing",
            "colourfastness_rubbing", "expected_lifetime_washes",
        ))
    ),
    "repairability": lambda v: (
        isinstance(v, dict) and (
            (isinstance(v.get("repairability_score"), (int, float)) and 0 <= v["repairability_score"] <= 10)
            or isinstance(v.get("spare_parts_available"), bool)
        )
    ),
    "end_of_life": lambda v: (
        isinstance(v, dict) and (
            (isinstance(v.get("recyclability_rate"), (int, float)) and _is_pct(v["recyclability_rate"]))
            or bool(v.get("take_back_scheme_url"))
        )
    ),
    "lifecycle_status": lambda v: isinstance(v, dict) and v.get("status") in _STATUS_ENUM,
    "dpp_metadata": lambda v: isinstance(v, dict) and bool(v.get("schema_version")),
}


# =============================================================================
# Required field checks (16 fields = M1 + M2, per schema.json mandate_status)
# =============================================================================

@dataclass(frozen=True)
class FieldCheck:
    """One required open-dpp textile field with its coverage detector."""
    aspect: str
    name: str        # field_name from schema.json (== output_key here)
    output_key: str
    check_fn: Callable[[Dict[str, Any]], bool]

    def __str__(self) -> str:
        return f"{self.aspect}.{self.name}"


FIELD_CHECKS: List[FieldCheck] = [
    # ── 1. Product identity ───────────────────────────────────────────────
    FieldCheck("PI", "product_identifier", "product_identifier",
               lambda m: bool((m.get("identity", {}).get("product_identifier") or {}).get("id"))),
    FieldCheck("PI", "user_manuals_and_safety_information", "user_manuals_and_safety_information",
               lambda m: m.get("lifecycle", {}).get("user_manuals_and_safety_information") is not None),
    # ── 2. Actors ──────────────────────────────────────────────────────────
    FieldCheck("ACT", "operator_identifiers", "operator_identifiers",
               lambda m: bool(m.get("identity", {}).get("operator_identifiers"))),
    FieldCheck("ACT", "manufacturer_contact_details", "manufacturer_contact_details",
               lambda m: m.get("identity", {}).get("manufacturer_contact_details") is not None),
    # ── 3. Material composition ───────────────────────────────────────────
    FieldCheck("MC", "fibre_composition", "fibre_composition",
               lambda m: bool(m.get("structure", {}).get("fibre_composition"))),
    FieldCheck("MC", "recycled_content", "recycled_content",
               lambda m: bool(m.get("structure", {}).get("recycled_content"))),
    # ── 4. Supply chain ───────────────────────────────────────────────────
    FieldCheck("SC", "supply_chain", "supply_chain",
               lambda m: bool(m.get("lifecycle", {}).get("supply_chain"))),
    # ── 5. Environmental performance ──────────────────────────────────────
    FieldCheck("ENV", "carbon_footprint", "carbon_footprint",
               lambda m: (m.get("sustainability", {}).get("carbon_footprint") or {}).get("total_kgco2e") is not None),
    FieldCheck("ENV", "water_use", "water_use",
               lambda m: (m.get("sustainability", {}).get("water_use") or {}).get("total_litres") is not None),
    # ── 6. Substances ─────────────────────────────────────────────────────
    FieldCheck("SUB", "substances_of_concern", "substances_of_concern",
               lambda m: m.get("risk", {}).get("substances_of_concern") is not None),
    FieldCheck("SUB", "restricted_substances_compliance", "restricted_substances_compliance",
               lambda m: m.get("risk", {}).get("restricted_substances_compliance") is not None),
    # ── 7. Circularity ────────────────────────────────────────────────────
    FieldCheck("CIR", "durability", "durability",
               lambda m: bool(m.get("circularity", {}).get("durability"))),
    FieldCheck("CIR", "repairability", "repairability",
               lambda m: m.get("circularity", {}).get("repairability") is not None),
    FieldCheck("CIR", "end_of_life", "end_of_life",
               lambda m: m.get("circularity", {}).get("end_of_life") is not None),
    # ── 9. Lifecycle status ───────────────────────────────────────────────
    FieldCheck("LC", "lifecycle_status", "lifecycle_status",
               lambda m: m.get("lifecycle", {}).get("lifecycle_status") is not None),
    # ── 10. DPP metadata ──────────────────────────────────────────────────
    FieldCheck("META", "dpp_metadata", "dpp_metadata",
               lambda m: bool((m.get("metadata", {}).get("dpp_metadata") or {}).get("schema_version"))),
]

_FIELD_IDS = [str(fc) for fc in FIELD_CHECKS]


# =============================================================================
# Metric helpers
# =============================================================================

def collect_emitted_fields(mapped: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return {field_name: value} for every section-level key in the mapper
    output that carries a non-null, non-empty value.

    Unlike the battery mapper, no promotion step is needed: every field name
    here is already at the top level of its section dict.
    """
    result: Dict[str, Any] = {}
    for sec in _SECTIONS:
        sec_dict = mapped.get(sec) or {}
        for k, v in sec_dict.items():
            if v is not None and v != [] and v != {}:
                result[k] = v
    return result


def compute_metrics(mapped: Dict[str, Any]) -> Dict[str, Any]:
    """Compute all four coverage metrics for one mapper output."""
    emitted = collect_emitted_fields(mapped)
    emitted_keys = set(emitted.keys())

    valid_emitted    = emitted_keys & ALL_TEXTILE_FIELDS
    spurious_emitted = emitted_keys - ALL_TEXTILE_FIELDS
    struct_precision = len(valid_emitted) / len(emitted_keys) if emitted_keys else 0.0

    covered_checks = [fc for fc in FIELD_CHECKS if fc.check_fn(mapped)]
    missing_checks  = [fc for fc in FIELD_CHECKS if not fc.check_fn(mapped)]
    struct_recall   = len(covered_checks) / len(FIELD_CHECKS) if FIELD_CHECKS else 0.0

    denom = struct_precision + struct_recall
    struct_f1 = (2 * struct_precision * struct_recall / denom) if denom > 0 else 0.0

    semant_valid:   List[FieldCheck] = []
    semant_invalid: List[FieldCheck] = []

    for fc in covered_checks:
        validator = SEMANTIC_VALIDATORS.get(fc.output_key)
        value     = emitted.get(fc.output_key)

        if validator is None or value is None:
            semant_valid.append(fc)
        elif validator(value):
            semant_valid.append(fc)
        else:
            semant_invalid.append(fc)

    semant_precision = len(semant_valid) / len(covered_checks) if covered_checks else 0.0

    return {
        "structural_precision": struct_precision,
        "structural_recall":    struct_recall,
        "structural_f1":        struct_f1,
        "semantic_precision":   semant_precision,
        "emitted_keys":         emitted_keys,
        "valid_emitted":        valid_emitted,
        "spurious_emitted":     spurious_emitted,
        "covered_checks":       covered_checks,
        "missing_checks":       missing_checks,
        "semant_valid":         semant_valid,
        "semant_invalid":       semant_invalid,
    }


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def mapper():
    return TextileDPPMapper(config={})


@pytest.fixture(scope="module")
def minimal_textile_dpp():
    """Minimal DPP — only the fields validate_mapping() hard-requires."""
    return DigitalProductPassport(
        identity=IdentityLayer(
            global_ids={"gtin": "09506000134352"},
            make_model={"product_name": "Basic Tee"},
            ownership={"manufacturer": "EcoWear Ltd"},
            conformity=[],
        ),
        structure=StructureLayer(
            hierarchy={},
            parts=[],
            interfaces=[],
            materials=[{"fibre_type": "cotton", "percentage": 100.0}],
            bom_refs=[],
        ),
        lifecycle=LifecycleLayer(
            manufacture={},
            use={},
            serviceability={},
            events=[],
            end_of_life={},
        ),
        risk=RiskLayer(criticality={}, fmea=[], security={}),
        sustainability=SustainabilityLayer(
            mass=0.15, energy={}, recycled_content={}, remanufacture={},
        ),
        provenance=ProvenanceLayer(signatures=[], trace_links=[]),
    )


@pytest.fixture(scope="module")
def full_textile_dpp():
    """Maximally-populated DPP — all 18 open-dpp textile schema fields present."""
    return DigitalProductPassport(
        identity=IdentityLayer(
            global_ids={
                "gtin": "09506000134352",
                "batch": "B2025-04",
                "serial": "SN-000123",
                "dpp_level": "item",
            },
            make_model={
                "product_name": "Classic Organic Tee",
                "product_type": "T-shirt",
                "model_number": "TEE-CLASSIC-001",
            },
            ownership={
                "manufacturer":            "EcoWear Ltd",
                "manufacturer_gln":        "5410000000001",
                "postal_address":          "1 Mill Street, Glasgow, UK",
                "electronic_contact":      "compliance@ecowear.example",
                "complaints_channel_url":  "https://ecowear.example/complaints",
                "importer": {
                    "name":               "EcoWear EU Import BV",
                    "gln":                "5410000000002",
                    "postal_address":     "2 Havenweg, Rotterdam, NL",
                    "electronic_contact": "import@ecowear.example",
                    "eori_number":        "NL123456789",
                },
            },
            conformity=["CE"],
        ),
        structure=StructureLayer(
            hierarchy={"product": "Classic Organic Tee"},
            parts=[],
            interfaces=[],
            materials=[
                {
                    "fibre_type": "organic cotton", "percentage": 80.0,
                    "component": "shell", "is_recycled": False,
                    "material": "organic cotton",
                    "country_of_origin": "IN", "region": "Gujarat",
                    "farm_or_source_id": "FARM-2024-119",
                },
                {
                    "fibre_type": "recycled polyester", "percentage": 20.0,
                    "component": "shell", "is_recycled": True,
                    "material": "recycled polyester",
                    "recycled_percentage": 100.0, "recycled_source": "post_consumer",
                    "verification_standard": "GRS 4.0", "certificate_id": "GRS-2024-5567",
                    "country_of_origin": "PT",
                },
            ],
            bom_refs=[],
        ),
        lifecycle=LifecycleLayer(
            manufacture={
                "date": "2025-01-15",
                "factory": "EcoWear Plant 3",
                "supply_chain": [
                    {"stage": "raw_material_processing", "facility_name": "Gujarat Cotton Co-op",
                     "country": "IN", "tier": 4},
                    {"stage": "spinning", "facility_name": "Ahmedabad Spinning Mill",
                     "country": "IN", "tier": 3},
                    {"stage": "dyeing_finishing", "facility_name": "GreenDye Works",
                     "country": "PT", "tier": 2, "unique_facility_identifier": "5410000000010"},
                    {"stage": "final_assembly", "facility_name": "EcoWear Plant 3",
                     "country": "PT", "tier": 1, "unique_facility_identifier": "5410000000011"},
                ],
            },
            use={
                "status": "new",
                "status_date": "2025-01-20",
                "updated_by": "manufacturer",
            },
            serviceability={
                "care_instructions":         "Machine wash cold, do not bleach, tumble dry low.",
                "repair_instructions_url":   "https://ecowear.example/repair",
                "end_of_life_instructions":  "Return to any EcoWear store for recycling.",
                "language_codes":            ["en", "fr"],
                "accessible_until":          "2035-01-20",
                "durability": {
                    "pilling_resistance": {"score": 4, "test_method": "ISO 12945-2:2020", "test_cycles": 7000},
                    "colourfastness_washing": {"score": 4, "test_method": "ISO 105-C06:2010"},
                    "colourfastness_rubbing": {"dry_score": 4, "wet_score": 3, "test_method": "ISO 105-X12:2016"},
                    "expected_lifetime_washes": 50,
                },
                "repairability_score":     7.5,
                "spare_parts_available":   True,
                "spare_parts_url":         "https://ecowear.example/spares",
                "repair_network_url":      "https://ecowear.example/repair-network",
                "last_updated":            "2025-01-20",
                "updated_by":              "manufacturer",
            },
            events=[],
            end_of_life={
                "recyclability_rate":     85.0,
                "disassembly_instructions": "Remove zip and buttons before recycling.",
                "take_back_scheme_url":   "https://ecowear.example/takeback",
                "waste_sorting_code":     "TEX-01",
                "contains_non_recyclable_components": True,
                "non_recyclable_components_description": "Metal zip pull",
                "last_updated":           "2025-01-20",
                "updated_by":             "manufacturer",
            },
        ),
        risk=RiskLayer(
            criticality={},
            fmea=[{
                "substance": "Antimony trioxide",
                "cas_number": "1309-64-4",
                "ec_number": "215-175-0",
                "location_in_product": "polyester fibre",
                "concentration_ppm": 150.0,
                "espr_category": "substance_of_concern",
                "safe_use_instructions": "No special precautions for normal use.",
                "end_of_life_handling": "Standard textile recycling stream.",
            }],
            security={
                "reach_compliant":       True,
                "rsl_standard":          "ZDHC MRSL 3.1",
                "test_report_reference": "TR-2025-0042",
                "tested_by":             "Intertek",
                "test_date":             "2025-01-10",
            },
        ),
        sustainability=SustainabilityLayer(
            mass=0.18,
            energy={
                "total_kgco2e": 5.2,
                "calculation_methodology": "PEF Category Rules for Apparel and Footwear",
                "scope_boundary": "cradle_to_grave",
                "reference_year": 2025,
                "total_litres": 2700.0,
                "water_calculation_methodology": "ISO 14046:2014",
                "water_scope_boundary": "cradle_to_gate",
            },
            recycled_content={},
            remanufacture={},
        ),
        provenance=ProvenanceLayer(
            signatures=[{
                "standard_name":   "GOTS 7.0",
                "certificate_id":  "GOTS-2025-8891",
                "signed_by":       "Control Union Certifications",
                "valid_from":      "2025-01-01",
                "valid_until":     "2026-01-01",
                "scope":           "product",
                "certificate_url": "https://certificates.example/gots-2025-8891",
            }],
            trace_links=["epcis://batch/B2025-04"],
        ),
    )


@pytest.fixture(scope="module")
def mapped_full(mapper, full_textile_dpp):
    return mapper.map_dpp(full_textile_dpp)


@pytest.fixture(scope="module")
def mapped_minimal(mapper, minimal_textile_dpp):
    return mapper.map_dpp(minimal_textile_dpp)


@pytest.fixture(scope="module")
def metrics_full(mapped_full):
    return compute_metrics(mapped_full)


@pytest.fixture(scope="module")
def metrics_minimal(mapped_minimal):
    return compute_metrics(mapped_minimal)


# =============================================================================
# Vocabulary tests
# =============================================================================

def test_vocabulary_size_matches_context(mapper):
    """ALL_TEXTILE_FIELDS must contain exactly the field names from get_context()."""
    ctx = mapper.get_context()
    namespace_keys = {"@vocab", "textile", "schema", "gs1"}
    context_fields = {k for k in ctx if k not in namespace_keys}
    assert context_fields == ALL_TEXTILE_FIELDS, (
        f"Vocabulary mismatch.\n"
        f"  In ALL_TEXTILE_FIELDS but not context: {ALL_TEXTILE_FIELDS - context_fields}\n"
        f"  In context but not ALL_TEXTILE_FIELDS: {context_fields - ALL_TEXTILE_FIELDS}"
    )


def test_vocabulary_covers_all_required_field_output_keys():
    """Every required field's output_key must appear in the valid vocabulary."""
    missing = {fc.output_key for fc in FIELD_CHECKS} - ALL_TEXTILE_FIELDS
    assert not missing, f"Required field output keys not in vocabulary: {missing}"


def test_field_checks_exclude_m3_fields():
    """M3 fields (raw_material_origin, certifications) must not be in FIELD_CHECKS."""
    checked = {fc.name for fc in FIELD_CHECKS}
    assert not (checked & _M3_FIELDS), (
        f"M3 fields should not be required-field checks: {checked & _M3_FIELDS}"
    )
    assert len(FIELD_CHECKS) == len(ALL_TEXTILE_FIELDS) - len(_M3_FIELDS) == 16


# =============================================================================
# Structural precision tests
# =============================================================================

def test_structural_precision_full_dpp_beats_ml_baseline(metrics_full):
    """
    Structural precision on a fully-populated DPP should exceed the ML-driven
    ontology-quality baseline of 93.5% [ontology_quality_2026].
    """
    p = metrics_full["structural_precision"]
    assert p > 0.935, (
        f"Structural precision {p:.3f} does not beat ML baseline 0.935. "
        f"Spurious fields: {metrics_full['spurious_emitted']}"
    )


def test_no_spurious_fields_in_minimal_dpp(metrics_minimal):
    """
    Even with a sparsely-populated DPP the mapper must not emit field names
    outside the textile vocabulary (precision = 1.0 for emitted fields).
    """
    assert not metrics_minimal["spurious_emitted"], (
        f"Unexpected non-vocabulary fields emitted: {metrics_minimal['spurious_emitted']}"
    )


def test_no_spurious_fields_in_full_dpp(metrics_full):
    """The mapper must never emit a field name outside the textile vocabulary."""
    assert not metrics_full["spurious_emitted"], (
        f"Unexpected non-vocabulary fields emitted: {metrics_full['spurious_emitted']}"
    )


# =============================================================================
# Structural recall tests
# =============================================================================

def test_structural_recall_full_dpp_is_100_percent(metrics_full):
    """
    A maximally-populated DPP must achieve 100% recall (all 16 M1+M2 fields
    covered), exceeding the expert-ontology baseline of 71% [ml_ontology_2026].
    """
    r = metrics_full["structural_recall"]
    assert r == 1.0, (
        f"Recall {r:.3f} < 1.0. Missing: {[str(fc) for fc in metrics_full['missing_checks']]}"
    )


def test_structural_recall_minimal_dpp_covers_mandatory_core(metrics_minimal):
    """
    Even without optional fields the mapper must cover the fields
    validate_mapping() hard-requires: product_identifier, operator_identifiers,
    manufacturer_contact_details, fibre_composition, substances_of_concern
    (present-but-possibly-empty), and dpp_metadata (always mapper-generated).
    """
    covered_names = {fc.name for fc in metrics_minimal["covered_checks"]}
    mandatory_core = {
        "product_identifier", "operator_identifiers",
        "manufacturer_contact_details", "fibre_composition",
        "substances_of_concern", "dpp_metadata",
    }
    missing = mandatory_core - covered_names
    assert not missing, f"Mandatory core fields not covered: {missing}"


def test_structural_recall_full_beats_ontology_baseline(metrics_full):
    """Recall must exceed the expert ontology's 0.71 recall [ml_ontology_2026]."""
    assert metrics_full["structural_recall"] > 0.71


def test_structural_recall_minimal_dpp_lower_bound(metrics_minimal):
    """A minimal DPP should still cover at least 5 of the 16 required fields."""
    assert len(metrics_minimal["covered_checks"]) >= 5, (
        f"Minimal DPP covers only {len(metrics_minimal['covered_checks'])} required fields"
    )


# =============================================================================
# Structural F1 tests
# =============================================================================

def test_structural_f1_full_dpp_beats_ontology_baseline(metrics_full):
    """Structural F1 on a full DPP must exceed the expert-ontology baseline of 0.83."""
    f1 = metrics_full["structural_f1"]
    assert f1 > 0.83, f"Structural F1 {f1:.3f} does not beat ontology baseline 0.83."


def test_structural_f1_full_dpp_beats_ml_baseline(metrics_full):
    """Structural F1 must exceed the ML ontology-quality framework's ~0.90."""
    f1 = metrics_full["structural_f1"]
    assert f1 > 0.90, f"Structural F1 {f1:.3f} does not beat ML baseline ~0.90."


# =============================================================================
# Semantic precision tests (per-field type/shape validation)
# =============================================================================

def test_semantic_precision_full_dpp_beats_ml_baseline(metrics_full):
    """Semantic precision must exceed the ML ontology-quality framework's 90.2%."""
    sp = metrics_full["semantic_precision"]
    assert sp > 0.902, (
        f"Semantic precision {sp:.3f} does not beat ML baseline 0.902. "
        f"Failed fields: {[str(fc) for fc in metrics_full['semant_invalid']]}"
    )


@pytest.mark.parametrize("fc", FIELD_CHECKS, ids=_FIELD_IDS)
def test_semantic_field_type(mapped_full, fc):
    """Each covered required field must carry a value that passes its shape validator."""
    emitted = collect_emitted_fields(mapped_full)
    covered = fc.check_fn(mapped_full)
    if not covered:
        pytest.skip(f"{fc} not covered — semantic check skipped")

    validator = SEMANTIC_VALIDATORS.get(fc.output_key)
    if validator is None:
        return

    value = emitted.get(fc.output_key)
    if value is None:
        return

    assert validator(value), (
        f"{fc.aspect}.{fc.name}: value {value!r} failed semantic shape check "
        f"for output_key '{fc.output_key}'"
    )


# =============================================================================
# Summary report
# =============================================================================

def test_f1_coverage_report(metrics_full, metrics_minimal):
    """
    Print a comparison table of all four metrics against the literature
    baselines, alongside the BatteryDPPMapper results reported in
    test_schema_f1_coverage.py.

    Run with -v -s to see the full report:
        pytest -v -s tests/test_textile_schema_f1_coverage.py::test_f1_coverage_report
    """
    mf = metrics_full
    mm = metrics_minimal

    BASELINES = {
        "Expert ontology [ml_ontology_2026]":    {"P": 1.000, "R": 0.710, "F1": 0.830, "SemP": None},
        "ML framework [ontology_quality_2026]":  {"P": 0.935, "R": None,  "F1": 0.900, "SemP": 0.902},
    }

    sep  = "=" * 76
    sep2 = "-" * 76

    print(f"\n\n{sep}")
    print("  Schema Coverage Metrics — TextileDPPMapper vs Literature Baselines")
    print(f"{sep}")
    print(f"  {'System':<42}  {'Struct P':>8}  {'Recall':>7}  {'F1':>6}  {'Sem P':>6}")
    print(sep2)

    for label, b in BASELINES.items():
        p    = f"{b['P']:.3f}"    if b["P"]    is not None else "  N/A "
        r    = f"{b['R']:.3f}"    if b["R"]    is not None else "  N/A "
        f1   = f"{b['F1']:.3f}"   if b["F1"]   is not None else "  N/A "
        semp = f"{b['SemP']:.3f}" if b["SemP"] is not None else "  N/A "
        print(f"  {label:<42}  {p:>8}  {r:>7}  {f1:>6}  {semp:>6}")

    print(sep2)

    def _row(label, m):
        p    = f"{m['structural_precision']:.3f}"
        r    = f"{m['structural_recall']:.3f}"
        f1   = f"{m['structural_f1']:.3f}"
        semp = f"{m['semantic_precision']:.3f}"
        cov  = len(m['covered_checks'])
        tot  = len(FIELD_CHECKS)
        tag  = f"({cov}/{tot} fields)"
        print(f"  {label:<42}  {p:>8}  {r:>7}  {f1:>6}  {semp:>6}  {tag}")

    _row("This work — full DPP    (TextileDPPMapper)", mf)
    _row("This work — minimal DPP (ESPR M1 core only)", mm)
    print(sep2)

    aspect_total: Dict[str, int] = {}
    aspect_cov:   Dict[str, int] = {}
    for fc in FIELD_CHECKS:
        aspect_total[fc.aspect] = aspect_total.get(fc.aspect, 0) + 1
    for fc in mf["covered_checks"]:
        aspect_cov[fc.aspect] = aspect_cov.get(fc.aspect, 0) + 1

    print("\n  Per-aspect recall (full DPP):")
    for asp in aspect_total:
        c   = aspect_cov.get(asp, 0)
        t   = aspect_total[asp]
        pct = c / t * 100
        bar = "#" * c + "-" * (t - c)
        print(f"    {asp:<6}  [{bar:<11}]  {pct:5.1f}%  ({c}/{t})")

    if mf["spurious_emitted"]:
        print(f"\n  Spurious (non-vocabulary) emitted keys: {sorted(mf['spurious_emitted'])}")
    if mf["semant_invalid"]:
        print(f"\n  Semantic failures: {[str(fc) for fc in mf['semant_invalid']]}")

    print(f"\n{sep}\n")

    assert mf["structural_f1"] > 0.83, "Full-DPP F1 must exceed expert-ontology baseline (0.83)"
    assert mf["structural_f1"] > 0.90, "Full-DPP F1 must exceed ML-framework baseline (~0.90)"
    assert mf["semantic_precision"] > 0.902, "Semantic precision must exceed ML baseline (90.2%)"
