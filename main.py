from src.data_loader import PROJECT_ROOT, load_input_data
from src.scenarios import run_scenarios


OUTPUT_DIR = PROJECT_ROOT / "outputs"


def main() -> None:
    warehouses, regions, transport_costs, scenarios = load_input_data()
    scenario_summary, shipments, utilization, unmet_demand = run_scenarios(
        warehouses,
        regions,
        transport_costs,
        scenarios,
    )

    OUTPUT_DIR.mkdir(exist_ok=True)

    scenario_summary.to_csv(OUTPUT_DIR / "scenario_summary.csv", index=False)
    shipments.to_csv(OUTPUT_DIR / "optimized_shipments.csv", index=False)
    utilization.to_csv(OUTPUT_DIR / "warehouse_utilization.csv", index=False)
    unmet_demand.to_csv(OUTPUT_DIR / "unmet_demand.csv", index=False)

    print("Optimization completed.")
    print(f"Scenario summary: {OUTPUT_DIR / 'scenario_summary.csv'}")
    print(f"Optimized shipments: {OUTPUT_DIR / 'optimized_shipments.csv'}")
    print(f"Warehouse utilization: {OUTPUT_DIR / 'warehouse_utilization.csv'}")
    print(f"Unmet demand: {OUTPUT_DIR / 'unmet_demand.csv'}")


if __name__ == "__main__":
    main()
