import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def scenario_cost_chart(scenario_summary: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        scenario_summary,
        x="scenario",
        y="total_cost",
        color="status",
        text_auto=",.0f",
        title="Total Cost by Scenario",
        labels={"total_cost": "Total Cost", "scenario": "Scenario"},
    )
    fig.update_layout(xaxis_tickangle=-20, legend_title_text="Solver Status")
    return fig


def cost_breakdown_chart(scenario_summary: pd.DataFrame, scenario: str) -> go.Figure:
    row = scenario_summary[scenario_summary["scenario"] == scenario].iloc[0]
    data = pd.DataFrame(
        {
            "cost_type": ["Transportation", "Unmet Demand Penalty"],
            "cost": [row["transportation_cost"], row["unmet_penalty_cost"]],
        }
    )

    fig = px.bar(
        data,
        x="cost_type",
        y="cost",
        text_auto=",.0f",
        title=f"Cost Breakdown - {scenario}",
        labels={"cost_type": "Cost Type", "cost": "Cost"},
    )
    fig.update_layout(showlegend=False)
    return fig


def warehouse_utilization_chart(utilization: pd.DataFrame, scenario: str) -> go.Figure:
    data = utilization[utilization["scenario"] == scenario].copy()
    data["utilization_pct"] = data["utilization"] * 100

    fig = px.bar(
        data,
        x="warehouse",
        y="utilization_pct",
        text_auto=".1f",
        title=f"Warehouse Utilization - {scenario}",
        labels={"warehouse": "Warehouse", "utilization_pct": "Utilization (%)"},
    )
    fig.add_hline(y=100, line_dash="dash", line_color="red")
    fig.update_yaxes(range=[0, max(110, data["utilization_pct"].max() + 10)])
    return fig


def unmet_demand_chart(unmet_demand: pd.DataFrame, scenario: str) -> go.Figure:
    data = unmet_demand[unmet_demand["scenario"] == scenario].copy()
    data = data[data["unmet_quantity"] > 1e-6]

    if data.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"Unmet Demand - {scenario}",
            annotations=[
                {
                    "text": "No unmet demand",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 18},
                }
            ],
        )
        return fig

    fig = px.bar(
        data,
        x="region",
        y="unmet_quantity",
        text_auto=".0f",
        title=f"Unmet Demand - {scenario}",
        labels={"region": "Region", "unmet_quantity": "Unmet Demand"},
    )
    return fig


def shipment_sankey(shipments: pd.DataFrame, scenario: str) -> go.Figure:
    data = shipments[shipments["scenario"] == scenario].copy()
    if data.empty:
        fig = go.Figure()
        fig.update_layout(title_text=f"Shipment Flows - {scenario}")
        return fig

    warehouses = data["from_warehouse"].drop_duplicates().tolist()
    regions = data["to_region"].drop_duplicates().tolist()
    labels = warehouses + regions
    label_to_index = {label: index for index, label in enumerate(labels)}

    fig = go.Figure(
        data=[
            go.Sankey(
                node={"label": labels, "pad": 18, "thickness": 18},
                link={
                    "source": data["from_warehouse"].map(label_to_index),
                    "target": data["to_region"].map(label_to_index),
                    "value": data["quantity"],
                },
            )
        ]
    )
    fig.update_layout(title_text=f"Shipment Flows - {scenario}")
    return fig


def network_flow_map(
    warehouses: pd.DataFrame,
    regions: pd.DataFrame,
    shipments: pd.DataFrame,
    scenario: str,
) -> go.Figure:
    data = shipments[shipments["scenario"] == scenario].copy()
    warehouse_locations = warehouses.set_index("warehouse")[["latitude", "longitude"]]
    region_locations = regions.set_index("region")[["latitude", "longitude"]]

    fig = go.Figure()
    label_lats = []
    label_lons = []
    label_texts = []
    label_hover_texts = []

    for _, row in data.iterrows():
        warehouse = row["from_warehouse"]
        region = row["to_region"]
        from_lat = warehouse_locations.loc[warehouse, "latitude"]
        from_lon = warehouse_locations.loc[warehouse, "longitude"]
        to_lat = region_locations.loc[region, "latitude"]
        to_lon = region_locations.loc[region, "longitude"]
        width = max(1, row["quantity"] / data["quantity"].max() * 8)

        fig.add_trace(
            go.Scattermapbox(
                lat=[from_lat, to_lat],
                lon=[from_lon, to_lon],
                mode="lines",
                line={"width": width, "color": "#2f6fed"},
                hoverinfo="text",
                text=f"{warehouse} to {region}: {row['quantity']:.0f} units",
                showlegend=False,
            )
        )
        label_lats.append((from_lat + to_lat) / 2)
        label_lons.append((from_lon + to_lon) / 2)
        label_texts.append(f"{row['quantity']:.0f}")
        label_hover_texts.append(
            f"{warehouse} to {region}<br>"
            f"Quantity: {row['quantity']:.0f}<br>"
            f"Cost per unit: {row['cost_per_unit']:.2f}<br>"
            f"Route cost: {row['total_cost']:,.0f}"
        )

    if label_lats:
        fig.add_trace(
            go.Scattermapbox(
                lat=label_lats,
                lon=label_lons,
                mode="markers+text",
                marker={"size": 34, "color": "#ffffff", "opacity": 0.98},
                text=label_texts,
                textfont={"size": 15, "color": "#111827"},
                textposition="middle center",
                hoverinfo="text",
                hovertext=label_hover_texts,
                name="Shipment Quantity",
            )
        )

    fig.add_trace(
        go.Scattermapbox(
            lat=warehouses["latitude"],
            lon=warehouses["longitude"],
            mode="markers+text",
            marker={"size": 14, "color": "#d62728"},
            text=warehouses["warehouse"],
            textposition="top right",
            name="Warehouses",
        )
    )
    fig.add_trace(
        go.Scattermapbox(
            lat=regions["latitude"],
            lon=regions["longitude"],
            mode="markers+text",
            marker={"size": 10, "color": "#2ca02c"},
            text=regions["region"],
            textposition="bottom right",
            name="Customer Regions",
        )
    )

    fig.update_layout(
        title=f"Distribution Network Flow - {scenario}",
        mapbox={
            "style": "open-street-map",
            "center": {"lat": 52.0, "lon": 5.2},
            "zoom": 6,
        },
        margin={"l": 0, "r": 0, "t": 45, "b": 0},
        height=650,
    )
    return fig
