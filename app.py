import pandas as pd
import streamlit as st

from src.risk_model import (
    BusinessAssumptions,
    build_mitigation_memo,
    build_risk_register,
    build_scenarios,
    format_money,
    load_risk_drivers,
)


def format_percent_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    output = df.copy()
    for column in columns:
        if column in output.columns:
            output[column] = output[column].map(lambda value: f"{value:.1%}")
    return output


def format_money_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    output = df.copy()
    for column in columns:
        if column in output.columns:
            output[column] = output[column].map(lambda value: f"${value:,.1f}M")
    return output


st.set_page_config(
    page_title="Business Risk & Scenario Planning Dashboard",
    page_icon=":triangular_flag_on_post:",
    layout="wide",
)


@st.cache_data
def load_drivers() -> pd.DataFrame:
    return load_risk_drivers("data/risk_drivers.csv")


st.title("Business Risk & Scenario Planning Dashboard")
st.caption("Scenario planning, cash runway, EBITDA pressure, risk scoring, and mitigation memo for operating decisions.")

with st.sidebar:
    st.header("Operating Plan")
    company_name = st.text_input("Company", "Atlas Workflow Systems")
    starting_revenue = st.slider("Starting monthly revenue", 1.0, 12.0, 4.8, 0.1)
    monthly_growth = st.slider("Monthly revenue growth", -0.05, 0.12, 0.035, 0.005)
    gross_margin = st.slider("Gross margin", 0.25, 0.85, 0.62, 0.01)
    fixed_cost = st.slider("Monthly fixed cost", 0.5, 6.0, 2.35, 0.05)
    variable_cost_pct = st.slider("Variable cost / revenue", 0.02, 0.35, 0.18, 0.01)
    starting_cash = st.slider("Starting cash", 1.0, 25.0, 9.5, 0.5)
    minimum_cash_buffer = st.slider("Minimum cash buffer", 0.5, 8.0, 2.0, 0.25)

assumptions = BusinessAssumptions(
    starting_revenue=starting_revenue,
    monthly_growth=monthly_growth,
    gross_margin=gross_margin,
    fixed_cost=fixed_cost,
    variable_cost_pct_revenue=variable_cost_pct,
    starting_cash=starting_cash,
    minimum_cash_buffer=minimum_cash_buffer,
)

drivers = load_drivers()
projections, scenario_summary = build_scenarios(assumptions)
risk_register = build_risk_register(drivers)
base = scenario_summary.loc[scenario_summary["scenario"] == "Base"].iloc[0]
stress = scenario_summary.loc[scenario_summary["scenario"] == "Stress"].iloc[0]

hero = st.columns(5)
hero[0].metric("Base Status", str(base.status))
hero[1].metric("Base Ending Cash", format_money(float(base.ending_cash)))
hero[2].metric("Stress Runway", f"{int(stress.runway_months)} months")
hero[3].metric("Stress Risk Score", f"{float(stress.risk_score):.1f}/100")
hero[4].metric("Base Break-even", str(base.break_even_month))

st.divider()

snapshot_tab, scenario_tab, risk_tab, memo_tab, data_tab = st.tabs(
    ["Executive Snapshot", "Scenario Model", "Risk Register", "Mitigation Memo", "Data"]
)

with snapshot_tab:
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Cash Balance by Scenario")
        cash_chart = projections.pivot(index="Month", columns="Scenario", values="Cash_Balance")
        st.line_chart(cash_chart, use_container_width=True)
    with right:
        st.subheader("Scenario Readout")
        st.write(f"Base case ends with **{format_money(float(base.ending_cash))}** cash and **{format_money(float(base.cumulative_ebitda))}** cumulative EBITDA.")
        st.write(f"Stress case ends with **{format_money(float(stress.ending_cash))}** cash and a **{float(stress.risk_score):.1f}/100** risk score.")
        st.write(f"Highest-priority risk: **{risk_register.iloc[0]['Risk']}**.")

    st.subheader("Risk Score by Scenario")
    risk_chart = scenario_summary[["scenario", "risk_score"]].set_index("scenario")
    st.bar_chart(risk_chart, use_container_width=True)

with scenario_tab:
    st.subheader("Scenario Summary")
    scenario_display = scenario_summary.copy()
    scenario_display = format_money_columns(
        scenario_display,
        ["ending_revenue", "cumulative_revenue", "cumulative_ebitda", "ending_cash"],
    )
    st.dataframe(scenario_display, use_container_width=True, hide_index=True)

    st.subheader("EBITDA by Month")
    ebitda_chart = projections.pivot(index="Month", columns="Scenario", values="EBITDA")
    st.line_chart(ebitda_chart, use_container_width=True)

with risk_tab:
    st.subheader("Risk Register")
    risk_display = format_percent_columns(
        risk_register,
        ["Probability", "Revenue_Impact", "Cost_Impact", "Expected_Revenue_Impact", "Expected_Cost_Impact"],
    )
    st.dataframe(risk_display, use_container_width=True, hide_index=True)

    st.subheader("Expected Severity")
    severity_chart = risk_register[["Risk", "Severity_Score"]].set_index("Risk")
    st.bar_chart(severity_chart, use_container_width=True)

with memo_tab:
    st.subheader("Consultant-Style Mitigation Memo")
    memo = build_mitigation_memo(scenario_summary, risk_register, company_name)
    st.markdown(memo)
    st.download_button("Download memo", memo, "business_risk_mitigation_memo.md", "text/markdown")

with data_tab:
    st.subheader("Monthly Projection")
    projection_display = projections.copy()
    projection_display = format_money_columns(
        format_percent_columns(projection_display, ["EBITDA_Margin"]),
        ["Revenue", "Gross_Profit", "Operating_Cost", "EBITDA", "Cash_Balance"],
    )
    st.dataframe(projection_display, use_container_width=True, hide_index=True)
    st.subheader("Source Risk Drivers")
    st.dataframe(drivers, use_container_width=True, hide_index=True)
