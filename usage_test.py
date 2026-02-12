"""
usage_test.py

Generates a dummy Digital Product Passport for a "Coffee Machine" with 50+ parts.
Verifies the mapping functionality of the nmis_dpp package (ECLASS, ISA-95).
"""

import json
import logging
from typing import List
import random

from nmis_dpp import get_global_registry, register_default_mappers
from nmis_dpp.model import (
    IdentityLayer, StructureLayer, LifecycleLayer, RiskLayer,
    SustainabilityLayer, ProvenanceLayer, DigitalProductPassport
)
from nmis_dpp.part_class import (
    PartClass, Actuator, Sensor, PowerConversion, Thermal, Fluidics,
    Structural, ControlUnit, UserInterface, Fastener, Connectivity
)
from nmis_dpp.utils import to_dict

# Ensure default mappers are registered
register_default_mappers()

def generate_coffee_machine_parts() -> List[PartClass]:
    """Generates a list of ~50 parts for a coffee machine."""
    parts = []
    
    # 1. Core Actuators (Pumps, Grinders)
    parts.append(Actuator(
        part_id="M01-MainPump", name="High Pressure Pump", type="Actuator",
        torque=1.5, speed=3000, voltage=230, actuation_type="vibration_pump"
    ))
    parts.append(Actuator(
        part_id="M02-Grinder", name="Bean Grinder Motor", type="Actuator",
        torque=2.0, speed=1500, voltage=230, actuation_type="electric_motor"
    ))
    parts.append(Actuator(
        part_id="M03-BrewGroup", name="Brew Group Driver", type="Actuator",
        torque=5.0, speed=60, voltage=24, actuation_type="servo"
    ))

    # 2. Thermal Components
    parts.append(Thermal(
        part_id="H01-Boiler", name="Main Boiler", type="Thermal",
        power=1400, delta_t=95, airflow=0
    ))
    parts.append(Thermal(
        part_id="H02-SteamThermoblock", name="Steam Thermoblock", type="Thermal",
        power=1200, delta_t=130, airflow=0
    ))
    parts.append(Thermal(
        part_id="H03-CupWarmer", name="Cup Warmer Plate", type="Thermal",
        power=50, delta_t=40, airflow=0
    ))

    # 3. Sensors
    for i in range(1, 4):
        parts.append(Sensor(
            part_id=f"S{i:02d}-NTC", name=f"NTC Temp Sensor {i}", type="Sensor",
            sensor_type="temperature", range_min=0, range_max=150
        ))
    parts.append(Sensor(
        part_id="S04-Flow", name="Flow Meter", type="Sensor",
        sensor_type="flow", range_min=0, range_max=2000
    ))
    parts.append(Sensor(
        part_id="S05-Level", name="Water Tank Level", type="Sensor",
        sensor_type="capacitive_level"
    ))

    # 4. Fluidics
    parts.append(Fluidics(
        part_id="F01-Tank", name="Water Tank", type="Fluidics",
        volume=2.5, fluid_type="water"
    ))
    parts.append(Fluidics(
        part_id="F02-Sprout", name="Coffee Sprout", type="Fluidics",
        fluid_type="coffee"
    ))
    # Tubing segments
    for i in range(1, 6):
        parts.append(Fluidics(
            part_id=f"F{10+i}-Tube", name=f"PTFE Tube {i}", type="Fluidics",
            pressure=15, fluid_type="water/steam"
        ))

    # 5. Electronics / Control
    parts.append(ControlUnit(
        part_id="E01-MainBoard", name="Main PCB Controller", type="ControlUnit",
        cpu_type="STM32", memory=1.0, firmware_version="3.4.1"
    ))
    parts.append(PowerConversion(
        part_id="P01-PSU", name="Power Supply 230V-24V", type="PowerConversion",
        input_voltage=230, output_voltage=24, power_rating=150
    ))
    parts.append(UserInterface(
        part_id="UI01-Display", name="Touch Display", type="UserInterface",
        ui_type="touchscreen", display_size=5.0
    ))

    # 6. Structural (Housing parts)
    parts.append(Structural(
        part_id="ST01-Chassis", name="Main Chassis Frame", type="Structural",
        material="Steel", mass=2.5
    ))
    parts.append(Structural(
        part_id="ST02-HousingL", name="Housing Left", type="Structural",
        material="ABS Plastic", mass=0.4
    ))
    parts.append(Structural(
        part_id="ST03-HousingR", name="Housing Right", type="Structural",
        material="ABS Plastic", mass=0.4
    ))
    parts.append(Structural(
        part_id="ST04-DripTray", name="Drip Tray", type="Structural",
        material="Steel/Plastic", mass=0.8
    ))

    # 7. Connectivity (Cables)
    for i in range(1, 6):
        parts.append(Connectivity(
            part_id=f"C{i:02d}-Cable", name=f"Harness Segment {i}", type="Connectivity",
            interface_type="power/signal"
        ))

    # 8. Fasteners (Screws - fill up to ~50)
    current_count = len(parts)
    target_count = 50
    screw_types = ["M3x10", "M4x12", "M5x20"]
    for i in range(target_count - current_count + 1): # Fill + 1
        stype = random.choice(screw_types)
        parts.append(Fastener(
            part_id=f"FAST-{i+1:02d}", name=f"Screw {stype}", type="Fastener",
            fastener_type="screw", material="Stainless Steel", length=int(stype.split('x')[1])
        ))

    return parts

def create_coffee_machine_dpp(parts: List[PartClass]) -> DigitalProductPassport:
    """Creates the full DPP object."""
    part_ids = [p.part_id for p in parts]
    
    return DigitalProductPassport(
        identity=IdentityLayer(
            global_ids={"gtin": "00-CAFE-9000", "serial": "CM2025-001"},
            make_model={"brand": "BaristaPro", "model": "EspressoMaster 9000"},
            ownership={"manufacturer": "CoffeeTech Industries"},
            conformity=["CE", "UL", "CB"]
        ),
        structure=StructureLayer(
            hierarchy={"product": "EspressoMaster 9000"},
            parts=parts,
            # components=part_ids, # Removed invalid arg
            interfaces=[],
            materials=[],
            bom_refs=[]
        ),
        lifecycle=LifecycleLayer(
            manufacture={"date": "2025-06-01", "factory": "Plant A"},
            use={},
            serviceability={},
            events=[],
            end_of_life={}
        ),
        risk=RiskLayer(criticality={}, fmea=[], security={}),
        sustainability=SustainabilityLayer(mass=12.5, energy={}, recycled_content={}, remanufacture={}),
        provenance=ProvenanceLayer(signatures=[], trace_links=[])
    )

def main():
    print("Generating Coffee Machine Data...")
    parts = generate_coffee_machine_parts()
    print(f"Generated {len(parts)} parts.")
    
    dpp = create_coffee_machine_dpp(parts)
    print("DPP Created.")

    registry = get_global_registry()
    
    # 1. Map to ECLASS
    print("\nMapping to ECLASS...")
    try:
        eclass_mapper = registry.get_mapper("ECLASS")
        eclass_output = eclass_mapper.map_dpp(dpp)
        print("ECLASS Mapping Successful.")
        # Optional: Print snippet
        print(f"ECLASS Schema: {eclass_output.get('schema')}")
        print(f"Mapped Components: {len(eclass_output.get('structure', {}).get('components', []))}")
        
    except Exception as e:
        print(f"ECLASS Mapping Failed: {e}")

    # 2. Map to ISA-95
    print("\nMapping to ISA-95...")
    try:
        isa95_mapper = registry.get_mapper("ISA-95")
        isa95_output = isa95_mapper.map_dpp(dpp)
        print("ISA-95 Mapping Successful.")
        print(f"ISA-95 Schema: {isa95_output.get('schema')}")
        print(f"Nested Equipment: {len(isa95_output.get('structure', {}).get('NestedEquipment', []))}")

    except Exception as e:
        print(f"ISA-95 Mapping Failed: {e}")

    print("\nUsage Test Complete.")

if __name__ == "__main__":
    main()
