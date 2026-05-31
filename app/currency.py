"""
Currency conversion module.
Stores exchange rates (relative to USD) and provides conversion utilities.
"""

import json
import os

# Exchange rates: 1 USD = X of target currency
EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.50,
    "CAD": 1.36,
    "AUD": 1.53,
    "CHF": 0.88,
    "CNY": 7.24,
    "INR": 83.12,
    "NGN": 1550.00,
    "ZAR": 18.65,
    "BRL": 4.97,
    "MXN": 17.15,
    "KRW": 1325.00,
    "SGD": 1.34,
    "HKD": 7.82,
    "SEK": 10.45,
    "NOK": 10.58,
    "DKK": 6.88,
    "NZD": 1.63,
    "AED": 3.67,
    "SAR": 3.75,
    "KES": 153.50,
    "GHS": 12.50,
    "EGP": 30.90,
    "TRY": 27.50,
    "PLN": 4.05,
    "THB": 35.20,
    "MYR": 4.65,
    "PHP": 56.10,
    "IDR": 15450.00,
    "TWD": 31.50,
    "COP": 3950.00,
    "ARS": 350.00,
    "CLP": 890.00,
    "PEN": 3.72,
}

CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CAD": "C$",
    "AUD": "A$", "CHF": "CHF", "CNY": "¥", "INR": "₹", "NGN": "₦",
    "ZAR": "R", "BRL": "R$", "MXN": "MX$", "KRW": "₩", "SGD": "S$",
    "HKD": "HK$", "SEK": "kr", "NOK": "kr", "DKK": "kr", "NZD": "NZ$",
    "AED": "د.إ", "SAR": "﷼", "KES": "KSh", "GHS": "₵", "EGP": "E£",
    "TRY": "₺", "PLN": "zł", "THB": "฿", "MYR": "RM", "PHP": "₱",
    "IDR": "Rp", "TWD": "NT$", "COP": "COL$", "ARS": "AR$", "CLP": "CL$",
    "PEN": "S/.",
}

CURRENCY_NAMES = {
    "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound",
    "JPY": "Japanese Yen", "CAD": "Canadian Dollar", "AUD": "Australian Dollar",
    "CHF": "Swiss Franc", "CNY": "Chinese Yuan", "INR": "Indian Rupee",
    "NGN": "Nigerian Naira", "ZAR": "South African Rand", "BRL": "Brazilian Real",
    "MXN": "Mexican Peso", "KRW": "South Korean Won", "SGD": "Singapore Dollar",
    "HKD": "Hong Kong Dollar", "SEK": "Swedish Krona", "NOK": "Norwegian Krone",
    "DKK": "Danish Krone", "NZD": "New Zealand Dollar", "AED": "UAE Dirham",
    "SAR": "Saudi Riyal", "KES": "Kenyan Shilling", "GHS": "Ghanaian Cedi",
    "EGP": "Egyptian Pound", "TRY": "Turkish Lira", "PLN": "Polish Zloty",
    "THB": "Thai Baht", "MYR": "Malaysian Ringgit", "PHP": "Philippine Peso",
    "IDR": "Indonesian Rupiah", "TWD": "Taiwan Dollar", "COP": "Colombian Peso",
    "ARS": "Argentine Peso", "CLP": "Chilean Peso", "PEN": "Peruvian Sol",
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CURRENCY_META_FILE = os.path.join(DATA_DIR, "currency_meta.json")


def get_supported_currencies():
    """Return list of supported currencies with their info."""
    return [
        {
            "code": code,
            "name": CURRENCY_NAMES.get(code, code),
            "symbol": CURRENCY_SYMBOLS.get(code, code),
            "rate": rate,
        }
        for code, rate in sorted(EXCHANGE_RATES.items())
    ]


def convert(amount, from_currency, to_currency):
    """Convert an amount from one currency to another."""
    if from_currency == to_currency:
        return amount
    # Convert to USD first, then to target
    usd_amount = amount / EXCHANGE_RATES.get(from_currency, 1.0)
    return usd_amount * EXCHANGE_RATES.get(to_currency, 1.0)


def detect_currency_from_data(df):
    """Detect the currency from a DataFrame. Checks for a 'currency' column."""
    if "currency" in df.columns:
        currencies = df["currency"].dropna().unique()
        if len(currencies) == 1:
            code = currencies[0].upper().strip()
            if code in EXCHANGE_RATES:
                return code
        elif len(currencies) > 1:
            # Multiple currencies — take the most common one
            code = df["currency"].mode().iloc[0].upper().strip()
            if code in EXCHANGE_RATES:
                return code
    return "USD"


def save_source_currency(currency_code):
    """Save the source currency of the current dataset."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CURRENCY_META_FILE, "w") as f:
        json.dump({"source_currency": currency_code}, f)


def get_source_currency():
    """Get the source currency of the current dataset."""
    if os.path.exists(CURRENCY_META_FILE):
        with open(CURRENCY_META_FILE, "r") as f:
            meta = json.load(f)
            return meta.get("source_currency", "USD")
    return "USD"
