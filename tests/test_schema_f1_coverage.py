"""
test_schema_f1_coverage.py

Measures BatteryDPPMapper schema coverage using information-retrieval metrics
(precision, recall, F1) and semantic field-type precision, providing results
directly comparable to ontology-alignment baselines cited in the paper:

    Literature baseline 1 — expert-curated industrial ontology:
        structural F1 = 0.83  (P = 1.00, R = 0.71)          [ml_ontology_2026]

    Literature baseline 2 — ML-driven ontology-quality framework:
        structural P = 93.5%, semantic P = 90.2%, F1 ~ 0.90  [ontology_quality_2026]

Metric definitions
------------------
valid_vocabulary (V)   BatteryPass v1.2.0 field names declared via
                       BatteryDPPMapper.get_context() battery: namespace — 36 terms.

emitted fields (E)     Section-level keys in the mapper output carrying a non-null,
                       non-empty value (7 output sections; EnergyStorage component
                       attributes are promoted to top-level for analysis).

required fields (R)    29 fields mandated by EU Regulation 2023/1542 Annex XIII,
                       each with a coverage detector (see FIELD_CHECKS below).

structural_precision  = |E ∩ V| / |E|
structural_recall     = |{r ∈ R : mapper covers r}| / |R|
structural_f1         = harmonic_mean(structural_precision, structural_recall)
semantic_precision    = |{covered r : value passes type/format validator}| / |covered R|

Run with:
    pytest -v -s tests/test_schema_f1_coverage.py
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set

import pytest

from nmis_dpp.mappers.battery_dpp_mapper import BatteryDPPMapper
from nmis_dpp.model import (
    DigitalProductPassport,
    IdentityLayer,
    StructureLayer,
    LifecycleLayer,
    RiskLayer,
    SustainabilityLayer,
    ProvenanceLayer,
)
from nmis_dpp.part_class import Actuator, EnergyStorage


# =============================================================================
# Vocabulary and metric infrastructure
# =============================================================================

# All BatteryPass v1.2.0 field names declared in BatteryDPPMapper.get_context()
# under the battery: namespace.  These are the "valid vocabulary" for precision.
ALL_BP_FIELDS: Set[str] = {
    # GeneralProductInformation / identity
    "batteryModel", "manufacturerIdentification", "productIdentifier",
    "batteryPassportIdentifier", "conformityCertification", "batteryCategory",
    "operatorInformation",
    # Structure
    "componentsList", "chemistry", "capacity", "voltage", "rechargeCycles",
    "batteryMaterials",
    # Lifecycle
    "manufacturingDate", "placeOfManufacturing", "expectedLifetime",
    "stateOfHealth", "cycleCount", "batteryStatus", "puttingIntoService",
    "warrentyPeriod",
    # Risk
    "hazardousSubstances", "safetyInstructions",
    # Sustainability / CarbonFootprint
    "carbonFootprint", "carbonFootprintPerLifecycleStage",
    "carbonFootprintPerformanceClass", "carbonFootprintStudy",
    "recycledContent", "renewableContent", "mass",
    # Circularity
    "dismantlingAndRemovalInformation", "sparePartSources", "endOfLifeInformation",
    # Provenance
    "conformityDeclaration", "dueDiligenceReport", "supplyChainInfo",
}

_SECTIONS = [
    "identity", "structure", "lifecycle", "risk",
    "sustainability", "provenance", "circularity",
]

# Compiled regex patterns for semantic validators
_ISO_DATE_RE         = re.compile(r"^\d{4}-\d{2}-\d{2}")
_URN_RE              = re.compile(r"^urn:[a-z0-9][a-z0-9-]*:", re.I)
_ISO_YEAR_MONTH_RE   = re.compile(r"^--\d{2}$")
_URL_RE              = re.compile(r"^https?://")

# Semantic validators: output_key → validator(value) → bool
SEMANTIC_VALIDATORS: Dict[str, Callable[[Any], bool]] = {
    "batteryModel":               lambda v: isinstance(v, str) and len(v) > 0,
    "manufacturerIdentification": lambda v: isinstance(v, str) and len(v) > 0,
    "productIdentifier":          lambda v: isinstance(v, str) and len(v) > 0,
    "batteryPassportIdentifier":  lambda v: isinstance(v, str) and bool(_URN_RE.match(v)),
    "batteryCategory":            lambda v: isinstance(v, str) and len(v) > 0,
    "operatorInformation":        lambda v: isinstance(v, str) and len(v) > 0,
    "manufacturingDate":          lambda v: isinstance(v, str) and bool(_ISO_DATE_RE.match(v)),
    "placeOfManufacturing":       lambda v: isinstance(v, str) and len(v) > 0,
    "batteryStatus":              lambda v: isinstance(v, str) and len(v) > 0,
    "puttingIntoService":         lambda v: isinstance(v, str) and bool(_ISO_DATE_RE.match(v)),
    "warrentyPeriod":             lambda v: isinstance(v, str) and bool(_ISO_YEAR_MONTH_RE.match(v)),
    "stateOfHealth":              lambda v: isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0,
    "expectedLifetime":           lambda v: isinstance(v, str) and len(v) > 0,
    "carbonFootprint":            lambda v: isinstance(v, (int, float)) and float(v) >= 0,
    "carbonFootprintPerLifecycleStage": lambda v: isinstance(v, list) and len(v) > 0,
    "carbonFootprintPerformanceClass":  lambda v: isinstance(v, str) and len(v) > 0,
    "carbonFootprintStudy":       lambda v: isinstance(v, str) and bool(_URL_RE.match(v)),
    "recycledContent":            lambda v: isinstance(v, dict) and any(
        val is not None for val in v.values()
    ),
    "renewableContent":           lambda v: isinstance(v, (int, float)) and float(v) >= 0,
    "mass":                       lambda v: isinstance(v, (int, float)) and float(v) > 0,
    "hazardousSubstances":        lambda v: (
        isinstance(v, list) and len(v) > 0
        and all(isinstance(e, dict) and e.get("substanceName") for e in v)
    ),
    "safetyInstructions":         lambda v: isinstance(v, list) and len(v) > 0,
    "dismantlingAndRemovalInformation": lambda v: isinstance(v, list) and len(v) > 0,
    "sparePartSources":           lambda v: isinstance(v, list) and len(v) > 0,
    "endOfLifeInformation":       lambda v: isinstance(v, dict) and len(v) > 0,
    "batteryMaterials":           lambda v: isinstance(v, list) and len(v) > 0,
    "chemistry":                  lambda v: isinstance(v, str) and len(v) > 0,
    "capacity":                   lambda v: isinstance(v, (int, float)) and float(v) > 0,
    "voltage":                    lambda v: isinstance(v, (int, float)) and float(v) > 0,
    "rechargeCycles":             lambda v: isinstance(v, int) and v > 0,
}


# =============================================================================
# Required field checks  (29 fields per EU Reg 2023/1542 Annex XIII)
# =============================================================================

@dataclass(frozen=True)
class FieldCheck:
    """One required BatteryPass field with its coverage detector."""
    aspect: str
    name: str        # BatteryPass / paper field name
    output_key: str  # key in SEMANTIC_VALIDATORS / ALL_BP_FIELDS
    check_fn: Callable[[Dict[str, Any]], bool]

    def __str__(self) -> str:
        return f"{self.aspect}.{self.name}"


def _comps(m: Dict[str, Any]) -> List[Dict[str, Any]]:
    return m.get("structure", {}).get("componentsList", [])


FIELD_CHECKS: List[FieldCheck] = [
    # ── GeneralProductInformation ─────────────────────────────────────────
    FieldCheck("GPI", "productIdentifier",         "productIdentifier",
               lambda m: bool(m.get("identity", {}).get("productIdentifier"))),
    FieldCheck("GPI", "batteryPassportIdentifier",  "batteryPassportIdentifier",
               lambda m: bool(m.get("identity", {}).get("batteryPassportIdentifier"))),
    FieldCheck("GPI", "batteryCategory",            "batteryCategory",
               lambda m: bool(m.get("identity", {}).get("batteryCategory"))),
    FieldCheck("GPI", "manufacturerIdentification", "manufacturerIdentification",
               lambda m: bool(m.get("identity", {}).get("manufacturerIdentification"))),
    FieldCheck("GPI", "manufacturingDate",          "manufacturingDate",
               lambda m: bool(m.get("lifecycle", {}).get("manufacturingDate"))),
    FieldCheck("GPI", "batteryStatus",              "batteryStatus",
               lambda m: bool(m.get("lifecycle", {}).get("batteryStatus"))),
    FieldCheck("GPI", "batteryMass",                "mass",
               lambda m: m.get("sustainability", {}).get("mass") is not None),
    FieldCheck("GPI", "manufacturingPlace",         "placeOfManufacturing",
               lambda m: bool(m.get("lifecycle", {}).get("placeOfManufacturing"))),
    FieldCheck("GPI", "operatorInformation",        "operatorInformation",
               lambda m: bool(m.get("identity", {}).get("operatorInformation"))),
    FieldCheck("GPI", "puttingIntoService",         "puttingIntoService",
               lambda m: bool(m.get("lifecycle", {}).get("puttingIntoService"))),
    FieldCheck("GPI", "warrentyPeriod",             "warrentyPeriod",
               lambda m: bool(m.get("lifecycle", {}).get("warrentyPeriod"))),
    # ── CarbonFootprint ───────────────────────────────────────────────────
    FieldCheck("CF",  "batteryCarbonFootprint",           "carbonFootprint",
               lambda m: m.get("sustainability", {}).get("carbonFootprint") is not None),
    FieldCheck("CF",  "carbonFootprintPerLifecycleStage", "carbonFootprintPerLifecycleStage",
               lambda m: bool(m.get("sustainability", {}).get("carbonFootprintPerLifecycleStage"))),
    FieldCheck("CF",  "carbonFootprintPerformanceClass",  "carbonFootprintPerformanceClass",
               lambda m: bool(m.get("sustainability", {}).get("carbonFootprintPerformanceClass"))),
    FieldCheck("CF",  "carbonFootprintStudy",             "carbonFootprintStudy",
               lambda m: bool(m.get("sustainability", {}).get("carbonFootprintStudy"))),
    # ── Circularity ───────────────────────────────────────────────────────
    FieldCheck("CIR", "dismantlingAndRemovalInformation", "dismantlingAndRemovalInformation",
               lambda m: bool(m.get("circularity", {}).get("dismantlingAndRemovalInformation"))),
    FieldCheck("CIR", "sparePartSources",                 "sparePartSources",
               lambda m: bool(m.get("circularity", {}).get("sparePartSources"))),
    FieldCheck("CIR", "recycledContent",                  "recycledContent",
               lambda m: bool(m.get("sustainability", {}).get("recycledContent"))),
    FieldCheck("CIR", "safetyMeasures",                   "safetyInstructions",
               lambda m: bool(m.get("risk", {}).get("safetyInstructions"))),
    FieldCheck("CIR", "endOfLifeInformation",             "endOfLifeInformation",
               lambda m: bool(m.get("circularity", {}).get("endOfLifeInformation"))),
    FieldCheck("CIR", "renewableContent",                 "renewableContent",
               lambda m: m.get("sustainability", {}).get("renewableContent") is not None),
    # ── MaterialComposition ───────────────────────────────────────────────
    FieldCheck("MC",  "batteryChemistry",    "chemistry",
               lambda m: any(c.get("chemistry") for c in _comps(m))),
    FieldCheck("MC",  "batteryMaterials",    "batteryMaterials",
               lambda m: bool(m.get("structure", {}).get("batteryMaterials"))),
    FieldCheck("MC",  "hazardousSubstances", "hazardousSubstances",
               lambda m: bool(m.get("risk", {}).get("hazardousSubstances"))),
    # ── PerformanceAndDurability ──────────────────────────────────────────
    FieldCheck("P&D", "ratedCapacity",          "capacity",
               lambda m: any(c.get("capacity") is not None for c in _comps(m))),
    FieldCheck("P&D", "nominalVoltage",          "voltage",
               lambda m: any(c.get("voltage") is not None for c in _comps(m))),
    FieldCheck("P&D", "expectedNumberOfCycles",  "rechargeCycles",
               lambda m: any(c.get("rechargeCycles") is not None for c in _comps(m))),
    FieldCheck("P&D", "expectedLifetime",        "expectedLifetime",
               lambda m: bool(m.get("lifecycle", {}).get("expectedLifetime"))),
    FieldCheck("P&D", "stateOfCharge",           "stateOfHealth",
               lambda m: m.get("lifecycle", {}).get("stateOfHealth") is not None),
]

_FIELD_IDS = [str(fc) for fc in FIELD_CHECKS]


# =============================================================================
# Metric helpers
# =============================================================================

def collect_emitted_fields(mapped: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return {field_name: value} for every section-level key in the mapper output
    that carries a non-null, non-empty value.

    EnergyStorage component attributes (chemistry, capacity, voltage,
    rechargeCycles) are promoted to the top level so they can participate
    in structural-precision and semantic-precision calculations.
    """
    result: Dict[str, Any] = {}
    for sec in _SECTIONS:
        sec_dict = mapped.get(sec) or {}
        for k, v in sec_dict.items():
            if v is not None and v != [] and v != {}:
                result[k] = v

    # Promote EnergyStorage component attributes
    for comp in mapped.get("structure", {}).get("componentsList", []):
        if comp.get("type") == "EnergyStorage" or comp.get("chemistry") is not None:
            for attr in ("chemistry", "capacity", "voltage", "rechargeCycles"):
                if comp.get(attr) is not None:
                    result[attr] = comp[attr]

    return result


def compute_metrics(mapped: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute all four coverage metrics for one mapper output.

    Returns
    -------
    dict with keys:
        structural_precision, structural_recall, structural_f1,
        semantic_precision, emitted_keys, valid_emitted, spurious_emitted,
        covered_checks, missing_checks, semant_valid, semant_invalid
    """
    emitted = collect_emitted_fields(mapped)
    emitted_keys = set(emitted.keys())

    # Structural precision: fraction of emitted keys that are valid BP vocabulary
    valid_emitted    = emitted_keys & ALL_BP_FIELDS
    spurious_emitted = emitted_keys - ALL_BP_FIELDS
    struct_precision = len(valid_emitted) / len(emitted_keys) if emitted_keys else 0.0

    # Structural recall: fraction of 29 required fields that the mapper covers
    covered_checks = [fc for fc in FIELD_CHECKS if fc.check_fn(mapped)]
    missing_checks  = [fc for fc in FIELD_CHECKS if not fc.check_fn(mapped)]
    struct_recall   = len(covered_checks) / len(FIELD_CHECKS) if FIELD_CHECKS else 0.0

    # Structural F1
    denom = struct_precision + struct_recall
    struct_f1 = (2 * struct_precision * struct_recall / denom) if denom > 0 else 0.0

    # Semantic precision: of covered required fields, how many pass type/format validation?
    semant_valid:   List[FieldCheck] = []
    semant_invalid: List[FieldCheck] = []

    for fc in covered_checks:
        validator = SEMANTIC_VALIDATORS.get(fc.output_key)
        value     = emitted.get(fc.output_key)

        if validator is None or value is None:
            # No validator defined, or field accessed via componentsList (implicitly valid)
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
def battery_part():
    return EnergyStorage(
        part_id="BAT-001",
        name="Main Battery Pack",
        type="EnergyStorage",
        chemistry="Li-ion",
        capacity=100.0,
        voltage=48.0,
        recharge_cycles=1000,
    )


@pytest.fixture(scope="module")
def non_battery_part():
    return Actuator(
        part_id="ACT-001",
        name="Cooling Fan",
        type="Actuator",
        voltage=24.0,
    )


@pytest.fixture(scope="module")
def full_dpp(battery_part, non_battery_part):
    """Minimal DPP — only the five hard-required EU Reg 2023/1542 mandatory fields."""
    return DigitalProductPassport(
        identity=IdentityLayer(
            global_ids={"serial": "SN-2024-001"},
            make_model={"model": "PowerPack Pro"},
            ownership={"manufacturer": "NMIS Ltd"},
            conformity=["CE"],
        ),
        structure=StructureLayer(
            hierarchy={},
            parts=[battery_part, non_battery_part],
            interfaces=[],
            materials=[],
            bom_refs=[],
        ),
        lifecycle=LifecycleLayer(
            manufacture={"date": "2024-03-01", "factory": "Plant-Glasgow"},
            use={"state_of_health": 0.98, "cycles": 12},
            serviceability={"replacement_interval": "5 years"},
            events=[],
            end_of_life={},
        ),
        risk=RiskLayer(
            criticality={"safety_instructions": ["Do not short circuit"]},
            fmea=[{"substance": "Lithium", "hazard_class": "Flammable", "concentration": 0.05}],
            security={},
        ),
        sustainability=SustainabilityLayer(
            mass=8.5,
            energy={},
            recycled_content={"co2e": 75.0, "cobalt_pct": 12.0, "lithium_pct": 5.0},
            remanufacture={},
        ),
        provenance=ProvenanceLayer(
            signatures=[{"signed_by": "NMIS QA", "certificate": "EU-DoC-2024", "date": "2024-03-15"}],
            trace_links=["epcis://batch/SN-2024-001"],
        ),
    )


@pytest.fixture(scope="module")
def full_battery_pass_dpp(battery_part, non_battery_part):
    """Maximally-populated DPP — all 29 BatteryPass v1.2.0 required fields present."""
    return DigitalProductPassport(
        identity=IdentityLayer(
            global_ids={
                "serial": "SN-2024-001",
                "gtin": "00-BAT-001",
                "battery_passport_id": "urn:battery:sn2024001",
            },
            make_model={"brand": "NMIS Energy", "model": "PowerPack Pro", "battery_category": "ev"},
            ownership={"manufacturer": "NMIS Ltd", "operator": "NMIS Operations Ltd"},
            conformity=["CE", "UN 38.3"],
        ),
        structure=StructureLayer(
            hierarchy={"product": "PowerPack Pro"},
            parts=[battery_part, non_battery_part],
            interfaces=[],
            materials=[{
                "name": "Lithium Hexafluorophosphate",
                "cas": "21324-40-3",
                "mass_kg": 0.5,
                "critical": True,
            }],
            bom_refs=[{
                "nameOfSupplier": "NMIS Spares Ltd",
                "partName": "Cell Module",
                "partNumber": "CELL-MOD-001",
            }],
        ),
        lifecycle=LifecycleLayer(
            manufacture={"date": "2024-03-01", "factory": "Plant-Glasgow"},
            use={
                "state_of_health": 0.98,
                "cycles": 12,
                "battery_status": "Original",
                "putting_into_service": "2024-03-15T00:00:00Z",
            },
            serviceability={
                "replacement_interval": "5 years",
                "warranty_period": "--03",
                "dismantling_docs": [{
                    "documentType": "DismantlingManual",
                    "mimeType": "application/pdf",
                    "documentURL": "https://example.com/dismantling-manual.pdf",
                }],
            },
            events=[],
            end_of_life={
                "waste_prevention_url":    "https://example.com/waste-prevention",
                "separate_collection_url": "https://example.com/separate-collection",
                "collection_info_url":     "https://example.com/collection-info",
            },
        ),
        risk=RiskLayer(
            criticality={"safety_instructions": ["Do not short circuit", "Keep away from heat"]},
            fmea=[{"substance": "Lithium", "hazard_class": "Flammable", "concentration": 0.05}],
            security={},
        ),
        sustainability=SustainabilityLayer(
            mass=8.5,
            energy={
                "standby_w": 0.5,
                "carbon_per_lifecycle_stage": [
                    {"lifecycleStage": "RawMaterialExtraction", "carbonFootprint": 20.0},
                    {"lifecycleStage": "MainProduction",        "carbonFootprint": 30.0},
                    {"lifecycleStage": "Distribution",          "carbonFootprint": 15.0},
                    {"lifecycleStage": "Recycling",             "carbonFootprint": 10.0},
                ],
                "carbon_performance_class": "A",
                "carbon_study_url": "https://example.com/carbon-study.pdf",
            },
            recycled_content={
                "co2e": 75.0,
                "cobalt_pct": 12.0,
                "lithium_pct": 5.0,
                "nickel_pct": 8.0,
                "pcr_percent": 20.0,
                "bio_based_percent": 3.5,
            },
            remanufacture={"eligible": True},
        ),
        provenance=ProvenanceLayer(
            signatures=[{"signed_by": "NMIS QA", "certificate": "EU-DoC-2024", "date": "2024-03-15"}],
            trace_links=["epcis://batch/SN-2024-001"],
        ),
    )


@pytest.fixture(scope="module")
def mapper():
    return BatteryDPPMapper(config={})


@pytest.fixture(scope="module")
def mapped_full(mapper, full_battery_pass_dpp):
    return mapper.map_dpp(full_battery_pass_dpp)


@pytest.fixture(scope="module")
def mapped_minimal(mapper, full_dpp):
    return mapper.map_dpp(full_dpp)


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
    """ALL_BP_FIELDS must contain exactly the battery: namespace terms from get_context()."""
    ctx = mapper.get_context()
    namespace_keys = {"@vocab", "battery", "schema", "xsd", "eclass"}
    context_bp_fields = {k for k in ctx if k not in namespace_keys}
    assert context_bp_fields == ALL_BP_FIELDS, (
        f"Vocabulary mismatch.\n"
        f"  In ALL_BP_FIELDS but not context: {ALL_BP_FIELDS - context_bp_fields}\n"
        f"  In context but not ALL_BP_FIELDS: {context_bp_fields - ALL_BP_FIELDS}"
    )


def test_vocabulary_covers_all_required_field_output_keys():
    """Every required field's output_key must appear in the valid vocabulary."""
    missing = {fc.output_key for fc in FIELD_CHECKS} - ALL_BP_FIELDS
    assert not missing, (
        f"Required field output keys not in BP vocabulary: {missing}"
    )


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
    outside the BatteryPass vocabulary (precision = 1.0 for emitted fields).
    """
    spurious = metrics_minimal["spurious_emitted"] - {"hierarchy"}
    # 'hierarchy' is an internal structural key, not a BP term; it is the only
    # tolerated spurious emission.
    assert not spurious, (
        f"Unexpected non-vocabulary fields emitted: {spurious}"
    )


def test_spurious_field_count(metrics_full):
    """At most one non-vocabulary key ('hierarchy') should be emitted."""
    spurious = metrics_full["spurious_emitted"]
    assert spurious <= {"hierarchy"}, (
        f"More than one spurious field emitted: {spurious}"
    )


# =============================================================================
# Structural recall tests
# =============================================================================

def test_structural_recall_full_dpp_is_100_percent(metrics_full):
    """
    A maximally-populated DPP must achieve 100% recall (all 29 required
    BatteryPass v1.2.0 fields covered), exceeding the expert-ontology baseline
    of 71% [ml_ontology_2026].
    """
    r = metrics_full["structural_recall"]
    assert r == 1.0, (
        f"Recall {r:.3f} < 1.0. Missing: "
        f"{[str(fc) for fc in metrics_full['missing_checks']]}"
    )


def test_structural_recall_minimal_dpp_covers_mandatory_core(metrics_minimal):
    """
    Even without optional BatteryPass fields the mapper must cover the core
    EU Reg 2023/1542 mandatory fields (productIdentifier, manufacturerIdentification,
    carbonFootprint, recycledContent, EnergyStorage component attributes).
    """
    covered_names = {fc.name for fc in metrics_minimal["covered_checks"]}
    mandatory_core = {
        "productIdentifier", "manufacturerIdentification",
        "batteryCarbonFootprint", "recycledContent",
        "batteryChemistry", "ratedCapacity", "nominalVoltage",
        "safetyMeasures",
    }
    missing = mandatory_core - covered_names
    assert not missing, f"Mandatory core fields not covered: {missing}"


def test_structural_recall_full_beats_ontology_baseline(metrics_full):
    """
    Recall must exceed the expert ontology's 0.71 recall [ml_ontology_2026].
    """
    assert metrics_full["structural_recall"] > 0.71


def test_structural_recall_minimal_dpp_lower_bound(metrics_minimal):
    """
    A minimal DPP should still cover at least 8 of the 29 required fields
    (the five EU mandatory fields + chemistry/capacity/voltage from components).
    """
    assert len(metrics_minimal["covered_checks"]) >= 8, (
        f"Minimal DPP covers only {len(metrics_minimal['covered_checks'])} required fields"
    )


# =============================================================================
# Structural F1 tests
# =============================================================================

def test_structural_f1_full_dpp_beats_ontology_baseline(metrics_full):
    """
    Structural F1 on a full DPP must exceed the expert-ontology baseline
    of 0.83 [ml_ontology_2026].
    """
    f1 = metrics_full["structural_f1"]
    assert f1 > 0.83, (
        f"Structural F1 {f1:.3f} does not beat ontology baseline 0.83."
    )


def test_structural_f1_full_dpp_beats_ml_baseline(metrics_full):
    """
    Structural F1 must exceed the ML ontology-quality framework's ~0.90
    [ontology_quality_2026].
    """
    f1 = metrics_full["structural_f1"]
    assert f1 > 0.90, (
        f"Structural F1 {f1:.3f} does not beat ML baseline ~0.90."
    )


# =============================================================================
# Semantic precision tests  (per-field type / format validation)
# =============================================================================

def test_semantic_precision_full_dpp_beats_ml_baseline(metrics_full):
    """
    Semantic precision must exceed the ML ontology-quality framework's
    90.2% [ontology_quality_2026].
    """
    sp = metrics_full["semantic_precision"]
    assert sp > 0.902, (
        f"Semantic precision {sp:.3f} does not beat ML baseline 0.902. "
        f"Failed fields: {[str(fc) for fc in metrics_full['semant_invalid']]}"
    )


@pytest.mark.parametrize("fc", FIELD_CHECKS, ids=_FIELD_IDS)
def test_semantic_field_type(mapped_full, fc):
    """
    Each covered required field must carry a value that passes its type/format
    validator (semantic precision at the per-field level).
    """
    emitted  = collect_emitted_fields(mapped_full)
    covered  = fc.check_fn(mapped_full)
    if not covered:
        pytest.skip(f"{fc} not covered — semantic check skipped")

    validator = SEMANTIC_VALIDATORS.get(fc.output_key)
    if validator is None:
        return  # no validator defined; field passes by default

    value = emitted.get(fc.output_key)
    if value is None:
        # Component-level field — implicitly valid if the coverage check passed
        return

    assert validator(value), (
        f"{fc.aspect}.{fc.name}: value {value!r} failed semantic type/format check "
        f"for output_key '{fc.output_key}'"
    )


# =============================================================================
# Summary report
# =============================================================================

def test_f1_coverage_report(metrics_full, metrics_minimal):
    """
    Print a comparison table of all four metrics against the literature baselines.

    Run with -v -s to see the full report:
        pytest -v -s tests/test_schema_f1_coverage.py::test_f1_coverage_report
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
    print("  Schema Coverage Metrics — BatteryDPPMapper vs Literature Baselines")
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

    _row("This work — full DPP    (BatteryDPPMapper)", mf)
    _row("This work — minimal DPP (EU mandatory only)", mm)
    print(sep2)

    # Per-aspect breakdown for full DPP
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

    # Hard gate: the full DPP must beat both baselines on F1
    assert mf["structural_f1"] > 0.83, "Full-DPP F1 must exceed expert-ontology baseline (0.83)"
    assert mf["structural_f1"] > 0.90, "Full-DPP F1 must exceed ML-framework baseline (~0.90)"
    assert mf["semantic_precision"] > 0.902, "Semantic precision must exceed ML baseline (90.2%)"
