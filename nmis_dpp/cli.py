"""
cli.py

Command-line interface for the nmis_dpp package.
Allows users to generate sample Digital Product Passports mapped to available schemas.
"""

import json
import logging
import sys
from typing import Dict, Any

from nmis_dpp import get_global_registry
from nmis_dpp.model import (
    IdentityLayer, StructureLayer, LifecycleLayer, RiskLayer,
    SustainabilityLayer, ProvenanceLayer, DigitalProductPassport
)
from nmis_dpp.part_class import (
    Actuator, Sensor, PowerConversion
)
from nmis_dpp.utils import to_dict

# Configure basic logging to avoid noise but show important info
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

def create_sample_dpp() -> DigitalProductPassport:
    """
    Create a dummy DigitalProductPassport for demonstration purposes.
    Reused from usage.py example logic.
    """
    # 1. Define parts
    motor = Actuator(
        part_id="A001",
        name="Drive Motor",
        type="Actuator",
        torque=2.1,
        speed=1750,
        duty_cycle=0.7,
        voltage=48,
        actuation_type="electric"
    )
    temperature_sensor = Sensor(
        part_id="S003",
        name="Temp Sensor",
        type="Sensor",
        sensor_type="temperature",
        range_min=-40,
        range_max=120,
        accuracy=0.25,
        drift=0.01,
        response_time=7
    )
    psu = PowerConversion(
        part_id="P001",
        name="PSU",
        type="PowerConversion",
        input_voltage=230,
        output_voltage=48,
        power_rating=350,
        efficiency=0.92
    )

    # 2. Build layers
    identity = IdentityLayer(
        global_ids={"gtin": "987654321", "serial": "SN1245"},
        make_model={"brand": "Acme", "model": "UnitX", "hw_rev": "A", "fw_rev": "2.0"},
        ownership={"manufacturer": "Acme Ltd", "owner": "BuyerOrg", "operator": "MaintainerX", "location": "Berlin"},
        conformity=["CE", "RoHS", "UKCA"]
    )
    structure = StructureLayer(
        hierarchy={
            "product": "UnitX",
            "components": ["A001", "S003", "P001"] # Simplified referencing
        },
        parts=[motor, temperature_sensor, psu],
        interfaces=[
            {"type": "electrical", "details": {"voltage": 48, "connector": "XT60"}},
            {"type": "data", "details": {"protocol": "CAN"}}
        ],
        materials=[{"cas": "7439-89-6", "%mass": 70, "recyclable": "yes"}],
        bom_refs=["XWZ-002"]
    )
    lifecycle = LifecycleLayer(
        manufacture={"lot": "Batch77", "factory": "ACMEPlant", "date": "2025-03-18", "process": "injection", "co2e": 27.3},
        use={"counters": {"hours": 143}, "telemetry": {}},
        serviceability={"schedule": {"interval": "1Y"}, "repair_steps": ["Open housing", "Replace motor"], "repairability_score": 6},
        events=[{"event_type": "install", "timestamp": "2025-04-01"}],
        end_of_life={"disassembly": ["Unplug connectors"], "hazards": ["None"], "recovery_routes": ["Recycle", "Landfill"]}
    )
    risk = RiskLayer(
        criticality={"levels": "Safety", "llp": False, "mtbf": 20000},
        fmea=[{"failure_mode": "overheat", "effect": "shutdown", "mitigation": "cooling upgrade"}],
        security={"sbom": "link", "vulnerabilities": [], "signing_keys": ["pubkey-xyz"], "update_policy": "signed-only"}
    )
    sustainability = SustainabilityLayer(
        mass=5.0,
        energy={"standby": 2.0, "active": 15.0, "water_use": 0.0},
        recycled_content={"pcr_percent": 39, "bio": 2},
        remanufacture={"eligible": True, "grading_criteria": {"condition": "A"}},
    )
    provenance = ProvenanceLayer(
        signatures=[{"type": "manufacturer", "certificate": "certABC"}],
        trace_links=["EPCIS:event1", "NFC:TAG773"]
    )

    # 3. Create passport
    return DigitalProductPassport(
        identity=identity,
        structure=structure,
        lifecycle=lifecycle,
        risk=risk,
        sustainability=sustainability,
        provenance=provenance
    )

def main():
    print("--- NMIS DPP Generator CLI ---")
    
    registry = get_global_registry()
    schemas = registry.list_schemas()
    
    if not schemas:
        print("No schemas registered. Please check your installation.")
        return

    print("Available schemas:")
    for i, s in enumerate(schemas, 1):
        print(f"  {i}. {s}")
    
    schema_choice = input("\nEnter the name of the schema to use (or 'q' to quit): ").strip()
    
    if schema_choice.lower() == 'q':
        return

    # Basic alias resolution fallback if they typed a number (optional enhancement)
    # but sticking to name as per plan
    
    try:
        mapper = registry.get_mapper(schema_choice)
    except KeyError:
        print(f"Error: Schema '{schema_choice}' not found.")
        print(f"Available: {', '.join(schemas)}")
        sys.exit(1)

    print(f"\nGenerating sample DPP and mapping to {mapper.get_schema_name()}...")
    
    dpp = create_sample_dpp()
    
    try:
        mapped_data = mapper.map_dpp(dpp)
        print("\n--- Mapped Result (JSON-LD) ---")
        print(json.dumps(mapped_data, indent=2))
        print("\nSuccess.")
    except Exception as e:
        print(f"Error during mapping: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
