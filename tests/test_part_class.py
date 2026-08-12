"""
test_part_class.py

Unit tests for universal PartClass subclasses in the Digital Product Passport system.

Covers:
    - Instantiation of each primary part class with sample attributes
    - Property correctness and type checks
    - Dictionary serialization of each part for Digital Product Passport integration

To run:
    pytest tests/test_part_class.py

Author: Anmol Kumar, NMIS
"""

from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

import pytest
from nmis_dpp.part_class import (
    PowerConversion, EnergyStorage, Actuator, Sensor, ControlUnit,
    UserInterface, Thermal, Fluidics, Structural, Transmission,
    Protection, Connectivity, SoftwareModule, Consumable, Fastener
)
from nmis_dpp.utils import to_dict
from nmis_dpp.eclass_build_mapping import (
    classify_domain_for_class,
    domain_score as eclass_domain_score,
    DOMAIN_KEYWORDS as ECLASS_DOMAIN_KEYWORDS,
    MIN_SCORE as ECLASS_MIN_SCORE,
)
from nmis_dpp.isa95_build_mapping import (
    classify_domain as isa95_classify_domain,
    domain_score as isa95_domain_score,
    DOMAIN_KEYWORDS as ISA95_DOMAIN_KEYWORDS,
    MIN_SCORE as ISA95_MIN_SCORE,
)

def test_power_conversion():
    """
    Test instantiation and properties of PowerConversion class.
    """
    part = PowerConversion(
        part_id="PC1",
        name="Inverter",
        type="PowerConversion",
        input_voltage=230,
        output_voltage=24,
        power_rating=500,
        efficiency=0.95
    )
    assert part.input_voltage == 230
    assert part.output_voltage == 24
    assert part.power_rating == 500
    assert part.efficiency == 0.95

def test_sensor():
    """
    Test Sensor part class, including optional attributes.
    """
    part = Sensor(
        part_id="SENS1",
        name="Pressure Sensor",
        type="Sensor",
        sensor_type="pressure",
        range_min=0,
        range_max=10,
        accuracy=0.02,
        drift=0.001,
        response_time=5
    )
    assert part.sensor_type == "pressure"
    assert part.range_min == 0
    assert part.range_max == 10
    assert part.accuracy == 0.02
    assert part.drift == 0.001
    assert part.response_time == 5

def test_actuator():
    """
    Test the Actuator part class and its mechanical properties.
    """
    part = Actuator(
        part_id="ACT1",
        name="Servo Motor",
        type="Actuator",
        torque=2.5,
        speed=1800,
        duty_cycle=0.75,
        voltage=24,
        actuation_type="electric"
    )
    assert part.torque == 2.5
    assert part.speed == 1800
    assert part.voltage == 24
    assert part.duty_cycle == 0.75
    assert part.actuation_type == "electric"

def test_control_unit():
    """
    Ensure proper instantiation of ControlUnit parts.
    """
    part = ControlUnit(
        part_id="CU1",
        name="ECU Board",
        type="ControlUnit",
        cpu_type="ARM Cortex-M",
        memory=128,
        firmware_version="1.0.3",
        io_count=16
    )
    assert part.cpu_type == "ARM Cortex-M"
    assert part.memory == 128
    assert part.firmware_version == "1.0.3"
    assert part.io_count == 16

def test_user_interface():
    """
    Test UserInterface component instantiation.
    """
    part = UserInterface(
        part_id="UI1",
        name="Touch HMI",
        type="UserInterface",
        ui_type="touchscreen",
        display_size=7.0,
        input_methods=["touch", "button"],
        indicator_count=3
    )
    assert part.display_size == 7.0
    assert "touch" in part.input_methods
    assert part.indicator_count == 3

def test_thermal():
    """
    Validate properties for Thermal part class.
    """
    part = Thermal(
        part_id="THERM1",
        name="Blower Fan",
        type="Thermal",
        power=50,
        delta_t=30,
        airflow=120
    )
    assert part.power == 50
    assert part.delta_t == 30
    assert part.airflow == 120

def test_fluidics():
    """
    Confirm Fluidics device instantiation and field typing.
    """
    part = Fluidics(
        part_id="FLD1",
        name="Water Pump",
        type="Fluidics",
        flow_rate=15,
        pressure=2.5,
        fluid_type="water",
        volume=2.0
    )
    assert part.flow_rate == 15
    assert part.pressure == 2.5
    assert part.fluid_type == "water"
    assert part.volume == 2.0

def test_structural():
    """
    Ensure Structural elements accept valid attributes.
    """
    part = Structural(
        part_id="STR1",
        name="Main Frame",
        type="Structural",
        material="Aluminum",
        mass=4.0,
        dimensions={"length": 100.0, "width": 20.0},
        load_rating=2000
    )
    assert part.material == "Aluminum"
    assert part.mass == 4.0
    assert part.dimensions["length"] == 100.0
    assert part.load_rating == 2000

def test_transmission():
    """
    Transmission class instantiation and core attribute check.
    """
    part = Transmission(
        part_id="TRAN1",
        name="Gearbox",
        type="Transmission",
        torque_rating=300,
        speed_rating=6000,
        transmission_type="gear"
    )
    assert part.torque_rating == 300
    assert part.speed_rating == 6000
    assert part.transmission_type == "gear"

def test_protection():
    """
    Validate Protection part instantiation for fuses or breakers.
    """
    part = Protection(
        part_id="PROT1",
        name="Fuse",
        type="Protection",
        protection_type="fuse",
        rating=10,
        response_time=0.5
    )
    assert part.protection_type == "fuse"
    assert part.rating == 10
    assert part.response_time == 0.5

def test_connectivity():
    """
    Test for Connectivity devices like harnesses/connectors.
    """
    part = Connectivity(
        part_id="CONN1",
        name="Data Bus",
        type="Connectivity",
        interface_type="data",
        connector_standard="Ethernet",
        pin_count=8
    )
    assert part.interface_type == "data"
    assert part.connector_standard == "Ethernet"
    assert part.pin_count == 8

def test_software_module():
    """
    Test for the SoftwareModule class with standard software fields.
    """
    part = SoftwareModule(
        part_id="SW1",
        name="MCU Firmware",
        type="SoftwareModule",
        version="3.2.0",
        language="C",
        license="MIT",
        checksums={"sha256": "abcd1234"}
    )
    assert part.version == "3.2.0"
    assert part.language == "C"
    assert part.license == "MIT"
    assert part.checksums["sha256"] == "abcd1234"

def test_consumable():
    """
    Validate Consumable construction (e.g. filters, oils).
    """
    part = Consumable(
        part_id="CONS1",
        name="Grease Cartridge",
        type="Consumable",
        consumable_type="grease",
        capacity=500,
        replacement_interval="12M"
    )
    assert part.consumable_type == "grease"
    assert part.capacity == 500
    assert part.replacement_interval == "12M"

def test_fastener():
    """
    Test the Fastener class for correct field usage.
    """
    part = Fastener(
        part_id="FST1",
        name="Rivet",
        type="Fastener",
        fastener_type="rivet",
        material="Steel",
        diameter=5,
        length=12,
        strength=1500
    )
    assert part.fastener_type == "rivet"
    assert part.material == "Steel"
    assert part.diameter == 5
    assert part.length == 12
    assert part.strength == 1500

def test_serialization_to_dict():
    """
    Check that all part classes can be converted to dict for serialization.
    """
    part = Actuator(
        part_id="A_TEST",
        name="Test Actuator",
        type="Actuator",
        torque=1.1,
        speed=1000
    )
    part_dict = to_dict(part)
    assert isinstance(part_dict, dict)
    assert part_dict["type"] == "Actuator"
    assert "name" in part_dict and part_dict["name"] == "Test Actuator"


# =============================================================================
# Empirical validation of the domain-classification heuristic
# (eclass_build_mapping.classify_domain_for_class / isa95_build_mapping.classify_domain)
#
# Both functions score a free-text definition against each PartClass domain by
# counting case-insensitive substring keyword hits (see domain_score() in each
# module) and take the argmax domain, subject to a MIN_SCORE floor:
#
#     Score(text, domain) = sum(1 for kw in DOMAIN_KEYWORDS[domain] if kw.lower() in text.lower())
#
# There is no weighting by phrase length, no n-gram extraction, and no
# normalisation by lexicon size. MIN_SCORE differs between the two sources
# (ECLASS = 2, ISA-95 = 1), and ties are broken by DOMAIN_KEYWORDS dict
# insertion order, not by any principled rule.
#
# The 64 labelled examples below are independent of the ECLASS/ISA-95 corpora
# the keyword lists were tuned against — real component definitions pulled
# from Wikipedia, Britannica, IBM/Fortinet glossaries and engineering
# reference sites (a handful marked STANDARD REF use uncontested
# textbook-style phrasing where a live citation wasn't retrievable). This is
# what actually answers "does the classifier generalise", as opposed to
# testing it against the same text it was tuned on.
# =============================================================================

LABELLED_COMPONENTS: List[Tuple[str, str, str]] = [
    # --- PowerConversion ---
    ("Power Supply Unit", "A device that converts alternating current from the electricity grid to direct current for hardware, typically consisting of a transformer and a rectifier.", "PowerConversion"),
    ("Rectifier Module", "A component that converts AC power from the grid into DC power and uses it to charge batteries.", "PowerConversion"),
    ("Grid-Tie Inverter", "A device that converts DC link voltage into an AC output with tight control on tolerance for critical load applications.", "PowerConversion"),
    ("Uninterruptible Power Supply", "A system used to provide continuous power to critical applications like hospital operating theatres and computer installations in case of mains power failure, consisting of a static rectifier, a static inverter, a static switch and an energy storage system.", "PowerConversion"),
    ("Step Voltage Regulator", "A step type device used to maintain a relatively constant voltage level in a power distribution system, protecting equipment such as air conditioners and motors from large voltage variations.", "PowerConversion"),

    # --- EnergyStorage ---
    ("Lithium Battery Pack", "Stores energy electrochemically, through chemical reactions that convert chemical energy into electrical energy.", "EnergyStorage"),
    ("Electrolytic Capacitor", "A device that stores electrical energy in an electrostatic field between two conducting plates separated by a dielectric material.", "EnergyStorage"),
    ("Supercapacitor Module", "A high-capacity capacitor with a capacitance value much higher than solid-state capacitors but with lower voltage limits, bridging the gap between electrolytic capacitors and rechargeable batteries.", "EnergyStorage"),
    ("Ultracapacitor Bank", "An energy storage device that occupies a distinct position between conventional capacitors and lithium-ion batteries.", "EnergyStorage"),

    # --- Actuator ---
    ("Generic Actuator", "A component of a machine that is responsible for moving and controlling a mechanism or system, for example by opening a valve.", "Actuator"),
    ("Precision Servo Motor", "A rotary or linear actuator that allows precise control of angular or linear position, velocity, and acceleration in a mechanical system, consisting of a motor coupled to a sensor and a controller.", "Actuator"),
    ("Linear Actuator", "An actuator that creates linear motion in a straight line, in contrast to the circular motion of a conventional electric motor, used in machine tools and industrial machinery.", "Actuator"),
    ("Pneumatic Valve Actuator", "A device that controls valve operations using various actuation methods including electric, hydraulic, pneumatic, or manual.", "Actuator"),

    # --- Sensor ---
    ("Industrial Pressure Sensor", "An electro-mechanical device that detects forces per unit area in gases or liquids and provides signals to the inputs of control and display devices.", "Sensor"),
    ("RTD Temperature Sensor", "An electronic device that detects thermal parameters and provides signals to the inputs of control and display devices.", "Sensor"),
    ("Inductive Proximity Sensor", "An electronic device used to detect the presence of nearby objects through non-contacting means.", "Sensor"),
    ("Vortex Flow Meter", "A device designed to measure the rate of flow of mass and volume for liquids or gases, with main components including the sensor, signal processor and transmitter.", "Sensor"),
    ("Piezoelectric Vibration Sensor", "An instrument arranged to detect vibration and convert it into an electric signal corresponding to the quantitative measurement for process monitoring.", "Sensor"),

    # --- ControlUnit ---
    ("Programmable Logic Controller", "An industrial computer that has been ruggedized and adapted for the control of manufacturing processes such as assembly lines, machines and robotic devices, requiring high reliability and ease of programming.", "ControlUnit"),
    ("Engine Control Unit", "STANDARD REF: An embedded electronic control unit that manages the operation of an internal-combustion engine by processing sensor inputs and driving actuator outputs through onboard control logic.", "ControlUnit"),
    ("Motion Controller Board", "STANDARD REF: A dedicated control system module that executes closed-loop control algorithms to regulate the position, velocity, or torque of connected drives.", "ControlUnit"),
    ("Building Automation Controller", "STANDARD REF: A control device that runs supervisory logic to coordinate HVAC, lighting, and safety subsystems within a facility.", "ControlUnit"),

    # --- UserInterface ---
    ("Industrial HMI Panel", "A user-friendly interface enabling interaction between humans and machines for monitoring, control, and operations, typically provided as a touchscreen display or physical control panel.", "UserInterface"),
    ("Operator Touchscreen", "STANDARD REF: A graphical touchscreen device mounted on industrial equipment that lets an operator monitor process parameters and issue control commands.", "UserInterface"),
    ("Alarm Annunciator Panel", "STANDARD REF: A panel of indicator lights and audible alarms that presents plant status and fault conditions to an operator.", "UserInterface"),
    ("Keypad Control Station", "STANDARD REF: A physical keypad and indicator assembly used by an operator to enter commands and view basic status information.", "UserInterface"),

    # --- Thermal ---
    ("Plate Heat Exchanger", "A system used to transfer heat between a source and a working fluid, used in both cooling and heating processes, with fluids separated by a solid wall to prevent mixing.", "Thermal"),
    ("Engine Radiator", "A heat exchanger used to transfer thermal energy from one medium to another for the purpose of cooling and heating, commonly constructed to function in cars, buildings, and electronics.", "Thermal"),
    ("Industrial Furnace", "STANDARD REF: A heating device that generates and contains high-temperature heat for processes such as melting, curing, or heat treatment.", "Thermal"),
    ("Enclosure Cooling Fan", "STANDARD REF: A fan mounted in an equipment enclosure that circulates air to remove heat generated by internal components.", "Thermal"),
    ("Cabinet Heater", "STANDARD REF: A compact resistive heater used to prevent condensation and maintain a minimum temperature inside an electrical cabinet.", "Thermal"),

    # --- Fluidics ---
    ("Hydraulic Piston Pump", "Driven by an electric motor, the pump draws hydraulic fluid from the reservoir and pressurizes it, creating the flow necessary to power the system.", "Fluidics"),
    ("Rotary Screw Compressor", "A self-contained system in which compressed air is generated as the source, and the compressed air is directed through pneumatic control valves.", "Fluidics"),
    ("Pneumatic Control Valve", "Used for accurately controlling the rate of movement and the direction of movement of fluid actuators and for pressure control.", "Fluidics"),
    ("Centrifugal Water Pump", "STANDARD REF: A pump that uses a rotating impeller to move fluid by converting rotational kinetic energy into hydrodynamic energy.", "Fluidics"),

    # --- Structural ---
    ("Vehicle Chassis", "The load-bearing framework of a manufactured object, which structurally supports the object in its construction and function; an example is a vehicle frame, the underpart of a motor vehicle on which the body is mounted.", "Structural"),
    ("Equipment Enclosure", "STANDARD REF: A protective housing that encloses electrical or mechanical equipment and shields it from the surrounding environment.", "Structural"),
    ("Mounting Bracket", "STANDARD REF: A structural support fitting used to attach a component to a frame, wall, or chassis.", "Structural"),
    ("Machine Base Frame", "STANDARD REF: A rigid structural frame that supports and aligns the working components of a machine.", "Structural"),

    # --- Transmission ---
    ("Vehicle Drive Shaft", "A component for transmitting mechanical power, torque, and rotation, usually used to connect other components of a drivetrain that cannot be connected directly because of distance or the need to allow for relative movement between them.", "Transmission"),
    ("Jaw Shaft Coupling", "Used to connect two shaft ends together to transmit both angular rotation and torque.", "Transmission"),
    ("Planetary Gearbox", "STANDARD REF: A mechanical transmission device that uses a system of gears to change the speed, torque, and direction of rotational motion between an input and output shaft.", "Transmission"),
    ("Roller Bearing", "STANDARD REF: A mechanical component that supports a rotating shaft and reduces friction between moving parts.", "Transmission"),

    # --- Protection ---
    ("Miniature Circuit Breaker", "An electrical safety device designed to protect an electrical circuit from damage caused by overcurrent, with its basic function being to interrupt current flow to protect equipment and prevent fire.", "Protection"),
    ("Surge Protection Device", "A device intended to protect electrical devices in alternating current circuits from voltage spikes with very short duration, which can arise from causes including lightning strikes.", "Protection"),
    ("Cartridge Fuse", "STANDARD REF: A one-time overcurrent protection device that melts an internal element to interrupt current when it exceeds a rated threshold.", "Protection"),
    ("Machine Safety Interlock", "STANDARD REF: A protective device that prevents hazardous machine operation unless a guard or access door is confirmed closed.", "Protection"),

    # --- Connectivity ---
    ("M12 Electrical Connector", "Simplifies linking equipment to network segments, enabling secure electrical and data connections between devices.", "Connectivity"),
    ("DIN Rail Terminal Block", "Commonly used to connect two or more conductors while maintaining clean wire routing and efficient current distribution.", "Connectivity"),
    ("Foundation Fieldbus Cable", "A serial communications network cable used to provide robust distributed control connectivity in process control environments.", "Connectivity"),
    ("Industrial Ethernet Switch", "STANDARD REF: A networking device that connects multiple devices on an industrial network segment and directs data traffic between them.", "Connectivity"),

    # --- SoftwareModule ---
    ("Device Firmware Image", "Software that provides low-level control of computing device hardware; for a relatively simple device, firmware may perform all control, monitoring and data manipulation functionality.", "SoftwareModule"),
    ("Embedded Control Application", "STANDARD REF: A software application compiled to run on an embedded microcontroller to implement a device's control logic.", "SoftwareModule"),
    ("PLC Ladder Logic Program", "STANDARD REF: A software program written in ladder logic that executes on a programmable controller to sequence machine operations.", "SoftwareModule"),
    ("Diagnostic Firmware Patch", "STANDARD REF: A firmware update package that corrects a defect or adds a diagnostic capability to a device's onboard software.", "SoftwareModule"),

    # --- Consumable ---
    ("Rubber Gasket", "A mechanical seal used to fill the space between two mating surfaces to prevent leakage of fluids or gases, typically made from materials like rubber, cork, or metal.", "Consumable"),
    ("Silicone Sealant", "A substance, often adhesive-based, applied to surfaces to prevent the passage of fluids, filling gaps as a continuous layer.", "Consumable"),
    ("Hydraulic Oil Filter Cartridge", "A consumable machine component whose primary jobs are to remove particles from the oil and protect sensitive machine components from contaminant invasion.", "Consumable"),
    ("Industrial Grease Cartridge", "STANDARD REF: A lubricant consumable used to reduce friction and wear between moving mechanical parts, replaced on a scheduled interval.", "Consumable"),

    # --- Fastener ---
    ("Generic Fastener", "A general term for a piece of hardware, often made of a metal such as steel, used to mechanically join together two components.", "Fastener"),
    ("Machine Screw", "An externally threaded fastener.", "Fastener"),
    ("Hex Head Bolt", "A mechanical fastener that is usually used with a nut for connecting two or more parts.", "Fastener"),
    ("Blind Rivet", "A permanent mechanical fastener.", "Fastener"),
    ("Flat Washer", "A thin plate, typically disk-shaped, with a hole in the middle that is normally used to distribute the load of a threaded fastener, such as a bolt or nut.", "Fastener"),
]

# Deliberately adversarial / boundary cases, each documenting one specific,
# reproducible behaviour of the heuristic rather than "correctness" per se.
ADVERSARIAL_CASES = [
    ("Payroll Attendance Form",
     "An administrative form used to record employee attendance for payroll purposes.",
     None, None),  # (expected ECLASS result, expected ISA-95 result)
    ("Generic Actuator Unit",
     "A generic mechanical actuator unit.",
     None, "Actuator"),
    ("Lot Quality Inspection Report",
     "Quality inspection report for the completed production lot, verifying the test sample results meet specification.",
     None, "Sensor"),
]


def _score_dict(text: str, keywords: Dict[str, List[str]], scorer: Callable[[str, str], int]) -> Dict[str, int]:
    return {d: scorer(text, d) for d in keywords if scorer(text, d) > 0}


def _evaluate(
    labelled: List[Tuple[str, str, str]],
    classify_fn: Callable[[str], Optional[str]],
) -> Dict[str, object]:
    """
    Run classify_fn over every labelled example and compute overall accuracy
    plus per-class precision/recall (treating each domain as the positive
    class in a one-vs-rest confusion count).
    """
    tp: Dict[str, int] = defaultdict(int)
    fp: Dict[str, int] = defaultdict(int)
    fn: Dict[str, int] = defaultdict(int)
    correct = 0
    mismatches: List[Tuple[str, str, Optional[str]]] = []

    for name, desc, truth in labelled:
        pred = classify_fn(desc)
        if pred == truth:
            correct += 1
            tp[truth] += 1
        else:
            mismatches.append((name, truth, pred))
            fn[truth] += 1
            if pred is not None:
                fp[pred] += 1

    classes = sorted({truth for _, _, truth in labelled})
    per_class = {}
    for c in classes:
        precision = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) > 0 else None
        recall = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) > 0 else None
        per_class[c] = {"precision": precision, "recall": recall, "tp": tp[c], "fp": fp[c], "fn": fn[c]}

    return {
        "accuracy": correct / len(labelled),
        "correct": correct,
        "total": len(labelled),
        "mismatches": mismatches,
        "per_class": per_class,
    }


@pytest.fixture(scope="module")
def eclass_results():
    return _evaluate(LABELLED_COMPONENTS, classify_domain_for_class)


@pytest.fixture(scope="module")
def isa95_results():
    return _evaluate(LABELLED_COMPONENTS, isa95_classify_domain)


# =============================================================================
# Sanity checks on the labelled corpus itself
# =============================================================================

def test_labelled_corpus_size_and_coverage():
    """The labelled set covers every PartClass domain with at least 4 examples."""
    assert len(LABELLED_COMPONENTS) >= 60
    counts: Dict[str, int] = defaultdict(int)
    for _, _, truth in LABELLED_COMPONENTS:
        counts[truth] += 1
    all_domains = set(ECLASS_DOMAIN_KEYWORDS.keys())
    assert set(counts.keys()) == all_domains, (
        f"Labelled corpus missing domains: {all_domains - set(counts.keys())}"
    )
    assert min(counts.values()) >= 4, f"Some domain has fewer than 4 labelled examples: {counts}"


# =============================================================================
# Empirical accuracy on independent, real-world component descriptions
# =============================================================================

def test_eclass_classifier_accuracy_on_independent_data(eclass_results):
    """
    ECLASS's classify_domain_for_class(), evaluated against 64 real component
    definitions independent of the ECLASS ontology corpus it was tuned on.

    Observed accuracy is 21/64 = 0.328 (32.8%), overwhelmingly due to
    MIN_SCORE=2 rejecting real-world phrasing that doesn't hit two of
    ECLASS's specific multi-word keyword phrases. This is the empirical
    generalisation result referenced in the paper: strong precision on
    class-internal validation does not imply strong recall on independent text.
    """
    acc = eclass_results["accuracy"]
    assert acc >= 0.25, (
        f"ECLASS classifier accuracy {acc:.3f} regressed below observed floor 0.25. "
        f"Mismatches: {eclass_results['mismatches']}"
    )


def test_isa95_classifier_accuracy_on_independent_data(isa95_results):
    """
    ISA-95's classify_domain(), evaluated against the same 64 independent
    component definitions. Observed accuracy is 38/64 = 0.594 (59.4%) --
    substantially higher than ECLASS's, driven by MIN_SCORE=1 (vs 2) and a
    broader, more generic keyword list, at the cost of more false positives
    (see test_isa95_generic_keywords_produce_false_positive below).
    """
    acc = isa95_results["accuracy"]
    assert acc >= 0.45, (
        f"ISA-95 classifier accuracy {acc:.3f} regressed below observed floor 0.45. "
        f"Mismatches: {isa95_results['mismatches']}"
    )


# =============================================================================
# Documented, reproducible adversarial behaviours
# =============================================================================

def test_true_negative_returns_none_for_both_classifiers():
    """Text with zero keyword overlap must not be force-classified into any domain."""
    _, desc, expected_eclass, expected_isa95 = ADVERSARIAL_CASES[0]
    assert classify_domain_for_class(desc) == expected_eclass
    assert isa95_classify_domain(desc) == expected_isa95


def test_min_score_threshold_disagreement_between_sources():
    """
    A single-keyword-hit definition is rejected by ECLASS (MIN_SCORE=2) but
    accepted by ISA-95 (MIN_SCORE=1) for the identical input -- direct
    evidence that the accept/reject threshold is not held constant across
    the two lexicon sources.
    """
    _, desc, expected_eclass, expected_isa95 = ADVERSARIAL_CASES[1]
    assert eclass_domain_score(desc, "Actuator") == 1
    assert isa95_domain_score(desc, "Actuator") == 1
    assert classify_domain_for_class(desc) == expected_eclass
    assert isa95_classify_domain(desc) == expected_isa95


def test_eclass_tie_break_is_domain_keywords_insertion_order():
    """
    Two domains tied at the same score are resolved by DOMAIN_KEYWORDS dict
    insertion order (via max(scores, key=scores.get)), not by any semantic
    tie-break rule such as matched-phrase length.
    """
    desc = (
        "A combined transformer and heat exchanger unit used for converting "
        "power supply lines and cooling equipment."
    )
    scores = _score_dict(desc, ECLASS_DOMAIN_KEYWORDS, eclass_domain_score)
    assert scores["PowerConversion"] == scores["Thermal"] == 2, (
        f"Expected a genuine tie between PowerConversion and Thermal, got {scores}"
    )
    domain_order = list(ECLASS_DOMAIN_KEYWORDS.keys())
    assert domain_order.index("PowerConversion") < domain_order.index("Thermal")
    assert classify_domain_for_class(desc) == "PowerConversion"


def test_isa95_generic_keywords_produce_false_positive():
    """
    ISA-95's broader, more generic keyword list (bare "quality", "test",
    "sample", "result") misclassifies a non-component quality-inspection
    report as a Sensor. ECLASS's narrower, more technical keyword list does
    not exhibit this false positive on the same input.
    """
    _, desc, expected_eclass, expected_isa95 = ADVERSARIAL_CASES[2]
    assert classify_domain_for_class(desc) == expected_eclass
    assert isa95_classify_domain(desc) == expected_isa95
    isa95_scores = _score_dict(desc, ISA95_DOMAIN_KEYWORDS, isa95_domain_score)
    assert isa95_scores.get("Sensor", 0) >= 4


# =============================================================================
# Summary report
# =============================================================================

def test_domain_classifier_validation_report(eclass_results, isa95_results):
    """
    Print a precision/recall-per-class report for both classifiers against
    the independent labelled corpus.

    Run with -v -s to see the full report:
        pytest -v -s tests/test_part_class.py::test_domain_classifier_validation_report
    """
    sep, sep2 = "=" * 78, "-" * 78

    print(f"\n\n{sep}")
    print("  Domain-Classification Heuristic vs Independent Labelled Corpus")
    print(f"  (n={len(LABELLED_COMPONENTS)} real component definitions, 15 PartClass domains)")
    print(sep)
    print(f"  ECLASS  (MIN_SCORE={ECLASS_MIN_SCORE}): accuracy "
          f"{eclass_results['correct']}/{eclass_results['total']} = {eclass_results['accuracy']:.3f}")
    print(f"  ISA-95  (MIN_SCORE={ISA95_MIN_SCORE}): accuracy "
          f"{isa95_results['correct']}/{isa95_results['total']} = {isa95_results['accuracy']:.3f}")
    print(sep2)
    print(f"  {'Domain':<16} {'ECLASS P':>9} {'ECLASS R':>9} {'ISA95 P':>9} {'ISA95 R':>9}")
    print(sep2)

    def _fmt(v):
        return f"{v:.3f}" if v is not None else "  N/A  "

    for domain in sorted(ECLASS_DOMAIN_KEYWORDS.keys()):
        e = eclass_results["per_class"].get(domain, {"precision": None, "recall": None})
        i = isa95_results["per_class"].get(domain, {"precision": None, "recall": None})
        print(f"  {domain:<16} {_fmt(e['precision']):>9} {_fmt(e['recall']):>9} "
              f"{_fmt(i['precision']):>9} {_fmt(i['recall']):>9}")

    print(sep2)
    print("\n  Notable ECLASS mismatches (mostly MIN_SCORE=2 rejecting valid components as None):")
    for name, truth, pred in eclass_results["mismatches"][:8]:
        print(f"    {name!r}: truth={truth} pred={pred}")

    print("\n  Notable ISA-95 mismatches (mostly cross-domain confusion from generic keywords):")
    for name, truth, pred in isa95_results["mismatches"][:8]:
        print(f"    {name!r}: truth={truth} pred={pred}")

    print(f"\n{sep}\n")

