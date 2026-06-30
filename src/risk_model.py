from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd


@dataclass(frozen=True)
class BusinessAssumptions:
    starting_revenue: float = 4.8
    monthly_growth: float = 0.035
    gross_margin: float = 0.62
    fixed_cost: float = 2.35
    variable_cost_pct_revenue: float = 0.18
    starting_cash: float = 9.5
    minimum_cash_buffer: float = 2.0
    planning_months: int = 12
    revenue_shock: float = 0.00
    margin_shock: float = 0.00
    fixed_cost_shock: float = 0.00
    churn_risk: float = 0.00
    execution_risk: float = 0.00


@dataclass(frozen=True)
class ScenarioSummary:
    scenario: str
    ending_revenue: float
    cumulative_revenue: float
    cumulative_ebitda: float
    ending_cash: float
    runway_months: int
    break_even_month: str
    risk_score: float
    status: str


def load_risk_drivers(path: str) -> pd.DataFrame:
    drivers = pd.read_csv(path)
    required = {"Risk", "Category", "Probability", "Revenue_Impact", "Cost_Impact", "Mitigation"}
    missing = required.difference(drivers.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    numeric_columns = ["Probability", "Revenue_Impact", "Cost_Impact"]
    for column in numeric_columns:
        drivers[column] = pd.to_numeric(drivers[column], errors="coerce")
    return drivers.dropna(subset=numeric_columns).reset_index(drop=True)


def build_monthly_projection(assumptions: BusinessAssumptions) -> pd.DataFrame:
    rows = []
    cash_balance = assumptions.starting_cash
    monthly_growth = assumptions.monthly_growth - assumptions.churn_risk
    adjusted_margin = max(0.05, assumptions.gross_margin + assumptions.margin_shock)
    adjusted_fixed_cost = assumptions.fixed_cost * (1 + assumptions.fixed_cost_shock + assumptions.execution_risk)
    revenue = assumptions.starting_revenue * (1 + assumptions.revenue_shock)

    for month in range(1, assumptions.planning_months + 1):
        if month > 1:
            revenue *= 1 + monthly_growth
        gross_profit = revenue * adjusted_margin
        variable_cost = revenue * assumptions.variable_cost_pct_revenue
        operating_cost = adjusted_fixed_cost + variable_cost
        ebitda = gross_profit - operating_cost
        cash_balance += ebitda
        rows.append(
            {
                "Month": month,
                "Revenue": revenue,
                "Gross_Profit": gross_profit,
                "Operating_Cost": operating_cost,
                "EBITDA": ebitda,
                "EBITDA_Margin": divide(ebitda, revenue),
                "Cash_Balance": cash_balance,
                "Below_Buffer": cash_balance < assumptions.minimum_cash_buffer,
            }
        )
    return pd.DataFrame(rows)


def calculate_risk_score(projection: pd.DataFrame, assumptions: BusinessAssumptions) -> float:
    cash_pressure = max(0.0, divide(assumptions.minimum_cash_buffer - float(projection["Cash_Balance"].min()), assumptions.minimum_cash_buffer))
    margin_pressure = max(0.0, 0.15 - float(projection.iloc[-1]["EBITDA_Margin"]))
    growth_pressure = max(0.0, 0.02 - (assumptions.monthly_growth - assumptions.churn_risk))
    score = (cash_pressure * 45) + (margin_pressure * 180) + (growth_pressure * 350) + (assumptions.execution_risk * 100)
    return min(100.0, round(score, 1))


def summarize_projection(name: str, projection: pd.DataFrame, assumptions: BusinessAssumptions) -> ScenarioSummary:
    break_even_rows = projection.loc[projection["EBITDA"] >= 0]
    break_even_month = "Not reached" if break_even_rows.empty else f"Month {int(break_even_rows.iloc[0]['Month'])}"
    runway_months = int((projection["Cash_Balance"] >= assumptions.minimum_cash_buffer).sum())
    risk_score = calculate_risk_score(projection, assumptions)
    status = classify_status(risk_score, float(projection.iloc[-1]["Cash_Balance"]), assumptions.minimum_cash_buffer)
    return ScenarioSummary(
        scenario=name,
        ending_revenue=float(projection.iloc[-1]["Revenue"]),
        cumulative_revenue=float(projection["Revenue"].sum()),
        cumulative_ebitda=float(projection["EBITDA"].sum()),
        ending_cash=float(projection.iloc[-1]["Cash_Balance"]),
        runway_months=runway_months,
        break_even_month=break_even_month,
        risk_score=risk_score,
        status=status,
    )


def build_scenarios(assumptions: BusinessAssumptions) -> tuple[pd.DataFrame, pd.DataFrame]:
    scenario_inputs = {
        "Upside": replace(assumptions, revenue_shock=0.06, margin_shock=0.03, fixed_cost_shock=-0.04, churn_risk=0.00, execution_risk=0.00),
        "Base": assumptions,
        "Downside": replace(assumptions, revenue_shock=-0.08, margin_shock=-0.04, fixed_cost_shock=0.08, churn_risk=0.015, execution_risk=0.04),
        "Stress": replace(assumptions, revenue_shock=-0.16, margin_shock=-0.08, fixed_cost_shock=0.14, churn_risk=0.03, execution_risk=0.08),
    }
    projection_rows = []
    summary_rows = []
    for scenario_name, scenario_assumptions in scenario_inputs.items():
        projection = build_monthly_projection(scenario_assumptions)
        projection["Scenario"] = scenario_name
        projection_rows.append(projection)
        summary_rows.append(summarize_projection(scenario_name, projection, scenario_assumptions).__dict__)
    return pd.concat(projection_rows, ignore_index=True), pd.DataFrame(summary_rows)


def build_risk_register(drivers: pd.DataFrame) -> pd.DataFrame:
    output = drivers.copy()
    output["Expected_Revenue_Impact"] = output["Probability"] * output["Revenue_Impact"]
    output["Expected_Cost_Impact"] = output["Probability"] * output["Cost_Impact"]
    output["Severity_Score"] = (output["Expected_Revenue_Impact"].abs() + output["Expected_Cost_Impact"].abs()) * 100
    return output.sort_values("Severity_Score", ascending=False).reset_index(drop=True)


def build_mitigation_memo(summary: pd.DataFrame, risk_register: pd.DataFrame, company_name: str) -> str:
    base = summary.loc[summary["scenario"] == "Base"].iloc[0]
    stress = summary.loc[summary["scenario"] == "Stress"].iloc[0]
    top_risks = risk_register.head(3)
    mitigation_lines = "\n".join(f"- **{row.Risk}:** {row.Mitigation}" for row in top_risks.itertuples())
    return f"""### Business Risk & Scenario Memo

**Company:** {company_name}

**Base case:** Ending cash is {format_money(float(base.ending_cash))}, cumulative EBITDA is {format_money(float(base.cumulative_ebitda))}, and the risk score is {float(base.risk_score):.1f}/100.

**Stress case:** Ending cash falls to {format_money(float(stress.ending_cash))}, runway is {int(stress.runway_months)} months, and the risk score rises to {float(stress.risk_score):.1f}/100.

**Decision readout:** {status_message(str(base.status), str(stress.status))}

**Priority mitigations:**
{mitigation_lines}

**Operating cadence:** Review this dashboard monthly, refresh risk probabilities after management meetings, and escalate any scenario where cash drops below the minimum buffer or EBITDA break-even is not reached.
"""


def classify_status(risk_score: float, ending_cash: float, minimum_cash_buffer: float) -> str:
    if ending_cash < minimum_cash_buffer or risk_score >= 70:
        return "Escalate"
    if risk_score >= 40:
        return "Monitor"
    return "On track"


def status_message(base_status: str, stress_status: str) -> str:
    if stress_status == "Escalate":
        return "Base case is manageable, but the stress case needs active mitigation and cash-buffer monitoring."
    if base_status == "Escalate":
        return "The current operating plan requires immediate intervention before further growth investment."
    return "The plan is resilient across the modeled range, with monitoring focused on the highest-severity risks."


def format_money(value: float) -> str:
    return f"${value:,.1f}M"


def divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
