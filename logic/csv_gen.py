"""
CSV audit report generator for RSU Vitals.

Produces a multi-section CSV readable in Excel / Google Sheets:

  Section 1  — Report Metadata
  Section 2  — User Inputs
  Section 3  — Federal Tax Bracket Audit (Base Income only)
  Section 4  — Federal Tax Bracket Audit (Base + Total RSU Income)
  Section 5  — Tax Impact Summary
  Section 6  — Concentration Risk
  Section 7  — Full Vesting Schedule (one row per vest event)
"""

import io
from datetime import date

import pandas as pd

from logic.taxes import (
    STANDARD_DEDUCTIONS,
    calculate_federal_tax_detailed,
)


def _write_section(buf: io.StringIO, title: str, df: pd.DataFrame) -> None:
    """Write a titled section then a blank line into buf."""
    buf.write(f"SECTION: {title}\n")
    df.to_csv(buf, index=False)
    buf.write("\n")


def generate_csv_report(
    user_data: dict,
    results: dict,
    df_schedule: pd.DataFrame,
) -> bytes:
    """
    Build the full audit-trail CSV.

    Parameters
    ----------
    user_data   : dict with keys ticker, num_shares, grant_date, frequency,
                  income_bucket, state, filing_status, net_worth, price
    results     : dict with keys total_rsu_value, tax_impact, concentration
    df_schedule : DataFrame with columns date, shares, vest_number, value

    Returns
    -------
    UTF-8 encoded bytes suitable for st.download_button.
    """
    buf = io.StringIO()
    tax = results["tax_impact"]
    conc = results["concentration"]
    total_rsu_value = results["total_rsu_value"]
    filing_status = user_data["filing_status"]
    base_income = user_data.get("income_midpoint", tax.get("income_midpoint", 0))

    # ── Section 1: Report Metadata ────────────────────────────────────────────
    _write_section(buf, "Report Metadata", pd.DataFrame([
        {"Field": "Generated Date",        "Value": date.today().isoformat()},
        {"Field": "Ticker Symbol",          "Value": user_data["ticker"]},
        {"Field": "Share Price Used ($)",   "Value": f"{user_data['price']:,.2f}"},
        {"Field": "Report Type",            "Value": "RSU Vitals - Educational Estimate"},
        {"Field": "Tax Year Reference",     "Value": "2025"},
        {"Field": "Tax Calculation Method", "Value": tax.get("calculation_method", "bracket_estimate")},
    ]))

    # ── Section 2: User Inputs ────────────────────────────────────────────────
    _write_section(buf, "User Inputs", pd.DataFrame([
        {"Field": "Ticker Symbol",           "Value": user_data["ticker"]},
        {"Field": "Total Shares Granted",    "Value": user_data["num_shares"]},
        {"Field": "Grant Date",              "Value": str(user_data["grant_date"])},
        {"Field": "Vesting Frequency",       "Value": user_data["frequency"]},
        {"Field": "Annual Income Bucket",    "Value": user_data["income_bucket"]},
        {"Field": "Income Midpoint Used ($)","Value": f"{base_income:,.2f}"},
        {"Field": "State of Residence",      "Value": user_data["state"]},
        {"Field": "State Tax Rate (est.)",   "Value": f"{tax['state_rate'] * 100:.2f}%"},
        {"Field": "Filing Status",           "Value": filing_status},
        {"Field": "Standard Deduction ($)",  "Value": f"{tax['standard_deduction']:,}"},
        {"Field": "Total Net Worth ($)",     "Value": f"{user_data['net_worth']:,.2f}"},
        {"Field": "Share Price Used ($)",    "Value": f"{user_data['price']:,.2f}"},
        {"Field": "Total RSU Value ($)",     "Value": f"{total_rsu_value:,.2f}"},
    ]))

    # ── Section 3: Federal Bracket Audit — Base Income ───────────────────────
    base_brackets = calculate_federal_tax_detailed(base_income, filing_status)
    deduction = STANDARD_DEDUCTIONS.get(filing_status, 15_000)
    taxable_base = max(0.0, base_income - deduction)

    buf.write(f"SECTION: Federal Tax Bracket Audit - Base Income Only\n")
    buf.write(f"# Gross Income: ${base_income:,.2f}  |  Standard Deduction: ${deduction:,}  |  Taxable Income: ${taxable_base:,.2f}\n")
    pd.DataFrame(base_brackets, columns=[
        "bracket_number", "lower_bound", "upper_bound",
        "rate_pct", "income_in_bracket", "tax_from_bracket", "cumulative_tax",
    ]).rename(columns={
        "bracket_number":    "Bracket #",
        "lower_bound":       "Lower Bound ($)",
        "upper_bound":       "Upper Bound ($)",
        "rate_pct":          "Rate",
        "income_in_bracket": "Income in Bracket ($)",
        "tax_from_bracket":  "Tax from Bracket ($)",
        "cumulative_tax":    "Cumulative Tax ($)",
    }).to_csv(buf, index=False)
    buf.write("\n")

    # ── Section 4: Federal Bracket Audit — Base + RSU Income ─────────────────
    total_income = base_income + total_rsu_value
    total_brackets = calculate_federal_tax_detailed(total_income, filing_status)
    taxable_total = max(0.0, total_income - deduction)

    buf.write(f"SECTION: Federal Tax Bracket Audit - Base + Total RSU Income\n")
    buf.write(f"# Gross Income: ${total_income:,.2f}  |  Standard Deduction: ${deduction:,}  |  Taxable Income: ${taxable_total:,.2f}\n")
    pd.DataFrame(total_brackets, columns=[
        "bracket_number", "lower_bound", "upper_bound",
        "rate_pct", "income_in_bracket", "tax_from_bracket", "cumulative_tax",
    ]).rename(columns={
        "bracket_number":    "Bracket #",
        "lower_bound":       "Lower Bound ($)",
        "upper_bound":       "Upper Bound ($)",
        "rate_pct":          "Rate",
        "income_in_bracket": "Income in Bracket ($)",
        "tax_from_bracket":  "Tax from Bracket ($)",
        "cumulative_tax":    "Cumulative Tax ($)",
    }).to_csv(buf, index=False)
    buf.write("\n")

    # ── Section 5: Tax Impact Summary ────────────────────────────────────────
    federal_base_tax = base_brackets[-1]["cumulative_tax"] if base_brackets else 0
    federal_total_tax = total_brackets[-1]["cumulative_tax"] if total_brackets else 0

    # Recompute from the bracket audit rows above so the summary is internally consistent.
    incremental_federal  = federal_total_tax - federal_base_tax
    actual_liability_csv = incremental_federal + tax.get("additional_medicare_tax", 0) + tax["state_tax_on_rsu"]
    surprise_bill_csv    = actual_liability_csv - tax["statutory_withholding"]
    net_rsu_csv          = total_rsu_value - actual_liability_csv
    effective_rate_csv   = (actual_liability_csv / total_rsu_value) if total_rsu_value > 0 else 0.0

    _write_section(buf, "Tax Impact Summary", pd.DataFrame([
        {"Line Item": "Federal Tax on Base Income ($)",       "Amount": f"{federal_base_tax:,.2f}", "Notes": "Incremental; RSU not yet included"},
        {"Line Item": "Federal Tax on Base + RSU Income ($)", "Amount": f"{federal_total_tax:,.2f}", "Notes": "Full income including RSUs"},
        {"Line Item": "Incremental Federal Tax on RSUs ($)",  "Amount": f"{incremental_federal:,.2f}", "Notes": "Row above minus base federal tax"},
        {"Line Item": "State Tax on RSUs ($)",                "Amount": f"{tax['state_tax_on_rsu']:,.2f}", "Notes": f"{tax['state_rate']*100:.2f}% est. x RSU value"},
        {"Line Item": "Additional Medicare Tax (0.9%) ($)",   "Amount": f"{tax.get('additional_medicare_tax', 0):,.2f}", "Notes": "0.9% on W-2 income above $200K (Single)/$250K (MFJ). Applied in both tenforty and bracket paths."},
        {"Line Item": "Total Actual Tax Liability ($)",       "Amount": f"{actual_liability_csv:,.2f}", "Notes": "Federal income tax + Additional Medicare + State on RSU income"},
        {"Line Item": "Statutory Broker Withholding ($)",     "Amount": f"{tax['statutory_withholding']:,.2f}", "Notes": "22% flat withheld at vest by broker"},
        {"Line Item": "Surprise Tax Bill / Refund ($)",       "Amount": f"{surprise_bill_csv:,.2f}", "Notes": "Positive = you owe more at filing; negative = likely refund"},
        {"Line Item": "Net RSU Value After Tax ($)",          "Amount": f"{net_rsu_csv:,.2f}", "Notes": "Gross RSU value minus actual liability"},
        {"Line Item": "Effective Tax Rate on RSUs",           "Amount": f"{effective_rate_csv*100:.2f}%", "Notes": "Total actual liability / gross RSU value"},
        {"Line Item": "Marginal Federal Bracket",             "Amount": f"{tax['marginal_federal_rate']*100:.0f}%", "Notes": "Top bracket hit with RSU income included"},
    ]))

    # ── Section 6: Concentration Risk ────────────────────────────────────────
    _write_section(buf, "Concentration Risk", pd.DataFrame([
        {"Field": "Total RSU Value ($)",      "Value": f"{total_rsu_value:,.2f}"},
        {"Field": "Stated Net Worth ($)",     "Value": f"{user_data['net_worth']:,.2f}"},
        {"Field": "RSU Concentration (%)",    "Value": f"{conc['concentration_pct']:.2f}%"},
        {"Field": "Risk Level",               "Value": conc["warning_level"].capitalize()},
        {"Field": "10% Threshold Warning",    "Value": "YES" if conc["is_warning"] else "NO"},
        {"Field": "Guideline",                "Value": "Financial planners generally recommend <10% single-stock exposure"},
    ]))

    # ── Section 7: Full Vesting Schedule ─────────────────────────────────────
    sched = df_schedule.copy()
    sched["date"] = sched["date"].astype(str)
    sched["gross_value"] = sched["value"].round(2)

    # Pro-rata tax estimate per vest: scale actual_liability by shares fraction
    total_shares = sched["shares"].sum()
    sched["est_tax_per_vest"] = (
        (sched["shares"] / total_shares) * tax["actual_liability"]
    ).round(2)
    sched["est_net_per_vest"] = (sched["gross_value"] - sched["est_tax_per_vest"]).round(2)
    sched["share_price"] = user_data["price"]

    sched = sched.rename(columns={
        "date":             "Vest Date",
        "vest_number":      "Vest #",
        "shares":           "Shares Vesting",
        "share_price":      "Share Price ($)",
        "gross_value":      "Gross Value ($)",
        "est_tax_per_vest": "Est. Tax per Vest ($)",
        "est_net_per_vest": "Est. Net per Vest ($)",
    })[["Vest #", "Vest Date", "Shares Vesting", "Share Price ($)",
        "Gross Value ($)", "Est. Tax per Vest ($)", "Est. Net per Vest ($)"]]

    _write_section(buf, "Full Vesting Schedule (Pro-Rata Tax Estimates per Vest)", sched)

    # ── Disclaimer ────────────────────────────────────────────────────────────
    buf.write("DISCLAIMER\n")
    buf.write(
        '"This file is generated for educational purposes only and does not constitute '
        "financial, tax, or legal advice. All calculations are estimates based on 2025 "
        "U.S. federal tax brackets and flat-rate state estimates. Actual tax liability "
        "depends on your complete tax situation. Always consult a qualified CPA or "
        'financial advisor before making any decisions."\n'
    )

    # utf-8-sig adds the BOM so Excel auto-detects UTF-8 encoding correctly.
    return buf.getvalue().encode("utf-8-sig")
