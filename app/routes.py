"""
Flask routes for the Sales Forecasting Dashboard.
Handles both page rendering and API endpoints for chart data.
"""

import os
import json
import hashlib
import pandas as pd
import numpy as np
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from app.forecast_engine import SalesForecastEngine
from app.data_generator import generate_sample_data, save_sample_data
from app.currency import (
    convert, detect_currency_from_data, save_source_currency,
    get_source_currency, get_supported_currencies,
    EXCHANGE_RATES, CURRENCY_SYMBOLS, CURRENCY_NAMES,
)

main_bp = Blueprint("main", __name__)
api_bp = Blueprint("api", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ALLOWED_EXTENSIONS = {"csv"}

# Simple data cache to avoid re-reading CSV on every request
_data_cache = {"mtime": None, "df": None}


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_data() -> pd.DataFrame:
    os.makedirs(DATA_DIR, exist_ok=True)
    data_path = os.path.join(DATA_DIR, "sales_data.csv")

    if not os.path.exists(data_path):
        save_sample_data(data_path)

    mtime = os.path.getmtime(data_path)
    if _data_cache["mtime"] == mtime and _data_cache["df"] is not None:
        return _data_cache["df"].copy()

    df = pd.read_csv(data_path)
    _data_cache["mtime"] = mtime
    _data_cache["df"] = df
    return df.copy()


def _get_display_currency():
    """Get the display currency from the request query parameter."""
    return request.args.get("currency", "USD").upper()


def _convert_value(value, to_currency):
    """Convert a monetary value from the source currency to the display currency."""
    source = get_source_currency()
    return round(convert(value, source, to_currency), 2)


def _apply_date_filter(df):
    """Apply date range filtering from query params."""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    if date_from or date_to:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        if date_from:
            df = df[df["date"] >= pd.to_datetime(date_from)]
        if date_to:
            df = df[df["date"] <= pd.to_datetime(date_to)]
    return df


FORECAST_HISTORY_PATH = os.path.join(DATA_DIR, "forecast_history.json")
DATASETS_DIR = os.path.join(DATA_DIR, "datasets")


def _load_forecast_history():
    if os.path.exists(FORECAST_HISTORY_PATH):
        with open(FORECAST_HISTORY_PATH, "r") as f:
            return json.load(f)
    return []


def _save_forecast_history(history):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FORECAST_HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


# ── Page Routes ──────────────────────────────────────────────

@main_bp.route("/")
def dashboard():
    return render_template("dashboard.html")


@main_bp.route("/forecast")
def forecast():
    return render_template("forecast.html")


@main_bp.route("/analytics")
def analytics():
    return render_template("analytics.html")


@main_bp.route("/data")
def data_view():
    return render_template("data.html")


# ── API Routes ───────────────────────────────────────────────

@api_bp.route("/currencies")
def api_currencies():
    return jsonify({
        "currencies": get_supported_currencies(),
        "source_currency": get_source_currency(),
        "default": "USD",
    })


@api_bp.route("/summary")
def api_summary():
    currency = _get_display_currency()
    df = _apply_date_filter(_get_data())
    engine = SalesForecastEngine(df)
    stats = engine.get_summary_stats()
    stats["total_revenue"] = _convert_value(stats["total_revenue"], currency)
    stats["avg_monthly_revenue"] = _convert_value(stats["avg_monthly_revenue"], currency)
    stats["currency"] = currency
    stats["currency_symbol"] = CURRENCY_SYMBOLS.get(currency, currency)
    stats["source_currency"] = get_source_currency()
    return jsonify(stats)


@api_bp.route("/forecast")
def api_forecast():
    months = request.args.get("months", 6, type=int)
    months = max(1, min(months, 24))  # Clamp between 1 and 24
    currency = _get_display_currency()

    df = _apply_date_filter(_get_data())
    engine = SalesForecastEngine(df)
    result = engine.get_forecast_data(forecast_months=months)

    # Convert monetary values
    result["historical_sales"] = [_convert_value(v, currency) for v in result["historical_sales"]]
    for model_name in result["models"]:
        result["models"][model_name]["fitted"] = [_convert_value(v, currency) for v in result["models"][model_name]["fitted"]]
        result["models"][model_name]["forecast"] = [_convert_value(v, currency) for v in result["models"][model_name]["forecast"]]
        result["models"][model_name]["metrics"]["mae"] = _convert_value(result["models"][model_name]["metrics"]["mae"], currency)
        result["models"][model_name]["metrics"]["rmse"] = _convert_value(result["models"][model_name]["metrics"]["rmse"], currency)
    result["currency"] = currency
    result["currency_symbol"] = CURRENCY_SYMBOLS.get(currency, currency)
    return jsonify(result)


@api_bp.route("/categories")
def api_categories():
    currency = _get_display_currency()
    df = _apply_date_filter(_get_data())
    engine = SalesForecastEngine(df)
    breakdown = engine.get_category_breakdown()
    if breakdown.get("sales"):
        breakdown["sales"] = [_convert_value(v, currency) for v in breakdown["sales"]]
    breakdown["currency"] = currency
    breakdown["currency_symbol"] = CURRENCY_SYMBOLS.get(currency, currency)
    return jsonify(breakdown)


@api_bp.route("/regions")
def api_regions():
    currency = _get_display_currency()
    df = _apply_date_filter(_get_data())
    engine = SalesForecastEngine(df)
    breakdown = engine.get_region_breakdown()
    if breakdown.get("sales"):
        breakdown["sales"] = [_convert_value(v, currency) for v in breakdown["sales"]]
    breakdown["currency"] = currency
    breakdown["currency_symbol"] = CURRENCY_SYMBOLS.get(currency, currency)
    return jsonify(breakdown)


@api_bp.route("/monthly-trend")
def api_monthly_trend():
    currency = _get_display_currency()
    df = _apply_date_filter(_get_data())
    df["date"] = pd.to_datetime(df["date"])
    monthly = (
        df.groupby(pd.Grouper(key="date", freq="MS"))
        .agg({"sales": "sum", "quantity": "sum"})
        .reset_index()
    )
    monthly = monthly.sort_values("date")

    return jsonify(
        {
            "dates": monthly["date"].dt.strftime("%Y-%m-%d").tolist(),
            "sales": [_convert_value(v, currency) for v in monthly["sales"].tolist()],
            "quantities": monthly["quantity"].tolist(),
            "currency": currency,
            "currency_symbol": CURRENCY_SYMBOLS.get(currency, currency),
        }
    )


@api_bp.route("/daily-trend")
def api_daily_trend():
    currency = _get_display_currency()
    df = _apply_date_filter(_get_data())
    df["date"] = pd.to_datetime(df["date"])

    # Last 90 days
    recent = df[df["date"] >= df["date"].max() - pd.Timedelta(days=90)]
    daily = (
        recent.groupby("date")
        .agg({"sales": "sum", "quantity": "sum"})
        .reset_index()
        .sort_values("date")
    )

    return jsonify(
        {
            "dates": daily["date"].dt.strftime("%Y-%m-%d").tolist(),
            "sales": [_convert_value(v, currency) for v in daily["sales"].tolist()],
            "quantities": daily["quantity"].tolist(),
            "currency": currency,
            "currency_symbol": CURRENCY_SYMBOLS.get(currency, currency),
        }
    )


@api_bp.route("/top-products")
def api_top_products():
    currency = _get_display_currency()
    df = _apply_date_filter(_get_data())
    top = (
        df.groupby("category")
        .agg({"sales": "sum", "quantity": "sum"})
        .sort_values("sales", ascending=False)
        .head(10)
        .reset_index()
    )
    return jsonify(
        {
            "categories": top["category"].tolist(),
            "sales": [_convert_value(v, currency) for v in top["sales"].tolist()],
            "quantities": top["quantity"].tolist(),
            "currency": currency,
            "currency_symbol": CURRENCY_SYMBOLS.get(currency, currency),
        }
    )


@api_bp.route("/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "Only CSV files are allowed"}), 400

    try:
        df = pd.read_csv(file)

        required_cols = {"date", "sales", "quantity"}
        if not required_cols.issubset(set(df.columns)):
            return jsonify(
                {
                    "error": f"CSV must contain columns: {', '.join(required_cols)}. Found: {', '.join(df.columns)}"
                }
            ), 400

        # Detect and save source currency
        source_currency = detect_currency_from_data(df)
        save_source_currency(source_currency)

        # Remove currency column before saving (it's stored as metadata)
        save_df = df.drop(columns=["currency"], errors="ignore")

        os.makedirs(DATA_DIR, exist_ok=True)
        data_path = os.path.join(DATA_DIR, "sales_data.csv")
        save_df.to_csv(data_path, index=False)

        return jsonify({
            "message": "Data uploaded successfully",
            "rows": len(df),
            "source_currency": source_currency,
        })
    except Exception as e:
        return jsonify({"error": f"Failed to process file: {str(e)}"}), 400


@api_bp.route("/reset", methods=["POST"])
def api_reset():
    os.makedirs(DATA_DIR, exist_ok=True)
    data_path = os.path.join(DATA_DIR, "sales_data.csv")
    save_sample_data(data_path)
    save_source_currency("USD")
    return jsonify({"message": "Data reset to sample dataset", "source_currency": "USD"})


@api_bp.route("/data-preview")
def api_data_preview():
    df = _get_data()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    per_page = max(10, min(per_page, 200))

    total = len(df)
    start = (page - 1) * per_page
    end = start + per_page

    subset = df.iloc[start:end]

    return jsonify(
        {
            "data": subset.to_dict(orient="records"),
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    )


# ── Feature: Date Range Info ────────────────────────────────

@api_bp.route("/date-range")
def api_date_range():
    """Return the min/max dates available in the dataset."""
    df = _get_data()
    df["date"] = pd.to_datetime(df["date"])
    return jsonify({
        "min_date": df["date"].min().strftime("%Y-%m-%d"),
        "max_date": df["date"].max().strftime("%Y-%m-%d"),
    })


# ── Feature: Anomaly Detection ──────────────────────────────

@api_bp.route("/anomalies")
def api_anomalies():
    """Detect anomalies in sales data using IQR method."""
    currency = _get_display_currency()
    df = _apply_date_filter(_get_data())
    df["date"] = pd.to_datetime(df["date"])

    monthly = (
        df.groupby(pd.Grouper(key="date", freq="MS"))
        .agg({"sales": "sum", "quantity": "sum"})
        .reset_index()
        .sort_values("date")
    )

    alerts = []

    if len(monthly) >= 4:
        # IQR-based anomaly detection on sales
        q1 = monthly["sales"].quantile(0.25)
        q3 = monthly["sales"].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        for _, row in monthly.iterrows():
            if row["sales"] > upper:
                alerts.append({
                    "type": "spike",
                    "severity": "warning",
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "message": f"Unusually high revenue of {_convert_value(row['sales'], currency):,.0f} in {row['date'].strftime('%b %Y')}",
                    "value": _convert_value(row["sales"], currency),
                })
            elif row["sales"] < lower:
                alerts.append({
                    "type": "drop",
                    "severity": "danger",
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "message": f"Revenue drop to {_convert_value(row['sales'], currency):,.0f} in {row['date'].strftime('%b %Y')}",
                    "value": _convert_value(row["sales"], currency),
                })

        # Month-over-month growth alerts
        for i in range(1, len(monthly)):
            prev = monthly.iloc[i - 1]["sales"]
            curr = monthly.iloc[i]["sales"]
            if prev > 0:
                change = ((curr - prev) / prev) * 100
                if change < -30:
                    alerts.append({
                        "type": "decline",
                        "severity": "danger",
                        "date": monthly.iloc[i]["date"].strftime("%Y-%m-%d"),
                        "message": f"{change:.1f}% decline in {monthly.iloc[i]['date'].strftime('%b %Y')} vs previous month",
                        "value": round(change, 1),
                    })
                elif change > 50:
                    alerts.append({
                        "type": "surge",
                        "severity": "info",
                        "date": monthly.iloc[i]["date"].strftime("%Y-%m-%d"),
                        "message": f"+{change:.1f}% surge in {monthly.iloc[i]['date'].strftime('%b %Y')} vs previous month",
                        "value": round(change, 1),
                    })

    # Sort by date descending
    alerts.sort(key=lambda x: x["date"], reverse=True)
    return jsonify({"alerts": alerts, "total": len(alerts)})


# ── Feature: Forecast History / Accuracy Tracking ────────────

@api_bp.route("/forecast-history", methods=["GET"])
def api_forecast_history():
    """Return saved forecast history for accuracy tracking."""
    history = _load_forecast_history()
    return jsonify({"history": history})


@api_bp.route("/forecast-history", methods=["POST"])
def api_save_forecast():
    """Save a forecast snapshot for future accuracy comparison."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    history = _load_forecast_history()
    entry = {
        "id": hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:8],
        "saved_at": datetime.now().isoformat(),
        "model": data.get("model", "unknown"),
        "months": data.get("months", 6),
        "forecast_dates": data.get("forecast_dates", []),
        "forecast_values": data.get("forecast_values", []),
        "currency": data.get("currency", "USD"),
    }
    history.append(entry)
    # Keep last 20 forecasts
    history = history[-20:]
    _save_forecast_history(history)
    return jsonify({"message": "Forecast saved", "id": entry["id"]})


@api_bp.route("/forecast-accuracy")
def api_forecast_accuracy():
    """Compare saved forecasts against actual data."""
    currency = _get_display_currency()
    history = _load_forecast_history()
    df = _get_data()
    df["date"] = pd.to_datetime(df["date"])
    monthly = (
        df.groupby(pd.Grouper(key="date", freq="MS"))
        .agg({"sales": "sum"})
        .reset_index()
    )
    actual_map = {
        row["date"].strftime("%Y-%m-%d"): row["sales"]
        for _, row in monthly.iterrows()
    }

    results = []
    for entry in history:
        comparisons = []
        for i, fdate in enumerate(entry.get("forecast_dates", [])):
            if fdate in actual_map:
                predicted = entry["forecast_values"][i]
                actual = actual_map[fdate]
                comparisons.append({
                    "date": fdate,
                    "predicted": _convert_value(predicted, currency),
                    "actual": _convert_value(actual, currency),
                    "error_pct": round(abs(predicted - actual) / actual * 100, 1) if actual else 0,
                })
        if comparisons:
            results.append({
                "id": entry["id"],
                "saved_at": entry["saved_at"],
                "model": entry["model"],
                "comparisons": comparisons,
                "avg_error": round(
                    sum(c["error_pct"] for c in comparisons) / len(comparisons), 1
                ),
            })
    return jsonify({"results": results})


# ── Feature: Multi-dataset Management ────────────────────────

@api_bp.route("/datasets", methods=["GET"])
def api_list_datasets():
    """List all saved datasets."""
    os.makedirs(DATASETS_DIR, exist_ok=True)
    datasets = []
    for fname in os.listdir(DATASETS_DIR):
        if fname.endswith(".csv"):
            fpath = os.path.join(DATASETS_DIR, fname)
            stat = os.stat(fpath)
            try:
                df = pd.read_csv(fpath, nrows=1)
                cols = list(df.columns)
                row_count_df = pd.read_csv(fpath)
                row_count = len(row_count_df)
            except Exception:
                cols = []
                row_count = 0
            datasets.append({
                "name": fname[:-4],
                "filename": fname,
                "rows": row_count,
                "columns": cols,
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    datasets.sort(key=lambda x: x["modified"], reverse=True)
    return jsonify({"datasets": datasets})


@api_bp.route("/datasets/save", methods=["POST"])
def api_save_dataset():
    """Save current dataset with a name."""
    data = request.get_json()
    name = data.get("name", "").strip() if data else ""
    if not name:
        return jsonify({"error": "Dataset name is required"}), 400

    # Sanitize name
    safe_name = secure_filename(name)
    if not safe_name:
        return jsonify({"error": "Invalid dataset name"}), 400

    os.makedirs(DATASETS_DIR, exist_ok=True)
    src = os.path.join(DATA_DIR, "sales_data.csv")
    dst = os.path.join(DATASETS_DIR, f"{safe_name}.csv")

    if not os.path.exists(src):
        return jsonify({"error": "No active dataset to save"}), 400

    import shutil
    shutil.copy2(src, dst)
    return jsonify({"message": f"Dataset saved as '{safe_name}'"})


@api_bp.route("/datasets/load", methods=["POST"])
def api_load_dataset():
    """Load a saved dataset as the active dataset."""
    data = request.get_json()
    name = data.get("name", "").strip() if data else ""
    if not name:
        return jsonify({"error": "Dataset name is required"}), 400

    safe_name = secure_filename(name)
    src = os.path.join(DATASETS_DIR, f"{safe_name}.csv")
    if not os.path.exists(src):
        return jsonify({"error": "Dataset not found"}), 404

    import shutil
    dst = os.path.join(DATA_DIR, "sales_data.csv")
    shutil.copy2(src, dst)

    # Reset cache
    _data_cache["mtime"] = None
    _data_cache["df"] = None

    return jsonify({"message": f"Dataset '{safe_name}' loaded"})


@api_bp.route("/datasets/delete", methods=["POST"])
def api_delete_dataset():
    """Delete a saved dataset."""
    data = request.get_json()
    name = data.get("name", "").strip() if data else ""
    if not name:
        return jsonify({"error": "Dataset name is required"}), 400

    safe_name = secure_filename(name)
    fpath = os.path.join(DATASETS_DIR, f"{safe_name}.csv")
    if os.path.exists(fpath):
        os.remove(fpath)
    return jsonify({"message": f"Dataset '{safe_name}' deleted"})


# ── Feature: Upload Validation / Preview ─────────────────────

@api_bp.route("/upload-validate", methods=["POST"])
def api_upload_validate():
    """Validate and preview CSV before committing upload."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not _allowed_file(file.filename):
        return jsonify({"error": "Only CSV files are allowed"}), 400

    try:
        df = pd.read_csv(file)
        columns = list(df.columns)
        required = {"date", "sales", "quantity"}
        missing = required - set(columns)

        # Basic stats
        stats = {
            "filename": file.filename,
            "rows": len(df),
            "columns": columns,
            "missing_required": list(missing),
            "has_required": len(missing) == 0,
            "preview": df.head(5).to_dict(orient="records"),
        }

        # Data quality checks
        issues = []
        if "date" in df.columns:
            try:
                dates = pd.to_datetime(df["date"])
                stats["date_range"] = {
                    "min": dates.min().strftime("%Y-%m-%d"),
                    "max": dates.max().strftime("%Y-%m-%d"),
                }
                null_dates = df["date"].isna().sum()
                if null_dates > 0:
                    issues.append(f"{null_dates} rows with missing dates")
            except Exception:
                issues.append("Unable to parse date column")

        if "sales" in df.columns:
            null_sales = df["sales"].isna().sum()
            if null_sales > 0:
                issues.append(f"{null_sales} rows with missing sales values")
            neg_sales = (pd.to_numeric(df["sales"], errors="coerce") < 0).sum()
            if neg_sales > 0:
                issues.append(f"{neg_sales} rows with negative sales values")
            stats["sales_summary"] = {
                "min": round(float(df["sales"].min()), 2) if not df["sales"].isna().all() else 0,
                "max": round(float(df["sales"].max()), 2) if not df["sales"].isna().all() else 0,
                "mean": round(float(df["sales"].mean()), 2) if not df["sales"].isna().all() else 0,
            }

        if "quantity" in df.columns:
            null_qty = df["quantity"].isna().sum()
            if null_qty > 0:
                issues.append(f"{null_qty} rows with missing quantity values")

        null_total = df.isna().sum().sum()
        if null_total > 0:
            issues.append(f"{null_total} total null values across all columns")

        # Detect currency
        detected_currency = detect_currency_from_data(df) if missing == set() else "USD"
        stats["detected_currency"] = detected_currency
        stats["issues"] = issues
        stats["quality_score"] = max(0, 100 - len(issues) * 15)

        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 400


# ── Feature: Column Mapping Upload ───────────────────────────

@api_bp.route("/upload-mapped", methods=["POST"])
def api_upload_mapped():
    """Upload CSV with custom column mapping."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not _allowed_file(file.filename):
        return jsonify({"error": "Only CSV files are allowed"}), 400

    mapping_str = request.form.get("mapping", "{}")
    try:
        mapping = json.loads(mapping_str)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid column mapping"}), 400

    try:
        df = pd.read_csv(file)

        # Apply column mapping (source -> target)
        if mapping:
            rename_map = {v: k for k, v in mapping.items() if v in df.columns}
            df = df.rename(columns=rename_map)

        required = {"date", "sales", "quantity"}
        if not required.issubset(set(df.columns)):
            missing = required - set(df.columns)
            return jsonify({
                "error": f"After mapping, still missing: {', '.join(missing)}"
            }), 400

        source_currency = detect_currency_from_data(df)
        save_source_currency(source_currency)

        save_df = df.drop(columns=["currency"], errors="ignore")
        os.makedirs(DATA_DIR, exist_ok=True)
        data_path = os.path.join(DATA_DIR, "sales_data.csv")
        save_df.to_csv(data_path, index=False)

        # Reset cache
        _data_cache["mtime"] = None
        _data_cache["df"] = None

        return jsonify({
            "message": "Data uploaded with column mapping",
            "rows": len(df),
            "source_currency": source_currency,
        })
    except Exception as e:
        return jsonify({"error": f"Failed to process: {str(e)}"}), 400


# ── Feature: Download CSV ────────────────────────────────────

@api_bp.route("/download-csv")
def api_download_csv():
    """Download the current dataset as CSV."""
    data_path = os.path.join(DATA_DIR, "sales_data.csv")
    if not os.path.exists(data_path):
        return jsonify({"error": "No data file found"}), 404
    return send_file(
        data_path,
        mimetype="text/csv",
        as_attachment=True,
        download_name="sales_data.csv",
    )


# ── Feature: Share State via URL ─────────────────────────────

@api_bp.route("/share-state", methods=["POST"])
def api_share_state():
    """Generate a shareable state token (base64 encoded settings)."""
    import base64
    data = request.get_json() or {}
    state = {
        "currency": data.get("currency", "USD"),
        "date_from": data.get("date_from", ""),
        "date_to": data.get("date_to", ""),
        "page": data.get("page", "/"),
    }
    token = base64.urlsafe_b64encode(json.dumps(state).encode()).decode()
    return jsonify({"token": token})
