"""
Sales Forecasting Engine
Uses multiple models: Linear Regression, Polynomial Regression, and Holt-Winters
Exponential Smoothing for time-series sales forecasting.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings

warnings.filterwarnings("ignore")


class SalesForecastEngine:
    """Core forecasting engine that runs multiple models and picks the best."""

    def __init__(self, data: pd.DataFrame):
        self.raw_data = data.copy()
        self.monthly_sales = self._prepare_monthly_data()
        self.models = {}
        self.forecasts = {}
        self.metrics = {}

    def _prepare_monthly_data(self) -> pd.DataFrame:
        df = self.raw_data.copy()
        df["date"] = pd.to_datetime(df["date"])
        monthly = (
            df.groupby(pd.Grouper(key="date", freq="MS"))
            .agg({"sales": "sum", "quantity": "sum"})
            .reset_index()
        )
        monthly = monthly.sort_values("date").reset_index(drop=True)
        monthly["month_num"] = np.arange(1, len(monthly) + 1)
        return monthly

    def run_all_models(self, forecast_months: int = 6):
        self._run_linear_regression(forecast_months)
        self._run_polynomial_regression(forecast_months)
        self._run_exponential_smoothing(forecast_months)
        return self._get_best_model()

    def _run_linear_regression(self, forecast_months: int):
        df = self.monthly_sales
        X = df[["month_num"]].values
        y = df["sales"].values

        if len(y) < 2:
            return

        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)

        future_months = np.arange(len(df) + 1, len(df) + forecast_months + 1).reshape(
            -1, 1
        )
        forecast = model.predict(future_months)

        self.models["linear_regression"] = model
        self.forecasts["linear_regression"] = {
            "fitted": y_pred.tolist(),
            "forecast": forecast.tolist(),
        }
        self.metrics["linear_regression"] = self._calculate_metrics(y, y_pred)

    def _run_polynomial_regression(self, forecast_months: int, degree: int = 3):
        df = self.monthly_sales
        X = df[["month_num"]].values
        y = df["sales"].values

        if len(y) < 2:
            return

        # Reduce degree if not enough data points
        degree = min(degree, len(y) - 1)

        model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
        model.fit(X, y)
        y_pred = model.predict(X)

        future_months = np.arange(len(df) + 1, len(df) + forecast_months + 1).reshape(
            -1, 1
        )
        forecast = model.predict(future_months)

        self.models["polynomial_regression"] = model
        self.forecasts["polynomial_regression"] = {
            "fitted": y_pred.tolist(),
            "forecast": forecast.tolist(),
        }
        self.metrics["polynomial_regression"] = self._calculate_metrics(y, y_pred)

    def _run_exponential_smoothing(self, forecast_months: int):
        df = self.monthly_sales
        y = df["sales"].values

        if len(y) < 4:
            return

        try:
            seasonal_periods = min(12, len(y) // 2)
            if seasonal_periods < 2:
                seasonal_periods = 2

            model = ExponentialSmoothing(
                y,
                trend="add",
                seasonal="add",
                seasonal_periods=seasonal_periods,
            ).fit(optimized=True)

            y_pred = model.fittedvalues
            forecast = model.forecast(forecast_months)

            self.models["exponential_smoothing"] = model
            self.forecasts["exponential_smoothing"] = {
                "fitted": y_pred.tolist(),
                "forecast": forecast.tolist(),
            }
            self.metrics["exponential_smoothing"] = self._calculate_metrics(
                y, y_pred
            )
        except Exception:
            pass

    def _safe_float(self, value, default=0.0):
        """Convert to float, replacing NaN/Inf with a default."""
        v = float(value)
        if np.isnan(v) or np.isinf(v):
            return default
        return v

    def _calculate_metrics(self, actual, predicted) -> dict:
        try:
            mae = self._safe_float(mean_absolute_error(actual, predicted))
        except Exception:
            mae = 0.0
        try:
            rmse = self._safe_float(np.sqrt(mean_squared_error(actual, predicted)))
        except Exception:
            rmse = 0.0
        try:
            r2 = self._safe_float(r2_score(actual, predicted))
        except Exception:
            r2 = 0.0
        try:
            mape = self._safe_float(
                np.mean(np.abs((actual - predicted) / (actual + 1e-10))) * 100
            )
        except Exception:
            mape = 0.0
        return {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": round(r2, 4),
            "mape": round(mape, 2),
        }

    def _get_best_model(self) -> str:
        if not self.metrics:
            return "linear_regression"
        return min(self.metrics, key=lambda m: self.metrics[m]["mae"])

    def get_summary_stats(self) -> dict:
        df = self.raw_data.copy()
        df["date"] = pd.to_datetime(df["date"])
        monthly = self.monthly_sales

        total_revenue = float(df["sales"].sum())
        total_orders = int(df["quantity"].sum())
        avg_monthly = float(monthly["sales"].mean())

        if len(monthly) >= 2:
            recent = monthly["sales"].iloc[-1]
            previous = monthly["sales"].iloc[-2]
            growth = ((recent - previous) / (previous + 1e-10)) * 100
        else:
            growth = 0.0

        best_month_idx = monthly["sales"].idxmax()
        best_month = monthly.loc[best_month_idx, "date"].strftime("%B %Y")

        return {
            "total_revenue": round(total_revenue, 2),
            "total_orders": total_orders,
            "avg_monthly_revenue": round(avg_monthly, 2),
            "monthly_growth": round(growth, 2),
            "best_month": best_month,
            "data_points": len(monthly),
        }

    def get_category_breakdown(self) -> dict:
        df = self.raw_data.copy()
        if "category" not in df.columns:
            return {}
        breakdown = (
            df.groupby("category")
            .agg({"sales": "sum", "quantity": "sum"})
            .sort_values("sales", ascending=False)
            .reset_index()
        )
        return {
            "categories": breakdown["category"].tolist(),
            "sales": [round(v, 2) for v in breakdown["sales"].tolist()],
            "quantities": breakdown["quantity"].tolist(),
        }

    def get_region_breakdown(self) -> dict:
        df = self.raw_data.copy()
        if "region" not in df.columns:
            return {}
        breakdown = (
            df.groupby("region")
            .agg({"sales": "sum", "quantity": "sum"})
            .sort_values("sales", ascending=False)
            .reset_index()
        )
        return {
            "regions": breakdown["region"].tolist(),
            "sales": [round(v, 2) for v in breakdown["sales"].tolist()],
            "quantities": breakdown["quantity"].tolist(),
        }

    def get_forecast_data(self, forecast_months: int = 6, include_extras: bool = False) -> dict:
        best_model = self.run_all_models(forecast_months)
        monthly = self.monthly_sales

        historical_dates = monthly["date"].dt.strftime("%Y-%m-%d").tolist()
        historical_sales = [round(v, 2) for v in monthly["sales"].tolist()]

        last_date = monthly["date"].iloc[-1]
        future_dates = pd.date_range(
            start=last_date + pd.DateOffset(months=1),
            periods=forecast_months,
            freq="MS",
        )
        future_dates_str = future_dates.strftime("%Y-%m-%d").tolist()

        result = {
            "best_model": best_model,
            "historical_dates": historical_dates,
            "historical_sales": historical_sales,
            "future_dates": future_dates_str,
            "models": {},
        }

        if include_extras:
            result["summary"] = self.get_summary_stats()
            result["category_breakdown"] = self.get_category_breakdown()
            result["region_breakdown"] = self.get_region_breakdown()

        for model_name, forecast_data in self.forecasts.items():
            result["models"][model_name] = {
                "fitted": [round(self._safe_float(v), 2) for v in forecast_data["fitted"]],
                "forecast": [round(self._safe_float(v), 2) for v in forecast_data["forecast"]],
                "metrics": self.metrics[model_name],
            }

        return result
