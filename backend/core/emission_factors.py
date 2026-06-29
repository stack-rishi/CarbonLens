import csv
import os
from typing import Any

# Path to the CSV file
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emission_factors.csv")

# Global cache
# Structure: {(category, item): (value, unit)}
_FACTORS_CACHE: dict[tuple[str, str], tuple[float, str]] = {}


def load_emission_factors() -> None:
    """Load emission factors from CSV into the global cache."""
    if _FACTORS_CACHE:
        return

    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Emission factors CSV not found at {CSV_PATH}")

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row["category"]
            item = row["item"]
            value = float(row["value"])
            unit = row["unit"]
            _FACTORS_CACHE[(category, item)] = (value, unit)


def get_factor(category: str, item: str) -> float:
    """Get the emission factor value for a category and item. Defaults to 1.0 if not found."""
    load_emission_factors()
    factor_info = _FACTORS_CACHE.get((category, item))
    if factor_info:
        return factor_info[0]
    return 1.0


def get_factor_with_unit(category: str, item: str) -> tuple[float, str]:
    """Get the emission factor value and unit. Defaults to (1.0, 'kg CO2e/unit') if not found."""
    load_emission_factors()
    factor_info = _FACTORS_CACHE.get((category, item))
    if factor_info:
        return factor_info
    return 1.0, "kg CO2e/unit"


def get_all_factors() -> dict[str, dict[str, dict[str, Any]]]:
    """Return all cached emission factors structured by category."""
    load_emission_factors()
    structured: dict[str, dict[str, dict[str, Any]]] = {}
    for (category, item), (value, unit) in _FACTORS_CACHE.items():
        if category not in structured:
            structured[category] = {}
        structured[category][item] = {"value": value, "unit": unit}
    return structured
