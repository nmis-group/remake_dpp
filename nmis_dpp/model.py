from dataclasses import dataclass, field
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
from .part_class import PartClass

@dataclass
class IdentityLayer:
    """
    Represents product identity attributes for a digital product passport.

    Attributes:
        global_ids (dict): Unique global identifiers for the product (e.g. GTIN, SGTIN, serial, manufacturer PN, UUID).
        make_model (dict): Manufacturing data (brand, model, hardware revision, firmware revision).
        ownership (dict): Manufacturer, current owner, operator, and location information.
        conformity (List[str]): List of certifications and approvals (e.g. CE, UKCA, FAA, RoHS).
    """
    global_ids: Dict[str, str]
    make_model: Dict[str, str]
    ownership: Dict[str, str]
    conformity: List[str]

@dataclass
class StructureLayer:
    """
    Describes how the product is structurally organized and built.

    Attributes:
        hierarchy (dict): Describes hierarchy — Product → Subsystem → Assembly → Component → Material.
        parts (List[PartClass]): List of universal part class instances present in the product.
        interfaces (List[dict]): Connection details such as electrical, mechanical, fluid, and data interfaces.
        materials (List[dict]): List describing material composition, CAS numbers, % mass, and recyclability.
        bom_refs (List[str]): Bill of Materials references, alternates, and supersessions for parts.
    """
    hierarchy: Dict[str, any]
    parts: List[PartClass]
    interfaces: List[Dict[str, any]]
    materials: List[Dict[str, any]]
    bom_refs: List[str]

@dataclass
class LifecycleLayer:
    """
    Tracks manufacturing, usage, and serviceability data across the product's life.

    Attributes:
        manufacture (dict): Information about lot, batch, factory, date, process, and CO₂ equivalent.
        use (dict): Usage counters (e.g. hours/cycles), operating ranges, telemetry summaries.
        serviceability (dict): Maintenance schedule, repair steps, spare part mapping, repairability score.
        events (List[dict]): Major lifecycle events (installation, removal, inspection, failures, updates).
        end_of_life (dict): Data for disassembly steps, hazards, and recovery routes.
    """
    manufacture: Dict[str, any]
    use: Dict[str, any]
    serviceability: Dict[str, any]
    events: List[Dict[str, any]]
    end_of_life: Dict[str, any]

@dataclass
class RiskLayer:
    """
    Criticality, reliability, and security information relevant to product risk assessment.

    Attributes:
        criticality (dict): Safety/mission level, life-limited part (LLP) flag, MTBF.
        fmea (List[dict]): Failure mode, effects, and mitigation analysis entries.
        security (dict): Software bill of materials (SBOM), vulnerability data, signing key and update policy.
    """
    criticality: Dict[str, any]
    fmea: List[Dict[str, any]]
    security: Dict[str, any]

@dataclass
class SustainabilityLayer:
    """
    Sustainability and circularity attributes for product impact and end-of-life eligibility.

    Attributes:
        mass (float): Mass breakdown.
        energy (dict): Standby and active energy, water use.
        recycled_content (dict): Percentage PCR, bio-based, restricted substances.
        remanufacture (dict): Remanufacture eligibility and grading.
    """
    mass: float
    energy: Dict[str, float]
    recycled_content: Dict[str, any]
    remanufacture: Dict[str, any]

@dataclass
class ProvenanceLayer:
    """
    Provenance and trust metadata for the product.

    Attributes:
        signatures (List[dict]): Manufacturer/service signatures and certificates (e.g., EASA Form 1).
        trace_links (List[str]): Traceability links (EPCIS events, QR/NFC tags).
    """
    signatures: List[Dict[str, any]]
    trace_links: List[str]

@dataclass
class DigitalProductPassport:
    """
    The top-level digital product passport model, aggregating all layers for full product provenance.

    Attributes:
        identity (IdentityLayer): Identity attributes of the product.
        structure (StructureLayer): Structural attributes.
        lifecycle (LifecycleLayer): Manufacturing, usage, and events.
        risk (RiskLayer): Safety and reliability information.
        sustainability (SustainabilityLayer): Impact and circularity properties.
        provenance (ProvenanceLayer): Product trust signatures and traceability links.
    """
    identity: IdentityLayer
    structure: StructureLayer
    lifecycle: LifecycleLayer
    risk: RiskLayer
    sustainability: SustainabilityLayer
    provenance: ProvenanceLayer

