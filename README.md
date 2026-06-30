# Business Risk & Scenario Planning Dashboard

A Streamlit dashboard for business risk analysis, scenario planning, cash runway monitoring, EBITDA stress testing, and consultant-style mitigation recommendations.

## Live Demo

[Open the Streamlit app](https://business-risk-scenario-dashboard.streamlit.app/)

## What It Does

- Models Upside, Base, Downside, and Stress scenarios
- Tracks revenue, EBITDA, cash balance, runway, and break-even timing
- Estimates cash balance using EBITDA less capex and incremental working capital investment
- Scores scenario risk based on cash pressure, margin pressure, growth pressure, and execution risk
- Ranks business risks by expected severity
- Generates a mitigation memo for management or consulting-style reviews
- Lets users adjust operating assumptions through Streamlit controls

## Why This Project Matters

This project is designed for business analyst, consulting, strategy, risk, operations, and finance applications. It shows that the user can translate uncertain business conditions into measurable operating scenarios and executive recommendations.

## Tech Stack

- Python
- Streamlit
- Pandas
- Standard-library tests with `unittest`

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Validate

```bash
python scripts/validate.py
```

## Portfolio Talking Points

- Built an interactive scenario dashboard for revenue, margin, cost, runway, and execution-risk analysis
- Created a quantitative risk score and risk-register ranking model
- Added capex, working capital, true runway logic, and transparent risk-score methodology
- Converted dashboard outputs into a consultant-style mitigation memo
- Designed the project to support business analyst, consulting, strategy, risk, and finance roles

## Author

Dhruv Harlalka

MBA Finance, Middlesex University Dubai
