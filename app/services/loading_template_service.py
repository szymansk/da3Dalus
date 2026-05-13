"""Loading Scenario Templates — default scenarios per aircraft class (gh-488).

Templates provide a sensible starting set of loading scenarios for each
aircraft class.  They are applied client-side (the user can customise or
discard them); they are not auto-created at aeroplane creation time.
"""
from __future__ import annotations

_EMPTY: dict = {
    "name": "Empty",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [],
    },
    "is_default": True,
}

_BATTERY_FWD: dict = {
    "name": "Battery Forward",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [
            {
                "name": "Battery (forward position)",
                "mass_kg": 0.2,
                "x_m": 0.05,
                "y_m": 0.0,
                "z_m": 0.0,
                "category": "payload",
            }
        ],
    },
    "is_default": False,
}

_BATTERY_AFT: dict = {
    "name": "Battery Aft",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [
            {
                "name": "Battery (aft position)",
                "mass_kg": 0.2,
                "x_m": 0.25,
                "y_m": 0.0,
                "z_m": 0.0,
                "category": "payload",
            }
        ],
    },
    "is_default": False,
}

_WITH_PAYLOAD: dict = {
    "name": "With Payload",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [
            {
                "name": "Mission Payload",
                "mass_kg": 0.3,
                "x_m": 0.15,
                "y_m": 0.0,
                "z_m": 0.0,
                "category": "payload",
            }
        ],
    },
    "is_default": False,
}

_WITHOUT_PAYLOAD: dict = {
    "name": "Without Payload",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [],
    },
    "is_default": False,
}

_FUEL_FULL: dict = {
    "name": "Fuel Full",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [
            {
                "name": "Fuel (full)",
                "mass_kg": 0.5,
                "x_m": 0.15,
                "y_m": 0.0,
                "z_m": 0.0,
                "category": "fuel",
            }
        ],
    },
    "is_default": False,
}

_FUEL_HALF: dict = {
    "name": "Fuel Half",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [
            {
                "name": "Fuel (half)",
                "mass_kg": 0.25,
                "x_m": 0.15,
                "y_m": 0.0,
                "z_m": 0.0,
                "category": "fuel",
            }
        ],
    },
    "is_default": False,
}

_FUEL_EMPTY: dict = {
    "name": "Fuel Empty",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [],
    },
    "is_default": False,
}

_MISSION_PAYLOAD_INSTALLED: dict = {
    "name": "Mission Payload Installed",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [
            {
                "name": "Survey Camera",
                "mass_kg": 0.4,
                "x_m": 0.10,
                "y_m": 0.0,
                "z_m": -0.05,
                "category": "payload",
            }
        ],
    },
    "is_default": False,
}

_MISSION_PAYLOAD_REMOVED: dict = {
    "name": "Mission Payload Removed",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [],
    },
    "is_default": False,
}

_DROP_PRE: dict = {
    "name": "Drop — Pre Release",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [
            {
                "name": "Drop Item",
                "mass_kg": 0.3,
                "x_m": 0.15,
                "y_m": 0.0,
                "z_m": 0.0,
                "category": "payload",
            }
        ],
    },
    "is_default": False,
}

_DROP_POST: dict = {
    "name": "Drop — Post Release",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [],
    },
    "is_default": False,
}

_BALLAST_FULL: dict = {
    "name": "Ballast Full",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [
            {
                "name": "Ballast (full)",
                "mass_kg": 0.5,
                "x_m": 0.20,
                "y_m": 0.0,
                "z_m": 0.0,
                "category": "ballast",
            }
        ],
    },
    "is_default": False,
}

_BALLAST_EMPTY: dict = {
    "name": "Ballast Empty",
    "component_overrides": {
        "toggles": [],
        "mass_overrides": [],
        "position_overrides": [],
        "adhoc_items": [],
    },
    "is_default": False,
}

# Templates per aircraft class
TEMPLATES: dict[str, list[dict]] = {
    "rc_trainer": [
        _EMPTY,
        _BATTERY_FWD,
        _BATTERY_AFT,
        _WITH_PAYLOAD,
        _WITHOUT_PAYLOAD,
    ],
    "rc_aerobatic": [
        _EMPTY,
        _BATTERY_FWD,
        _BATTERY_AFT,
    ],
    "rc_combust": [
        _EMPTY,
        _FUEL_EMPTY,
        _FUEL_HALF,
        _FUEL_FULL,
    ],
    "uav_survey": [
        _EMPTY,
        _MISSION_PAYLOAD_INSTALLED,
        _MISSION_PAYLOAD_REMOVED,
        _DROP_PRE,
        _DROP_POST,
    ],
    "glider": [
        _EMPTY,
        _BALLAST_EMPTY,
        _BALLAST_FULL,
    ],
    # Boxwing gets the rc_trainer set; SM tolerance band handled separately
    "boxwing": [
        _EMPTY,
        _BATTERY_FWD,
        _BATTERY_AFT,
        _WITH_PAYLOAD,
        _WITHOUT_PAYLOAD,
    ],
}


def get_templates_for_class(aircraft_class: str) -> list[dict]:
    """Return the default loading scenario templates for the given aircraft class.

    Falls back to rc_trainer templates for unknown classes.
    """
    return TEMPLATES.get(aircraft_class, TEMPLATES["rc_trainer"])
