"""Constants for the Mopeka Standard Check integration."""

DOMAIN = "mopeka_std"

CONF_TANK_TYPE = "tank_type"

# Tank presets: key -> (empty_mm, full_mm). Level % is linear between the
# empty and full liquid-column heights. Values match the Mopeka app / ESPHome.
TANK_TYPES: dict[str, tuple[float, float]] = {
    "20lb_vertical": (38, 254),
    "30lb_vertical": (38, 381),
    "40lb_vertical": (38, 508),
    "europe_6kg": (38, 336),
    "europe_11kg": (38, 366),
    "europe_14kg": (38, 467),
    "custom": (0, 100),
}

# Human-readable labels for the config dropdown (value stored = key).
TANK_TYPE_LABELS: dict[str, str] = {
    "20lb_vertical": "20 lb vertical (US)",
    "30lb_vertical": "30 lb vertical (US)",
    "40lb_vertical": "40 lb vertical (US)",
    "europe_6kg": "6 kg (Europe)",
    "europe_11kg": "11 kg (Europe)",
    "europe_14kg": "14 kg (Europe)",
    "custom": "Custom (0-100 mm)",
}

DEFAULT_TANK_TYPE = "20lb_vertical"
