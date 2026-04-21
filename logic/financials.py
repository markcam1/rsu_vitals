import pandas as pd
import yfinance as yf
from datetime import date
from dateutil.relativedelta import relativedelta

INCOME_BUCKETS = {
    "Under $100K":    75_000,
    "$100K–$200K":   150_000,
    "$200K–$400K":   300_000,
    "$400K–$600K":   500_000,
    "Over $600K":    750_000,
}

FREQUENCY_MONTHS = {
    "Monthly":   1,
    "Quarterly": 3,
    "Annually":  12,
}


def fetch_stock_price(ticker: str) -> dict:
    """
    Fetch the current price for ticker via yfinance.
    Returns {"success": bool, "price": float|None, "error": str|None}.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        price = stock.fast_info.get("lastPrice")
        if price is None:
            hist = stock.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        if price:
            return {"success": True, "price": round(float(price), 2), "error": None}
        return {"success": False, "price": None, "error": "No price data returned."}
    except Exception as e:
        return {"success": False, "price": None, "error": str(e)}


def generate_vesting_schedule(
    grant_date: date,
    total_shares: int,
    frequency: str,
) -> pd.DataFrame:
    """
    Generate a 4-year (48-month) linear vesting schedule with no cliff.

    Returns a DataFrame with columns:
        date        - vest date
        shares      - shares vesting on that date
        vest_number - sequential vest event index (1-based)
    """
    interval = FREQUENCY_MONTHS.get(frequency, 3)
    total_months = 48
    num_events = total_months // interval
    shares_per_event = total_shares / num_events

    rows = []
    current_date = grant_date
    for i in range(1, num_events + 1):
        current_date = current_date + relativedelta(months=interval)
        rows.append({
            "date": current_date,
            "shares": shares_per_event,
            "vest_number": i,
        })

    return pd.DataFrame(rows)


def calculate_concentration(rsu_value: float, net_worth: float) -> dict:
    """
    Calculate single-stock concentration risk.

    Returns:
        concentration_pct   - percentage (0–100)
        is_warning          - True if > 10%
        warning_level       - "safe" | "caution" | "danger"
    """
    if net_worth <= 0:
        return {"concentration_pct": 0.0, "is_warning": False, "warning_level": "safe"}

    pct = (rsu_value / net_worth) * 100
    pct = round(pct, 2)

    if pct > 25:
        level = "danger"
    elif pct > 10:
        level = "caution"
    else:
        level = "safe"

    return {
        "concentration_pct": pct,
        "is_warning": pct > 10,
        "warning_level": level,
    }


def get_income_midpoint(bucket_label: str) -> float:
    """Return the midpoint float for a given income bucket label."""
    return INCOME_BUCKETS.get(bucket_label, 150_000)
