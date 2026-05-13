import pandas as pd

from src.optimizer import OptimizationResult, solve_distribution_model


def apply_scenario(
    warehouses: pd.DataFrame,
    regions: pd.DataFrame,
    transport_costs: pd.DataFrame,
    scenario: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return scenario-adjusted copies of the input data."""
    adjusted_warehouses = warehouses.copy()
    adjusted_regions = regions.copy()
    adjusted_costs = transport_costs.copy()

    cost_multiplier = float(scenario.get("cost_multiplier", 1.0) or 1.0)
    adjusted_costs["cost_per_unit"] = adjusted_costs["cost_per_unit"] * cost_multiplier

    closed_warehouse = scenario.get("closed_warehouse", "")
    if closed_warehouse:
        adjusted_warehouses.loc[
            adjusted_warehouses["warehouse"] == closed_warehouse,
            "capacity",
        ] = 0

    capacity_warehouse = scenario.get("capacity_warehouse", "")
    capacity_multiplier = float(scenario.get("capacity_multiplier", 1.0) or 1.0)
    if capacity_warehouse:
        adjusted_warehouses.loc[
            adjusted_warehouses["warehouse"] == capacity_warehouse,
            "capacity",
        ] *= capacity_multiplier

    demand_region = scenario.get("demand_region", "")
    demand_multiplier = float(scenario.get("demand_multiplier", 1.0) or 1.0)
    if demand_region:
        impacted_regions = [region.strip() for region in str(demand_region).split(";")]
        adjusted_regions.loc[
            adjusted_regions["region"].isin(impacted_regions),
            "demand",
        ] *= demand_multiplier

    return adjusted_warehouses, adjusted_regions, adjusted_costs


def run_scenarios(
    warehouses: pd.DataFrame,
    regions: pd.DataFrame,
    transport_costs: pd.DataFrame,
    scenarios: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Solve all configured scenarios and return summary, shipments, utilization, and shortages."""
    results: list[OptimizationResult] = []

    for _, scenario in scenarios.iterrows():
        scenario_name = scenario["scenario"]
        scenario_warehouses, scenario_regions, scenario_costs = apply_scenario(
            warehouses,
            regions,
            transport_costs,
            scenario,
        )
        result = solve_distribution_model(
            scenario_warehouses,
            scenario_regions,
            scenario_costs,
            scenario_name=scenario_name,
        )
        results.append(result)

    summary = pd.DataFrame(
        {
            "scenario": scenarios["scenario"],
            "description": scenarios["description"],
            "status": [result.status for result in results],
            "total_cost": [result.total_cost for result in results],
            "transportation_cost": [result.transportation_cost for result in results],
            "unmet_penalty_cost": [result.unmet_penalty_cost for result in results],
            "total_unmet_demand": [
                result.unmet_demand["unmet_quantity"].sum()
                if not result.unmet_demand.empty
                else 0.0
                for result in results
            ],
        }
    )

    if not summary.empty and summary.loc[0, "status"] == "Optimal":
        base_cost = summary.loc[0, "total_cost"]
        summary["cost_change_vs_base"] = summary["total_cost"] - base_cost
        summary["cost_change_pct_vs_base"] = summary["cost_change_vs_base"] / base_cost
    else:
        summary["cost_change_vs_base"] = pd.NA
        summary["cost_change_pct_vs_base"] = pd.NA

    shipments = pd.concat(
        [result.shipments for result in results if not result.shipments.empty],
        ignore_index=True,
    )
    utilization = pd.concat(
        [
            result.warehouse_summary.assign(scenario=scenarios.loc[index, "scenario"])
            for index, result in enumerate(results)
        ],
        ignore_index=True,
    )
    unmet_demand = pd.concat(
        [result.unmet_demand for result in results if not result.unmet_demand.empty],
        ignore_index=True,
    )

    return summary, shipments, utilization, unmet_demand
