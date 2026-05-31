"""
Generates realistic sample sales data for demonstration purposes.
Simulates 3 years of daily sales across multiple product categories and regions.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def generate_sample_data() -> pd.DataFrame:
    np.random.seed(42)

    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 31)
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    categories = ["Electronics", "Clothing", "Home & Garden", "Sports", "Books"]
    regions = ["North America", "Europe", "Asia Pacific", "Latin America", "Africa"]

    records = []

    for date in date_range:
        day_of_year = date.timetuple().tm_yday
        month = date.month
        year = date.year

        # Seasonal pattern: higher sales in Q4 (holiday season)
        seasonal_factor = 1 + 0.4 * np.sin(2 * np.pi * (day_of_year - 60) / 365)

        # Year-over-year growth trend (15% annual growth)
        year_factor = 1 + 0.15 * (year - 2023)

        # Weekend boost
        weekend_factor = 1.2 if date.weekday() >= 5 else 1.0

        # Monthly spikes (Black Friday, Christmas, etc.)
        holiday_factor = 1.0
        if month == 11 and date.day >= 20:
            holiday_factor = 1.8
        elif month == 12 and date.day <= 25:
            holiday_factor = 1.6
        elif month == 1 and date.day <= 7:
            holiday_factor = 1.3

        num_transactions = np.random.randint(2, 5)
        for _ in range(num_transactions):
            category = np.random.choice(categories, p=[0.30, 0.25, 0.20, 0.15, 0.10])
            region = np.random.choice(regions, p=[0.35, 0.25, 0.20, 0.12, 0.08])

            # Category-specific base prices
            base_prices = {
                "Electronics": np.random.uniform(150, 800),
                "Clothing": np.random.uniform(25, 200),
                "Home & Garden": np.random.uniform(40, 350),
                "Sports": np.random.uniform(30, 250),
                "Books": np.random.uniform(10, 50),
            }

            base_price = base_prices[category]
            quantity = np.random.randint(1, 6)

            sale_amount = (
                base_price
                * quantity
                * seasonal_factor
                * year_factor
                * weekend_factor
                * holiday_factor
                * np.random.uniform(0.85, 1.15)
            )

            records.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "category": category,
                    "region": region,
                    "quantity": quantity,
                    "unit_price": round(base_price, 2),
                    "sales": round(sale_amount, 2),
                }
            )

    df = pd.DataFrame(records)
    return df


def save_sample_data(filepath: str):
    df = generate_sample_data()
    df.to_csv(filepath, index=False)
    return df
