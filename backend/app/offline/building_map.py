"""Map Satisfactory ``Build_..._C`` class names to display info + power.

Power figures are the game's nominal values at 100% clock (MW consumed for
machines/extractors, MW generated for generators). They are used only to
*estimate* a static save's grid load, so approximate averages are acceptable
for variable buildings (documented as estimates in the UI).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Category = Literal["production", "extraction", "generator", "power_storage", "logistics"]


@dataclass(frozen=True)
class BuildingSpec:
    """Display name, category, and nominal power for one building class."""

    name: str
    category: Category
    power_mw: float


# Curated catalog of the classes this app reasons about. Unlisted buildings
# (foundations, belts, walls, …) are ignored for machine/power rollups.
_SPECS: dict[str, BuildingSpec] = {
    # Production machines (power_mw = consumption at 100%).
    "Build_SmelterMk1_C": BuildingSpec("Smelter", "production", 4.0),
    "Build_FoundryMk1_C": BuildingSpec("Foundry", "production", 16.0),
    "Build_ConstructorMk1_C": BuildingSpec("Constructor", "production", 4.0),
    "Build_AssemblerMk1_C": BuildingSpec("Assembler", "production", 15.0),
    "Build_ManufacturerMk1_C": BuildingSpec("Manufacturer", "production", 55.0),
    "Build_OilRefinery_C": BuildingSpec("Refinery", "production", 30.0),
    "Build_Packager_C": BuildingSpec("Packager", "production", 10.0),
    "Build_Blender_C": BuildingSpec("Blender", "production", 75.0),
    "Build_HadronCollider_C": BuildingSpec("Particle Accelerator", "production", 500.0),
    "Build_Converter_C": BuildingSpec("Converter", "production", 250.0),
    "Build_QuantumEncoder_C": BuildingSpec("Quantum Encoder", "production", 1000.0),
    # Resource extractors (also counted as machines).
    "Build_MinerMk1_C": BuildingSpec("Miner Mk.1", "extraction", 5.0),
    "Build_MinerMk2_C": BuildingSpec("Miner Mk.2", "extraction", 12.0),
    "Build_MinerMk3_C": BuildingSpec("Miner Mk.3", "extraction", 30.0),
    "Build_OilPump_C": BuildingSpec("Oil Extractor", "extraction", 40.0),
    "Build_WaterPump_C": BuildingSpec("Water Extractor", "extraction", 20.0),
    "Build_FrackingExtractor_C": BuildingSpec("Resource Well Extractor", "extraction", 15.0),
    # Power generators (power_mw = generation at 100%).
    "Build_GeneratorBiomass_C": BuildingSpec("Biomass Burner", "generator", 30.0),
    "Build_GeneratorBiomass_Automated_C": BuildingSpec("Biomass Burner", "generator", 30.0),
    "Build_GeneratorCoal_C": BuildingSpec("Coal-Powered Generator", "generator", 75.0),
    "Build_GeneratorFuel_C": BuildingSpec("Fuel-Powered Generator", "generator", 250.0),
    "Build_GeneratorNuclear_C": BuildingSpec("Nuclear Power Plant", "generator", 2500.0),
    "Build_GeneratorGeoThermal_C": BuildingSpec("Geothermal Generator", "generator", 200.0),
    # Power storage (nominal 100 MWh capacity each).
    "Build_PowerStorageMk1_C": BuildingSpec("Power Storage", "power_storage", 100.0),
    # Logistics stations.
    "Build_TrainStation_C": BuildingSpec("Train Station", "logistics", 0.0),
    "Build_DroneStation_C": BuildingSpec("Drone Port", "logistics", 0.0),
    "Build_TruckStation_C": BuildingSpec("Truck Station", "logistics", 0.0),
}


def lookup(class_name: str) -> BuildingSpec | None:
    """Return the spec for a ``Build_..._C`` class, or ``None`` if uncatalogued."""
    return _SPECS.get(class_name)
