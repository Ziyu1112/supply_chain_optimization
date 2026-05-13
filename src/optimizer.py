from dataclasses import dataclass

import pandas as pd
import pulp


@dataclass(frozen=True)
class OptimizationResult:
    status: str
    total_cost: float
    transportation_cost: float
    unmet_penalty_cost: float
    unmet_demand: pd.DataFrame
    shipments: pd.DataFrame
    warehouse_summary: pd.DataFrame


def solve_distribution_model(
    warehouses: pd.DataFrame,
    regions: pd.DataFrame,
    transport_costs: pd.DataFrame,
    scenario_name: str = "Base Case",
) -> OptimizationResult:
    """Solve the FMCG distribution transportation problem."""
    warehouse_names = warehouses["warehouse"].tolist()
    region_names = regions["region"].tolist()

    capacity = warehouses.set_index("warehouse")["capacity"].to_dict()
    demand = regions.set_index("region")["demand"].to_dict()
    unmet_penalty = regions.set_index("region")["unmet_penalty"].to_dict()
    cost = transport_costs.set_index(["from_warehouse", "to_region"])["cost_per_unit"].to_dict()

    problem = pulp.LpProblem(f"FMCG_Distribution_{scenario_name}", pulp.LpMinimize)

    shipment_vars = pulp.LpVariable.dicts(
        "ship",
        ((warehouse, region) for warehouse in warehouse_names for region in region_names),
        lowBound=0,
        cat="Continuous",
    )
    unmet_vars = pulp.LpVariable.dicts(
        "unmet",
        region_names,
        lowBound=0,
        cat="Continuous",
    )

    problem += pulp.lpSum(
        cost[(warehouse, region)] * shipment_vars[(warehouse, region)]
        for warehouse in warehouse_names
        for region in region_names
    ) + pulp.lpSum(
        unmet_penalty[region] * unmet_vars[region]
        for region in region_names
    )

    for region in region_names:
        problem += (
            pulp.lpSum(shipment_vars[(warehouse, region)] for warehouse in warehouse_names)
            + unmet_vars[region]
            == demand[region],
            f"Demand_{region}",
        )

    for warehouse in warehouse_names:
        problem += (
            pulp.lpSum(shipment_vars[(warehouse, region)] for region in region_names)
            <= capacity[warehouse],
            f"Capacity_{warehouse}",
        )

    problem.solve(pulp.PULP_CBC_CMD(msg=False))
    status = pulp.LpStatus[problem.status]

    if status != "Optimal":
        return OptimizationResult(
            status=status,
            total_cost=float("nan"),
            transportation_cost=float("nan"),
            unmet_penalty_cost=float("nan"),
            unmet_demand=pd.DataFrame(),
            shipments=pd.DataFrame(),
            warehouse_summary=_warehouse_summary(warehouses, pd.DataFrame()),
        )

    shipment_rows = []
    for warehouse in warehouse_names:
        for region in region_names:
            quantity = shipment_vars[(warehouse, region)].value()
            if quantity and quantity > 1e-6:
                unit_cost = cost[(warehouse, region)]
                shipment_rows.append(
                    {
                        "scenario": scenario_name,
                        "from_warehouse": warehouse,
                        "to_region": region,
                        "quantity": round(quantity, 4),
                        "cost_per_unit": unit_cost,
                        "total_cost": round(quantity * unit_cost, 4),
                    }
                )

    shipments = pd.DataFrame(shipment_rows)
    unmet_rows = []
    for region in region_names:
        quantity = unmet_vars[region].value() or 0.0
        penalty = unmet_penalty[region]
        unmet_rows.append(
            {
                "scenario": scenario_name,
                "region": region,
                "unmet_quantity": round(quantity, 4),
                "penalty_per_unit": penalty,
                "penalty_cost": round(quantity * penalty, 4),
            }
        )

    unmet_demand = pd.DataFrame(unmet_rows)
    transportation_cost = shipments["total_cost"].sum() if not shipments.empty else 0.0
    unmet_penalty_cost = unmet_demand["penalty_cost"].sum()
    total_cost = transportation_cost + unmet_penalty_cost
    total_unmet = unmet_demand["unmet_quantity"].sum()
    result_status = "Optimal with Shortage" if total_unmet > 1e-6 else "Optimal"

    return OptimizationResult(
        status=result_status,
        total_cost=round(total_cost, 4),
        transportation_cost=round(transportation_cost, 4),
        unmet_penalty_cost=round(unmet_penalty_cost, 4),
        unmet_demand=unmet_demand,
        shipments=shipments,
        warehouse_summary=_warehouse_summary(warehouses, shipments),
    )


def _warehouse_summary(warehouses: pd.DataFrame, shipments: pd.DataFrame) -> pd.DataFrame:
    summary = warehouses[["warehouse", "capacity"]].copy()

    if shipments.empty:
        summary["shipped_quantity"] = 0.0
    else:
        shipped = shipments.groupby("from_warehouse")["quantity"].sum()
        summary["shipped_quantity"] = summary["warehouse"].map(shipped).fillna(0.0)

    summary["utilization"] = 0.0
    has_capacity = summary["capacity"] > 0
    summary.loc[has_capacity, "utilization"] = (
        summary.loc[has_capacity, "shipped_quantity"] / summary.loc[has_capacity, "capacity"]
    )
    summary["remaining_capacity"] = summary["capacity"] - summary["shipped_quantity"]
    return summary
