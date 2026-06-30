import unittest

import pandas as pd

from src.risk_model import (
    BusinessAssumptions,
    build_mitigation_memo,
    build_monthly_projection,
    build_risk_register,
    build_scenarios,
    calculate_risk_score,
    load_risk_drivers,
)


class RiskModelTests(unittest.TestCase):
    def setUp(self):
        self.assumptions = BusinessAssumptions()
        self.drivers = pd.DataFrame(
            {
                "Risk": ["Churn spike", "Supplier inflation"],
                "Category": ["Commercial", "Operations"],
                "Probability": [0.25, 0.30],
                "Revenue_Impact": [-0.10, 0.0],
                "Cost_Impact": [0.01, 0.05],
                "Mitigation": ["Retention plan", "Vendor renegotiation"],
            }
        )

    def test_monthly_projection_has_planning_period(self):
        projection = build_monthly_projection(self.assumptions)

        self.assertEqual(len(projection), 12)
        self.assertIn("Cash_Balance", projection.columns)
        self.assertGreater(projection.iloc[-1]["Revenue"], projection.iloc[0]["Revenue"])

    def test_scenarios_include_base_downside_upside_and_stress(self):
        projections, summary = build_scenarios(self.assumptions)

        self.assertEqual(set(summary["scenario"]), {"Upside", "Base", "Downside", "Stress"})
        self.assertEqual(set(projections["Scenario"]), {"Upside", "Base", "Downside", "Stress"})
        self.assertIn("risk_score", summary.columns)

    def test_stress_case_is_riskier_than_base(self):
        _, summary = build_scenarios(self.assumptions)
        base = float(summary.loc[summary["scenario"] == "Base", "risk_score"].iloc[0])
        stress = float(summary.loc[summary["scenario"] == "Stress", "risk_score"].iloc[0])

        self.assertGreaterEqual(stress, base)

    def test_risk_register_sorts_by_expected_severity(self):
        register = build_risk_register(self.drivers)

        self.assertIn("Severity_Score", register.columns)
        self.assertGreaterEqual(register.iloc[0]["Severity_Score"], register.iloc[-1]["Severity_Score"])

    def test_risk_score_is_bounded(self):
        projection = build_monthly_projection(self.assumptions)
        score = calculate_risk_score(projection, self.assumptions)

        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_driver_loader_validates_required_columns(self):
        loaded = load_risk_drivers("data/risk_drivers.csv")

        self.assertFalse(loaded.empty)
        self.assertIn("Mitigation", loaded.columns)

    def test_memo_contains_decision_sections(self):
        _, summary = build_scenarios(self.assumptions)
        register = build_risk_register(self.drivers)
        memo = build_mitigation_memo(summary, register, "TestCo")

        self.assertIn("Business Risk & Scenario Memo", memo)
        self.assertIn("Priority mitigations", memo)


if __name__ == "__main__":
    unittest.main()
