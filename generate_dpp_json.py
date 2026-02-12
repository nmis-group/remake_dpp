import json
from usage_test import generate_coffee_machine_parts, create_coffee_machine_dpp
from nmis_dpp.utils import to_dict

parts = generate_coffee_machine_parts()
dpp = create_coffee_machine_dpp(parts)
with open("coffee_machine.json", "w") as f:
    json.dump(to_dict(dpp), f, indent=2, default=str)
print("coffee_machine.json created")
