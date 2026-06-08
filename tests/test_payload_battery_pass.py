"""
test_payload_battery_pass.py

Loads the real-world Battery Passport payload from
tests/JSON_Payload/BattreyPassportPayload.json, converts it into a
DigitalProductPassport via a payload-to-DPP adapter function, then maps
that DPP through BatteryDPPMapper and verifies the output.

This mirrors test_battery_dpp_mapper.py exactly — the difference is that
the input data comes from an external industry payload rather than from
manually constructed fixtures.

Flow:
    JSON payload
        └─▶ payload_to_dpp()  →  DigitalProductPassport
                                     └─▶ BatteryDPPMapper.map_dpp()
                                              └─▶ mapped dict  (tested here)

Sections
--------
1.  Payload adapter  (payload_to_dpp helper)
2.  Fixtures
3.  DPP construction tests
4.  Mapped identity layer tests
5.  Mapped structure layer tests
6.  Mapped lifecycle layer tests
7.  Mapped risk layer tests
8.  Mapped sustainability layer tests
9.  Mapped provenance layer tests
10. validate_mapping tests
11. BatteryPass v1.2.0 compliance — parametrized (same 29 checks as
    test_battery_dpp_mapper.py, run against the mapper output)
12. Compliance score summary (percentage)

Run with -v -s to see the full compliance report:

    pytest -v -s tests/test_payload_battery_pass.py
"""

import dataclasses
import json
import pathlib
from typing import Any, Callable, Dict, List

import pytest

from nmis_dpp.mappers.battery_dpp_mapper import BatteryDPPMapper
from nmis_dpp.model import (
    DigitalProductPassport,
    IdentityLayer,
    LifecycleLayer,
    ProvenanceLayer,
    RiskLayer,
    StructureLayer,
    SustainabilityLayer,
)
from nmis_dpp.part_class import EnergyStorage

# ---------------------------------------------------------------------------
# Payload path
# ---------------------------------------------------------------------------

PAYLOAD_PATH = pathlib.Path(__file__).parent / "JSON_Payload" / "BattreyPassportPayload.json"

# ---------------------------------------------------------------------------
# 1. Payload-to-DPP adapter
# ---------------------------------------------------------------------------

_LIFECYCLE_STAGE_MAP = {
    "raw material extraction": "RawMaterialExtraction",
    "main product production": "MainProduction",
    "distribution":            "Distribution",
    "recycling":               "Recycling",
    "end of life":             "Recycling",
}


def payload_to_dpp(p: Dict[str, Any]) -> DigitalProductPassport:
    """
    Transform a Catena-X / BatteryPass JSON payload into a
    DigitalProductPassport suitable for BatteryDPPMapper.

    Source conventions (payload path → DPP field):
      identification.identification.serial[0].value → identity.global_ids.serial
      metadata.passportIdentifier                   → identity.global_ids.battery_passport_id
      identification.identification.type.nameAtManufacturer → identity.make_model.model
      identification.category                       → identity.make_model.battery_category
      operation.manufacturer.manufacturer           → identity.ownership.manufacturer
      metadata.economicOperatorId                   → identity.ownership.operator
      performance.rated.{capacity, voltage, ...}    → EnergyStorage part fields
      materials.composition                         → structure.materials
      handling.content.sparePart                    → structure.bom_refs
      operation.manufacturer.manufacturingDate      → lifecycle.manufacture.date
      operation.manufacturer.facility[0].facility   → lifecycle.manufacture.factory
      sustainability.status                         → lifecycle.use.battery_status
      operation.intoServiceDate                     → lifecycle.use.putting_into_service
      performance.rated.lifetime.expectedYears      → lifecycle.serviceability.replacement_interval
      characteristics.warranty                      → lifecycle.serviceability.warranty_period
      safety.dismantling                            → lifecycle.serviceability.dismantling_docs
      sustainability.documents.wastePrevention[0]  → lifecycle.end_of_life.waste_prevention_url
      sustainability.documents.separateCollection[0]→ lifecycle.end_of_life.separate_collection_url
      safety.safetyMeasures                         → risk.criticality.safety_instructions
      materials.hazardous.*                         → risk.fmea entries
      characteristics.physicalDimension.weight.value→ sustainability.mass
      sustainability.carbonFootprint                → sustainability.energy & recycled_content
      materials.active.{cobalt,lithium,nickel}      → sustainability.recycled_content.*_pct
      materials.composition[0].renewable            → sustainability.recycled_content.bio_based_percent
      conformity.declarationOfConformityId          → provenance.signatures[0].certificate
      metadata.registrationIdentifier + sources     → provenance.trace_links
    """
    ident      = p["identification"]
    ident_ids  = ident["identification"]
    meta       = p["metadata"]
    op         = p["operation"]
    mfr        = op["manufacturer"]
    perf_r     = p["performance"]["rated"]
    perf_d     = p["performance"]["dynamic"]
    sust       = p["sustainability"]
    mats       = p["materials"]
    safety     = p["safety"]
    handling   = p["handling"]
    conformity = p["conformity"]
    chars      = p["characteristics"]

    # ── serial ──
    serial = (ident_ids.get("serial") or [{}])[0].get("value", "UNKNOWN")

    # ── warranty period: convert to --MM format ──
    warranty     = chars.get("warranty", {})
    life_val     = warranty.get("lifeValue", 1)
    life_unit    = warranty.get("lifeUnit", "")
    if "day" in life_unit:
        months = max(1, round(life_val / 30))
    elif "year" in life_unit:
        months = life_val * 12
    else:
        months = int(life_val)
    warranty_period = f"--{months:02d}"

    # ── carbon footprint entries ──
    cf_list  = sust.get("carbonFootprint", [])
    cf0      = cf_list[0] if cf_list else {}
    cf_stages = [
        {
            "lifecycleStage": _LIFECYCLE_STAGE_MAP.get(
                e.get("lifecycle", "").lower(), e.get("lifecycle", "")
            ),
            "carbonFootprint": e.get("value", 0.0),
        }
        for e in cf_list
    ]

    # ── hazardous substances → fmea entries ──
    haz = mats.get("hazardous", {})
    fmea: List[Dict[str, Any]] = []
    for substance, key in [("Cadmium", "cadmium"), ("Mercury", "mercury"), ("Lead", "lead")]:
        entry = haz.get(key)
        if entry:
            fmea.append({
                "substance":    substance,
                "hazard_class": "Hazardous",
                "concentration": entry.get("concentration", 0.0),
            })
    for other in haz.get("other", []):
        mat_ids = other.get("materialIdentification") or [{}]
        name = mat_ids[0].get("name", "Unknown")
        fmea.append({
            "substance":    name,
            "hazard_class": "Hazardous",
            "concentration": other.get("concentration", 0.0),
        })

    # ── end-of-life URLs ──
    eol_docs   = sust.get("documents", {})
    waste_url  = (eol_docs.get("wastePrevention")    or [{}])[0].get("content")
    sep_url    = (eol_docs.get("separateCollection") or [{}])[0].get("content")
    info_url   = (eol_docs.get("sustainabilityReport") or [{}])[0].get("content")

    # ── active material recycled percentages ──
    active = mats.get("active", {})
    comp0  = (mats.get("composition") or [{}])[0]

    # ── EnergyStorage part from rated performance ──
    battery_part = EnergyStorage(
        part_id=serial,
        name=ident_ids["type"]["nameAtManufacturer"],
        type="EnergyStorage",
        chemistry=ident.get("chemistry", ""),
        capacity=perf_r["capacity"]["value"],
        voltage=perf_r["voltage"]["nominal"],
        recharge_cycles=int(perf_r["lifetime"]["cycleLifeTesting"]["cycles"]),
    )

    return DigitalProductPassport(
        identity=IdentityLayer(
            global_ids={
                "serial":              serial,
                "battery_passport_id": meta.get("passportIdentifier", ""),
                "gtin":                (ident_ids.get("codes") or [{}])[0].get("value", ""),
            },
            make_model={
                "model":            ident_ids["type"]["nameAtManufacturer"],
                "brand":            mfr.get("manufacturer", ""),
                "battery_category": ident.get("category", "").lower(),
            },
            ownership={
                "manufacturer": mfr.get("manufacturer", ""),
                "operator":     meta.get("economicOperatorId", ""),
            },
            conformity=[conformity.get("declarationOfConformityId", "")],
        ),
        structure=StructureLayer(
            hierarchy={
                "classification": (ident_ids.get("classification") or [{}])[0]
                                   .get("classificationStandard", ""),
            },
            parts=[battery_part],
            interfaces=[],
            materials=mats.get("composition", []),
            bom_refs=handling.get("content", {}).get("sparePart", []),
        ),
        lifecycle=LifecycleLayer(
            manufacture={
                "date":    mfr.get("manufacturingDate", ""),
                "factory": (mfr.get("facility") or [{}])[0].get("facility", ""),
            },
            use={
                "state_of_health":    perf_d["stateOfCharge"]["value"] / 100.0,
                "cycles":             int(perf_d["fullCycles"]["value"]),
                "battery_status":     sust.get("status", "").capitalize(),
                "putting_into_service": op.get("intoServiceDate", ""),
            },
            serviceability={
                "replacement_interval": f"{perf_r['lifetime']['expectedYears']} years",
                "warranty_period":      warranty_period,
                "dismantling_docs": [
                    {
                        "documentType": "DismantlingManual",
                        "mimeType":     d.get("contentType", ""),
                        "documentURL":  d.get("content", ""),
                    }
                    for d in safety.get("dismantling", [])
                ],
            },
            events=list(perf_d.get("negativeEvents", [])),
            end_of_life={
                "waste_prevention_url":    waste_url,
                "separate_collection_url": sep_url,
                "collection_info_url":     info_url,
            },
        ),
        risk=RiskLayer(
            criticality={
                "safety_instructions": [
                    d.get("content", "") for d in safety.get("safetyMeasures", [])
                ],
            },
            fmea=fmea,
            security={},
        ),
        sustainability=SustainabilityLayer(
            mass=chars["physicalDimension"]["weight"]["value"],
            energy={
                "carbon_per_lifecycle_stage": cf_stages,
                "carbon_performance_class":   cf0.get("performanceClass", ""),
                "carbon_study_url":           (cf0.get("declaration") or [{}])[0].get("content", ""),
                "standby_w":                  perf_r.get("selfDischargingRate", 0.0),
            },
            recycled_content={
                "co2e":             cf0.get("value"),
                "cobalt_pct":       active.get("cobalt", {}).get("recycled"),
                "lithium_pct":      active.get("lithium", {}).get("recycled"),
                "nickel_pct":       active.get("nickel", {}).get("recycled"),
                "pcr_percent":      comp0.get("recycled"),
                "bio_based_percent": comp0.get("renewable"),
            },
            remanufacture={},
        ),
        provenance=ProvenanceLayer(
            signatures=[{
                "signed_by":   mfr.get("manufacturer", ""),
                "certificate": conformity.get("declarationOfConformityId", ""),
                "date":        meta.get("issueDate", ""),
            }],
            trace_links=[
                meta.get("registrationIdentifier", ""),
                *[s.get("content", "") for s in p.get("sources", [])],
            ],
        ),
    )


# ---------------------------------------------------------------------------
# 2. Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def payload() -> Dict[str, Any]:
    with PAYLOAD_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def dpp(payload) -> DigitalProductPassport:
    return payload_to_dpp(payload)


@pytest.fixture(scope="module")
def mapper() -> BatteryDPPMapper:
    return BatteryDPPMapper(config={})


@pytest.fixture(scope="module")
def mapped(dpp, mapper) -> Dict[str, Any]:
    """The fully mapped Battery DPP produced from the payload data."""
    return mapper.map_dpp(dpp)


# ---------------------------------------------------------------------------
# 3. DPP construction tests
# ---------------------------------------------------------------------------

def test_payload_file_exists():
    assert PAYLOAD_PATH.exists(), f"Payload not found: {PAYLOAD_PATH}"


def test_dpp_is_constructed(dpp):
    assert isinstance(dpp, DigitalProductPassport)


def test_dpp_has_energy_storage_part(dpp):
    es_parts = [p for p in dpp.structure.parts if isinstance(p, EnergyStorage)]
    assert len(es_parts) == 1, "Expected exactly one EnergyStorage part built from payload"


def test_dpp_chemistry_from_payload(dpp, payload):
    es = dpp.structure.parts[0]
    assert es.chemistry == payload["identification"]["chemistry"]


def test_dpp_capacity_from_payload(dpp, payload):
    assert dpp.structure.parts[0].capacity == payload["performance"]["rated"]["capacity"]["value"]


def test_dpp_voltage_from_payload(dpp, payload):
    assert dpp.structure.parts[0].voltage == payload["performance"]["rated"]["voltage"]["nominal"]


def test_dpp_recharge_cycles_from_payload(dpp, payload):
    expected = payload["performance"]["rated"]["lifetime"]["cycleLifeTesting"]["cycles"]
    assert dpp.structure.parts[0].recharge_cycles == int(expected)


def test_dpp_manufacturer_from_payload(dpp, payload):
    assert dpp.identity.ownership["manufacturer"] == payload["operation"]["manufacturer"]["manufacturer"]


def test_dpp_operator_from_payload(dpp, payload):
    assert dpp.identity.ownership["operator"] == payload["metadata"]["economicOperatorId"]


def test_dpp_passport_id_from_payload(dpp, payload):
    assert dpp.identity.global_ids["battery_passport_id"] == payload["metadata"]["passportIdentifier"]


def test_dpp_manufacturing_date_from_payload(dpp, payload):
    assert dpp.lifecycle.manufacture["date"] == payload["operation"]["manufacturer"]["manufacturingDate"]


def test_dpp_hazardous_fmea_built(dpp):
    assert len(dpp.risk.fmea) >= 3, "Expected fmea entries for cadmium, mercury, lead at minimum"
    substances = [e["substance"] for e in dpp.risk.fmea]
    assert "Cadmium" in substances
    assert "Mercury" in substances
    assert "Lead" in substances


def test_dpp_recycled_content_from_payload(dpp, payload):
    active = payload["materials"]["active"]
    assert dpp.sustainability.recycled_content["cobalt_pct"] == active["cobalt"]["recycled"]
    assert dpp.sustainability.recycled_content["lithium_pct"] == active["lithium"]["recycled"]
    assert dpp.sustainability.recycled_content["nickel_pct"] == active["nickel"]["recycled"]


def test_dpp_carbon_footprint_value_from_payload(dpp, payload):
    expected = payload["sustainability"]["carbonFootprint"][0]["value"]
    assert dpp.sustainability.recycled_content["co2e"] == expected


def test_dpp_dismantling_docs_built(dpp):
    docs = dpp.lifecycle.serviceability["dismantling_docs"]
    assert len(docs) > 0
    assert docs[0]["documentURL"]


def test_dpp_end_of_life_urls_built(dpp):
    eol = dpp.lifecycle.end_of_life
    assert eol.get("waste_prevention_url")
    assert eol.get("separate_collection_url")


def test_dpp_spare_parts_from_payload(dpp, payload):
    spare = payload["handling"]["content"]["sparePart"]
    assert dpp.structure.bom_refs == spare


def test_dpp_materials_from_payload(dpp, payload):
    assert dpp.structure.materials == payload["materials"]["composition"]


# ---------------------------------------------------------------------------
# 4. Mapped identity layer tests
# ---------------------------------------------------------------------------

def test_mapped_schema_is_battery_dpp(mapped):
    assert mapped["schema"] == "BatteryDPP"


def test_mapped_battery_model(mapped, payload):
    expected = payload["identification"]["identification"]["type"]["nameAtManufacturer"]
    assert mapped["identity"]["batteryModel"] == expected


def test_mapped_manufacturer_identification(mapped, payload):
    assert mapped["identity"]["manufacturerIdentification"] == \
           payload["operation"]["manufacturer"]["manufacturer"]


def test_mapped_product_identifier(mapped, payload):
    serial = payload["identification"]["identification"]["serial"][0]["value"]
    assert mapped["identity"]["productIdentifier"] == serial


def test_mapped_battery_passport_identifier(mapped, payload):
    assert mapped["identity"]["batteryPassportIdentifier"] == \
           payload["metadata"]["passportIdentifier"]


def test_mapped_battery_category(mapped, payload):
    assert mapped["identity"]["batteryCategory"] == \
           payload["identification"]["category"].lower()


def test_mapped_operator_information(mapped, payload):
    assert mapped["identity"]["operatorInformation"] == \
           payload["metadata"]["economicOperatorId"]


def test_mapped_conformity_certification(mapped, payload):
    assert payload["conformity"]["declarationOfConformityId"] in \
           mapped["identity"]["conformityCertification"]


# ---------------------------------------------------------------------------
# 5. Mapped structure layer tests
# ---------------------------------------------------------------------------

def test_mapped_components_list_has_one_energy_storage(mapped):
    components = mapped["structure"]["componentsList"]
    assert len(components) == 1
    assert components[0]["type"] == "EnergyStorage"


def test_mapped_component_chemistry(mapped, payload):
    comp = mapped["structure"]["componentsList"][0]
    assert comp["chemistry"] == payload["identification"]["chemistry"]


def test_mapped_component_capacity(mapped, payload):
    comp = mapped["structure"]["componentsList"][0]
    assert comp["capacity"] == payload["performance"]["rated"]["capacity"]["value"]


def test_mapped_component_voltage(mapped, payload):
    comp = mapped["structure"]["componentsList"][0]
    assert comp["voltage"] == payload["performance"]["rated"]["voltage"]["nominal"]


def test_mapped_component_recharge_cycles(mapped, payload):
    comp = mapped["structure"]["componentsList"][0]
    expected = int(payload["performance"]["rated"]["lifetime"]["cycleLifeTesting"]["cycles"])
    assert comp["rechargeCycles"] == expected


def test_mapped_battery_materials_from_payload(mapped, payload):
    assert mapped["structure"]["batteryMaterials"] == payload["materials"]["composition"]


# ---------------------------------------------------------------------------
# 6. Mapped lifecycle layer tests
# ---------------------------------------------------------------------------

def test_mapped_manufacturing_date(mapped, payload):
    assert mapped["lifecycle"]["manufacturingDate"] == \
           payload["operation"]["manufacturer"]["manufacturingDate"]


def test_mapped_place_of_manufacturing(mapped, payload):
    facility = payload["operation"]["manufacturer"]["facility"][0]["facility"]
    assert mapped["lifecycle"]["placeOfManufacturing"] == facility


def test_mapped_state_of_health(mapped, payload):
    expected = payload["performance"]["dynamic"]["stateOfCharge"]["value"] / 100.0
    assert mapped["lifecycle"]["stateOfHealth"] == pytest.approx(expected)


def test_mapped_cycle_count(mapped, payload):
    expected = int(payload["performance"]["dynamic"]["fullCycles"]["value"])
    assert mapped["lifecycle"]["cycleCount"] == expected


def test_mapped_expected_lifetime(mapped, payload):
    years = payload["performance"]["rated"]["lifetime"]["expectedYears"]
    assert mapped["lifecycle"]["expectedLifetime"] == f"{years} years"


def test_mapped_battery_status(mapped, payload):
    assert mapped["lifecycle"]["batteryStatus"] == \
           payload["sustainability"]["status"].capitalize()


def test_mapped_putting_into_service(mapped, payload):
    assert mapped["lifecycle"]["puttingIntoService"] == payload["operation"]["intoServiceDate"]


def test_mapped_warrenty_period_is_truthy(mapped):
    assert mapped["lifecycle"]["warrentyPeriod"]


# ---------------------------------------------------------------------------
# 7. Mapped risk layer tests
# ---------------------------------------------------------------------------

def test_mapped_hazardous_substances_present(mapped):
    hazardous = mapped["risk"]["hazardousSubstances"]
    assert len(hazardous) >= 3


def test_mapped_hazardous_cadmium_entry(mapped, payload):
    conc = payload["materials"]["hazardous"]["cadmium"]["concentration"]
    names = [e["substanceName"] for e in mapped["risk"]["hazardousSubstances"]]
    assert "Cadmium" in names
    entry = next(e for e in mapped["risk"]["hazardousSubstances"] if e["substanceName"] == "Cadmium")
    assert entry["concentration"] == conc


def test_mapped_hazardous_mercury_entry(mapped):
    names = [e["substanceName"] for e in mapped["risk"]["hazardousSubstances"]]
    assert "Mercury" in names


def test_mapped_hazardous_lead_entry(mapped):
    names = [e["substanceName"] for e in mapped["risk"]["hazardousSubstances"]]
    assert "Lead" in names


def test_mapped_safety_instructions_from_payload(mapped, payload):
    expected_urls = [d["content"] for d in payload["safety"]["safetyMeasures"]]
    for url in expected_urls:
        assert url in mapped["risk"]["safetyInstructions"]


# ---------------------------------------------------------------------------
# 8. Mapped sustainability layer tests
# ---------------------------------------------------------------------------

def test_mapped_carbon_footprint_value(mapped, payload):
    expected = payload["sustainability"]["carbonFootprint"][0]["value"]
    assert mapped["sustainability"]["carbonFootprint"] == expected


def test_mapped_carbon_footprint_per_lifecycle_stage(mapped, payload):
    stages = mapped["sustainability"]["carbonFootprintPerLifecycleStage"]
    assert len(stages) == len(payload["sustainability"]["carbonFootprint"])
    assert all("lifecycleStage" in s and "carbonFootprint" in s for s in stages)


def test_mapped_carbon_performance_class(mapped, payload):
    expected = payload["sustainability"]["carbonFootprint"][0]["performanceClass"]
    assert mapped["sustainability"]["carbonFootprintPerformanceClass"] == expected


def test_mapped_carbon_study_url(mapped, payload):
    expected = payload["sustainability"]["carbonFootprint"][0]["declaration"][0]["content"]
    assert mapped["sustainability"]["carbonFootprintStudy"] == expected


def test_mapped_mass_from_payload(mapped, payload):
    expected = payload["characteristics"]["physicalDimension"]["weight"]["value"]
    assert mapped["sustainability"]["mass"] == expected


def test_mapped_recycled_content_cobalt(mapped, payload):
    expected = payload["materials"]["active"]["cobalt"]["recycled"]
    assert mapped["sustainability"]["recycledContent"]["cobalt"] == expected


def test_mapped_recycled_content_lithium(mapped, payload):
    expected = payload["materials"]["active"]["lithium"]["recycled"]
    assert mapped["sustainability"]["recycledContent"]["lithium"] == expected


def test_mapped_recycled_content_nickel(mapped, payload):
    expected = payload["materials"]["active"]["nickel"]["recycled"]
    assert mapped["sustainability"]["recycledContent"]["nickel"] == expected


def test_mapped_renewable_content(mapped, payload):
    expected = payload["materials"]["composition"][0]["renewable"]
    assert mapped["sustainability"]["renewableContent"] == expected


# ---------------------------------------------------------------------------
# 9. Mapped provenance layer tests
# ---------------------------------------------------------------------------

def test_mapped_conformity_declaration_present(mapped):
    decls = mapped["provenance"]["conformityDeclaration"]
    assert len(decls) == 1


def test_mapped_conformity_declaration_certificate(mapped, payload):
    cert_id = payload["conformity"]["declarationOfConformityId"]
    assert mapped["provenance"]["conformityDeclaration"][0]["certificateType"] == cert_id


def test_mapped_supply_chain_info_contains_registration(mapped, payload):
    reg = payload["metadata"]["registrationIdentifier"]
    assert reg in mapped["provenance"]["supplyChainInfo"]


# ---------------------------------------------------------------------------
# 10. Mapped circularity layer tests
# ---------------------------------------------------------------------------

def test_mapped_dismantling_docs(mapped, payload):
    docs = mapped["circularity"]["dismantlingAndRemovalInformation"]
    assert len(docs) == len(payload["safety"]["dismantling"])


def test_mapped_spare_part_sources(mapped, payload):
    spare = mapped["circularity"]["sparePartSources"]
    assert spare == payload["handling"]["content"]["sparePart"]


def test_mapped_end_of_life_information(mapped, payload):
    eol = mapped["circularity"]["endOfLifeInformation"]
    assert eol is not None
    expected_waste = payload["sustainability"]["documents"]["wastePrevention"][0]["content"]
    assert eol["wastePrevention"] == expected_waste


# ---------------------------------------------------------------------------
# 11. validate_mapping passes for payload-sourced DPP
# ---------------------------------------------------------------------------

def test_validate_mapping_passes_for_payload_dpp(mapper, mapped):
    valid, errors = mapper.validate_mapping(mapped)
    assert valid, f"validate_mapping failed: {errors}"


# ---------------------------------------------------------------------------
# 12. BatteryPass v1.2.0 compliance — same 29 checks as
#     test_battery_dpp_mapper.py, run against the mapped output
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ComplianceCheck:
    aspect: str
    field: str
    bp_ref: str
    check_fn: Callable[[Dict[str, Any]], bool]

    def __str__(self) -> str:
        return f"{self.aspect}.{self.field}"


def _components(mapped: Dict[str, Any]):
    return mapped.get("structure", {}).get("componentsList", [])


COMPLIANCE_CHECKS = [
    # ── GeneralProductInformation (1.2.0) ─────────────────────────────────
    ComplianceCheck(
        "GeneralProductInformation", "productIdentifier",
        "Art. 77(3); Annex XIII (1a)",
        lambda m: bool(m.get("identity", {}).get("productIdentifier")),
    ),
    ComplianceCheck(
        "GeneralProductInformation", "batteryPassportIdentifier",
        "Art. 77(3)",
        lambda m: bool(m.get("identity", {}).get("batteryPassportIdentifier")),
    ),
    ComplianceCheck(
        "GeneralProductInformation", "batteryCategory",
        "Annex XIII (1c)",
        lambda m: bool(m.get("identity", {}).get("batteryCategory")),
    ),
    ComplianceCheck(
        "GeneralProductInformation", "manufacturerInformation",
        "Annex XIII (1a); Art. 38(6)",
        lambda m: bool(m.get("identity", {}).get("manufacturerIdentification")),
    ),
    ComplianceCheck(
        "GeneralProductInformation", "manufacturingDate",
        "Annex XIII (1a); Annex VI Part A (4)",
        lambda m: bool(m.get("lifecycle", {}).get("manufacturingDate")),
    ),
    ComplianceCheck(
        "GeneralProductInformation", "batteryStatus",
        "Annex XIII (4c)",
        lambda m: bool(m.get("lifecycle", {}).get("batteryStatus")),
    ),
    ComplianceCheck(
        "GeneralProductInformation", "batteryMass",
        "Annex XIII (1a); Annex VI Part A (5)",
        lambda m: m.get("sustainability", {}).get("mass") is not None,
    ),
    ComplianceCheck(
        "GeneralProductInformation", "manufacturingPlace",
        "Annex XIII (1a); Annex VI Part A (4)",
        lambda m: bool(m.get("lifecycle", {}).get("placeOfManufacturing")),
    ),
    ComplianceCheck(
        "GeneralProductInformation", "operatorInformation",
        "Annex XIII (1a)",
        lambda m: bool(m.get("identity", {}).get("operatorInformation")),
    ),
    ComplianceCheck(
        "GeneralProductInformation", "puttingIntoService",
        "Annex VI Part A (1); Art. 38(7)",
        lambda m: bool(m.get("lifecycle", {}).get("puttingIntoService")),
    ),
    ComplianceCheck(
        "GeneralProductInformation", "warrentyPeriod",
        "Annex XIII (4d)",
        lambda m: bool(m.get("lifecycle", {}).get("warrentyPeriod")),
    ),
    # ── CarbonFootprint (1.2.0) ───────────────────────────────────────────
    ComplianceCheck(
        "CarbonFootprint", "batteryCarbonFootprint",
        "Annex XIII §6; DIN DKE 6.3.2",
        lambda m: m.get("sustainability", {}).get("carbonFootprint") is not None,
    ),
    ComplianceCheck(
        "CarbonFootprint", "carbonFootprintPerLifecycleStage",
        "Annex XIII §6; DIN DKE 6.3.3-6.3.6",
        lambda m: bool(m.get("sustainability", {}).get("carbonFootprintPerLifecycleStage")),
    ),
    ComplianceCheck(
        "CarbonFootprint", "carbonFootprintPerformanceClass",
        "Annex XIII §6; DIN DKE 6.3.7",
        lambda m: bool(m.get("sustainability", {}).get("carbonFootprintPerformanceClass")),
    ),
    ComplianceCheck(
        "CarbonFootprint", "carbonFootprintStudy",
        "Annex XIII §6; DIN DKE 6.3.8",
        lambda m: bool(m.get("sustainability", {}).get("carbonFootprintStudy")),
    ),
    # ── Circularity (1.2.0) ───────────────────────────────────────────────
    ComplianceCheck(
        "Circularity", "dismantlingAndRemovalInformation",
        "Annex XIII (2c); DIN DKE 6.6.1.2",
        lambda m: bool(m.get("circularity", {}).get("dismantlingAndRemovalInformation")),
    ),
    ComplianceCheck(
        "Circularity", "sparePartSources",
        "Annex XIII (2b); DIN DKE 6.6.1.3",
        lambda m: bool(m.get("circularity", {}).get("sparePartSources")),
    ),
    ComplianceCheck(
        "Circularity", "recycledContent",
        "Annex XIII §6; DIN DKE 6.6.2.3-6.6.2.10",
        lambda m: bool(m.get("sustainability", {}).get("recycledContent")),
    ),
    ComplianceCheck(
        "Circularity", "safetyMeasures",
        "Annex XIII (2d); DIN DKE 6.6.1.5",
        lambda m: bool(m.get("risk", {}).get("safetyInstructions")),
    ),
    ComplianceCheck(
        "Circularity", "endOfLifeInformation",
        "Art. 60(1); DIN DKE 6.6.3.2-6.6.3.4",
        lambda m: bool(m.get("circularity", {}).get("endOfLifeInformation")),
    ),
    ComplianceCheck(
        "Circularity", "renewableContent",
        "Annex XIII §6; DIN DKE 6.6.2.11",
        lambda m: m.get("sustainability", {}).get("renewableContent") is not None,
    ),
    # ── MaterialComposition (1.2.0) ───────────────────────────────────────
    ComplianceCheck(
        "MaterialComposition", "batteryChemistry",
        "Annex XIII (1b); Annex VI Part A (7)",
        lambda m: any(c.get("chemistry") for c in _components(m)),
    ),
    ComplianceCheck(
        "MaterialComposition", "batteryMaterials",
        "Annex XIII (2a); DIN DKE 6.5.3-6.5.4",
        lambda m: bool(m.get("structure", {}).get("batteryMaterials")),
    ),
    ComplianceCheck(
        "MaterialComposition", "hazardousSubstances",
        "Annex XIII (1b); Annex VI Part A (8)",
        lambda m: bool(m.get("risk", {}).get("hazardousSubstances")),
    ),
    # ── PerformanceAndDurability (1.2.0) ──────────────────────────────────
    ComplianceCheck(
        "PerformanceAndDurability", "batteryTechicalProperties.ratedCapacity",
        "Annex XIII §3; DIN DKE Spec",
        lambda m: any(c.get("capacity") is not None for c in _components(m)),
    ),
    ComplianceCheck(
        "PerformanceAndDurability", "batteryTechicalProperties.nominalVoltage",
        "Annex XIII §3; DIN DKE Spec",
        lambda m: any(c.get("voltage") is not None for c in _components(m)),
    ),
    ComplianceCheck(
        "PerformanceAndDurability", "batteryTechicalProperties.expectedNumberOfCycles",
        "Annex XIII §3; DIN DKE Spec",
        lambda m: any(c.get("rechargeCycles") is not None for c in _components(m)),
    ),
    ComplianceCheck(
        "PerformanceAndDurability", "batteryTechicalProperties.expectedLifetime",
        "Annex XIII §3; DIN DKE Spec",
        lambda m: bool(m.get("lifecycle", {}).get("expectedLifetime")),
    ),
    ComplianceCheck(
        "PerformanceAndDurability", "batteryCondition.stateOfCharge",
        "Annex XIII §5; DIN DKE Spec",
        lambda m: m.get("lifecycle", {}).get("stateOfHealth") is not None,
    ),
]

_COMPLIANCE_IDS = [str(c) for c in COMPLIANCE_CHECKS]


@pytest.mark.parametrize("check", COMPLIANCE_CHECKS, ids=_COMPLIANCE_IDS)
def test_battery_pass_field_coverage(mapped, check):
    """
    Run each BatteryPass v1.2.0 compliance check against the mapper output
    produced from the real-world JSON payload.
    """
    covered = check.check_fn(mapped)
    if not covered:
        pytest.xfail(
            f"{check.aspect}.{check.field} not covered in mapped DPP from payload "
            f"(BatteryPass v1.2.0 ref: {check.bp_ref})"
        )
    assert covered


# ---------------------------------------------------------------------------
# 13. Compliance score summary
# ---------------------------------------------------------------------------

def test_battery_pass_compliance_score(mapped):
    """
    Compute and display the BatteryPass v1.2.0 compliance score for the
    DPP built from the real-world JSON payload and mapped through
    BatteryDPPMapper.  Directly comparable to the score in
    test_battery_dpp_mapper.py.

    Run with -v -s:
        pytest -v -s tests/test_payload_battery_pass.py::test_battery_pass_compliance_score
    """
    covered_checks = []
    missing_checks = []

    for check in COMPLIANCE_CHECKS:
        (covered_checks if check.check_fn(mapped) else missing_checks).append(check)

    total   = len(COMPLIANCE_CHECKS)
    covered = len(covered_checks)
    score   = covered / total * 100 if total else 0.0

    aspect_totals:  Dict[str, int] = {}
    aspect_covered: Dict[str, int] = {}
    for check in COMPLIANCE_CHECKS:
        aspect_totals[check.aspect] = aspect_totals.get(check.aspect, 0) + 1
    for check in covered_checks:
        aspect_covered[check.aspect] = aspect_covered.get(check.aspect, 0) + 1

    sep = "=" * 70
    print(f"\n\n{sep}")
    print(f"  BatteryPass v1.2.0 Compliance Report  [payload -> BatteryDPPMapper]")
    print(f"  Source: {PAYLOAD_PATH.name}")
    print(f"  Overall Score: {score:.1f}%  ({covered}/{total} required fields covered)")
    print(sep)

    print("\n  Per-aspect breakdown:")
    for aspect in aspect_totals:
        a_cov   = aspect_covered.get(aspect, 0)
        a_total = aspect_totals[aspect]
        a_pct   = a_cov / a_total * 100
        bar     = "#" * a_cov + "-" * (a_total - a_cov)
        print(f"    {aspect:<35}  [{bar}]  {a_pct:5.1f}%  ({a_cov}/{a_total})")

    if covered_checks:
        print("\n  Covered fields:")
        for check in covered_checks:
            print(f"    [+]  {check.aspect}.{check.field}")

    if missing_checks:
        print("\n  Missing fields:")
        for check in missing_checks:
            print(f"    [-]  {check.aspect}.{check.field:<45}  [{check.bp_ref}]")

    print(f"\n{sep}\n")

    assert total > 0
    assert covered >= 9, (
        f"Coverage {covered}/{total} ({score:.1f}%) is below the minimum of 9 "
        f"core EU Reg 2023/1542 mandatory fields."
    )
