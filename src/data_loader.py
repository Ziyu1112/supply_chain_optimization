from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def load_input_data(data_dir: Path = DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all input CSV files used by the optimization model."""
    warehouses = pd.read_csv(data_dir / "warehouses.csv")
    regions = pd.read_csv(data_dir / "regions.csv")
    transport_costs = pd.read_csv(data_dir / "transport_costs.csv")
    scenarios = pd.read_csv(data_dir / "scenarios.csv").fillna("")

    validate_input_data(warehouses, regions, transport_costs)
    return warehouses, regions, transport_costs, scenarios


def validate_input_data(
    warehouses: pd.DataFrame,
    regions: pd.DataFrame,
    transport_costs: pd.DataFrame,
) -> None:
    """Validate that every warehouse-region route exists exactly once."""
    required_warehouse_cols = {"warehouse", "capacity", "latitude", "longitude"}
    required_region_cols = {"region", "demand", "latitude", "longitude"}
    required_cost_cols = {"from_warehouse", "to_region", "cost_per_unit"}

    missing = required_warehouse_cols - set(warehouses.columns)
    if missing:
        raise ValueError(f"warehouses.csv is missing columns: {sorted(missing)}")

    missing = required_region_cols - set(regions.columns)
    if missing:
        raise ValueError(f"regions.csv is missing columns: {sorted(missing)}")

    if "unmet_penalty" not in regions.columns:
        regions["unmet_penalty"] = 100.0

    missing = required_cost_cols - set(transport_costs.columns)
    if missing:
        raise ValueError(f"transport_costs.csv is missing columns: {sorted(missing)}")

    expected_routes = set(
        (warehouse, region)
        for warehouse in warehouses["warehouse"]
        for region in regions["region"]
    )
    actual_routes = set(zip(transport_costs["from_warehouse"], transport_costs["to_region"]))

    missing_routes = expected_routes - actual_routes
    extra_routes = actual_routes - expected_routes

    if missing_routes:
        raise ValueError(f"transport_costs.csv is missing routes: {sorted(missing_routes)}")
    if extra_routes:
        raise ValueError(f"transport_costs.csv has unknown routes: {sorted(extra_routes)}")

    duplicated = transport_costs.duplicated(["from_warehouse", "to_region"])
    if duplicated.any():
        duplicate_rows = transport_costs.loc[duplicated, ["from_warehouse", "to_region"]]
        raise ValueError(f"transport_costs.csv has duplicate routes:\n{duplicate_rows}")
