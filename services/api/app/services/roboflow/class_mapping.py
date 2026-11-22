from typing import Dict, Optional

# Standardized GramaSeva Civic Categories
CIVIC_CATEGORIES = {
    "garbage": "Garbage Dump & Waste",
    "road_damage": "Road Damage & Potholes",
    "drainage": "Drainage & Waterlogging",
    "water_leak": "Water Supply & Pipeline Leak",
    "streetlight": "Streetlight & Electrical",
    "public_facility": "Public Infrastructure & Buildings",
    "other": "Other Civic Issue",
}

# Explicit class normalization mapping
# Strictly prevents garbage dumps from being mapped to road damage or vice versa.
RAW_CLASS_MAPPING: Dict[str, str] = {
    # 1. Garbage & Solid Waste (Model 1 & Civic models)
    "garbage": "garbage",
    "garbage_dump": "garbage",
    "garbage-dump": "garbage",
    "trash": "garbage",
    "waste": "garbage",
    "litter": "garbage",
    "rubbish": "garbage",
    "debris": "garbage",
    "solid_waste": "garbage",
    "plastic_waste": "garbage",
    "dumpster": "garbage",
    "waste_heap": "garbage",
    "garbage_pile": "garbage",
    "littering": "garbage",

    # 2. Road Damage & Potholes (Model 2 & Civic models)
    "pothole": "road_damage",
    "potholes": "road_damage",
    "pot_hole": "road_damage",
    "road_damage": "road_damage",
    "damaged_road": "road_damage",
    "broken_road": "road_damage",
    "crack": "road_damage",
    "cracks": "road_damage",
    "road_crack": "road_damage",
    "alligator_crack": "road_damage",
    "asphalt_damage": "road_damage",
    "rutting": "road_damage",
    "manhole_damage": "road_damage",
    # Japanese RDD standard codes frequently used in Roboflow road datasets:
    "d00": "road_damage",  # Longitudinal crack
    "d10": "road_damage",  # Transverse crack
    "d20": "road_damage",  # Alligator/fatigue crack
    "d40": "road_damage",  # Pothole
    "d43": "road_damage",  # Crosswalk blur
    "d44": "road_damage",  # White line blur

    # 3. Waterlogging & Flooding & Drainage (Model 3 & Civic models)
    "waterlogging": "drainage",
    "water-logging": "drainage",
    "water_logging": "drainage",
    "standing_water": "drainage",
    "stagnant_water": "drainage",
    "flooded_road": "drainage",
    "flooding": "drainage",
    "water_accumulation": "drainage",
    "open_drain": "drainage",
    "clogged_drain": "drainage",
    "blocked_drain": "drainage",
    "overflowing_drain": "drainage",
    "drain": "drainage",
    "drainage": "drainage",
    "sewer": "drainage",
    "sewage": "drainage",
    "manhole": "drainage",

    # 4. Water Supply & Pipeline Leaks
    "water_leak": "water_leak",
    "leak": "water_leak",
    "pipeline_leak": "water_leak",
    "pipe_burst": "water_leak",
    "broken_pipe": "water_leak",
    "burst_pipe": "water_leak",

    # 5. Streetlight & Electrical Hazards
    "streetlight": "streetlight",
    "street_light": "streetlight",
    "broken_streetlight": "streetlight",
    "broken_pole": "streetlight",
    "electric_pole": "streetlight",
    "exposed_wires": "streetlight",
    "damaged_pole": "streetlight",

    # 6. Public Infrastructure & Facilities
    "public_facility": "public_facility",
    "broken_bench": "public_facility",
    "damaged_wall": "public_facility",
    "damaged_signboard": "public_facility",
    "damaged_bus_shelter": "public_facility",
}

def normalize_detected_class(raw_label: str) -> str:
    """
    Normalizes raw detection class name from Roboflow models to standard categories.
    Preserves unknown classes as 'other' instead of arbitrarily defaulting to road damage or garbage.
    """
    if not raw_label:
        return "other"

    clean_key = raw_label.strip().lower().replace(" ", "_").replace("-", "_")
    if clean_key in RAW_CLASS_MAPPING:
        return RAW_CLASS_MAPPING[clean_key]

    # Partial substring matching
    for key, mapped_category in RAW_CLASS_MAPPING.items():
        if key in clean_key:
            return mapped_category

    return "other"
