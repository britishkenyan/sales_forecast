# SalesCast — Data-Driven Sales Forecasting Dashboard

A professional sales forecasting web application built with **Python Flask** and **TailwindCSS**, featuring predictive models and interactive data visualizations.

## Features

- **Interactive Dashboard** — KPI cards, revenue trends, category breakdowns, and regional performance
- **Predictive Forecasting** — Three ML models (Linear Regression, Polynomial Regression, Holt-Winters Exponential Smoothing) with automatic best-model selection
- **Deep Analytics** — Year-over-year comparisons, seasonality analysis, growth rate tracking, and correlation scatter plots
- **Data Management** — Upload custom CSV datasets, preview data, and reset to sample data
- **Model Comparison** — Side-by-side accuracy metrics (MAE, RMSE, R², MAPE)
- **Data Storytelling** — Auto-generated forecast insights for non-technical stakeholders

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask |
| Frontend | TailwindCSS (CDN), Chart.js |
| ML Models | scikit-learn, statsmodels |
| Data | pandas, NumPy |

## Quick Start

```bash
# 1. Create & activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1       # Windows
# source venv/bin/activate        # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python run.py
```

Open **http://localhost:5000** in your browser.

## Project Structure

```
Sales_forecasting/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── routes.py                # Page & API routes
│   ├── forecast_engine.py       # ML forecasting models
│   ├── data_generator.py        # Realistic sample data generator
│   └── templates/
│       ├── base.html            # Layout with sidebar & TailwindCSS
│       ├── dashboard.html       # KPIs & overview charts
│       ├── forecast.html        # Forecasting & model comparison
│       ├── analytics.html       # Deep-dive analytics
│       └── data.html            # Data upload & preview
├── data/                        # Auto-generated sales data (gitignored)
├── run.py                       # Application entry point
├── requirements.txt
├── .env
└── .gitignore
```

## Uploading Custom Data

Your CSV must include these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `date` | Yes | Date in YYYY-MM-DD format |
| `sales` | Yes | Revenue amount |
| `quantity` | Yes | Units sold |
| `category` | No | Product category |
| `region` | No | Sales region |
| `unit_price` | No | Price per unit |

## Screenshots

| Dashboard | Forecast |
|-----------|----------|
| KPI cards + trend charts | Multi-model predictions |

---

Built as a portfolio project demonstrating data analysis, predictive modeling, and data storytelling skills.
