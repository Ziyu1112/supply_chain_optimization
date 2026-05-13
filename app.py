import streamlit as st

from src.data_loader import load_input_data
from src.scenarios import run_scenarios
from src.visualization import (
    cost_breakdown_chart,
    network_flow_map,
    scenario_cost_chart,
    unmet_demand_chart,
    warehouse_utilization_chart,
)


st.set_page_config(page_title="FMCG Distribution Optimization", layout="wide")


@st.cache_data
def load_results():
    warehouses, regions, transport_costs, scenarios = load_input_data()
    scenario_summary, shipments, utilization, unmet_demand = run_scenarios(
        warehouses,
        regions,
        transport_costs,
        scenarios,
    )
    return warehouses, regions, scenario_summary, shipments, utilization, unmet_demand


warehouses, regions, scenario_summary, shipments, utilization, unmet_demand = load_results()

st.title("FMCG Distribution Network Optimization")
st.caption("Scenario-based distribution planning with capacity limits, transport costs, and shortage penalties.")

scenario = st.sidebar.selectbox(
    "Scenario",
    scenario_summary["scenario"].tolist(),
)

selected_summary = scenario_summary[scenario_summary["scenario"] == scenario].iloc[0]
selected_shipments = shipments[shipments["scenario"] == scenario].sort_values(
    ["from_warehouse", "to_region"]
)
selected_unmet = unmet_demand[unmet_demand["scenario"] == scenario].sort_values("region")
selected_utilization = utilization[utilization["scenario"] == scenario].sort_values("warehouse")

with st.container(border=True):
    st.subheader(scenario)
    st.write(selected_summary["description"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Status", selected_summary["status"])
    col2.metric("Total Cost", f"{selected_summary['total_cost']:,.0f}")
    col3.metric(
        "Cost Change vs Base",
        f"{selected_summary['cost_change_vs_base']:,.0f}",
        f"{selected_summary['cost_change_pct_vs_base']:.1%}",
    )
    col4.metric("Unmet Demand", f"{selected_summary['total_unmet_demand']:,.0f}")

    if selected_summary["total_unmet_demand"] > 0:
        st.warning(
            f"This scenario has {selected_summary['total_unmet_demand']:,.0f} units of unmet demand. "
            f"The model applies {selected_summary['unmet_penalty_cost']:,.0f} in shortage penalty cost."
        )
    else:
        st.success("All regional demand is satisfied in this scenario.")

overview_tab, network_tab, shortage_tab, data_tab = st.tabs(
    ["Overview", "Network Plan", "Shortage", "Data"]
)

with overview_tab:
    left, right = st.columns([1.15, 0.85])
    with left:
        st.plotly_chart(scenario_cost_chart(scenario_summary), use_container_width=True)
    with right:
        st.plotly_chart(cost_breakdown_chart(scenario_summary, scenario), use_container_width=True)

    st.dataframe(
        scenario_summary[
            [
                "scenario",
                "status",
                "total_cost",
                "transportation_cost",
                "unmet_penalty_cost",
                "total_unmet_demand",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

with network_tab:
    st.plotly_chart(
        network_flow_map(warehouses, regions, shipments, scenario),
        use_container_width=True,
    )

    st.plotly_chart(warehouse_utilization_chart(utilization, scenario), use_container_width=True)

with shortage_tab:
    left, right = st.columns([1, 1])
    with left:
        st.plotly_chart(unmet_demand_chart(unmet_demand, scenario), use_container_width=True)
    with right:
        st.dataframe(
            selected_unmet,
            use_container_width=True,
            hide_index=True,
        )

with data_tab:
    st.subheader("Optimized Shipment Plan")
    st.dataframe(
        selected_shipments,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Warehouse Utilization")
    st.dataframe(
        selected_utilization,
        use_container_width=True,
        hide_index=True,
    )
