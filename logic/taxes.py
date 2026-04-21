# 2025 Federal Income Tax Brackets
# Source: IRS Rev. Proc. 2024-40
#
# State rates are flat educational estimates using each state's top marginal rate.
# For states not supported by tenforty, the flat rate is used as a fallback.
# These are for educational estimation only — actual liability depends on your full
# tax situation, deductions, and local taxes not modeled here.

# Standard deductions 2025
STANDARD_DEDUCTIONS = {
    "Single": 15_000,
    "Married Filing Jointly": 30_000,
}

# Brackets: list of (upper_limit, rate). Last entry uses float('inf').
FEDERAL_BRACKETS = {
    "Single": [
        (11_925,       0.10),
        (48_475,       0.12),
        (103_350,      0.22),
        (197_300,      0.24),
        (250_525,      0.32),
        (626_350,      0.35),
        (float("inf"), 0.37),
    ],
    "Married Filing Jointly": [
        (23_850,       0.10),
        (96_950,       0.12),
        (206_700,      0.22),
        (394_600,      0.24),
        (501_050,      0.32),
        (751_600,      0.35),
        (float("inf"), 0.37),
    ],
}

# State flat-rate estimates (top marginal, educational purposes only).
# Used as fallback for states not covered by tenforty.
# No-income-tax states = 0.0.
# Notes:
#   CA  12.3% applies to ~$677K–$1M; 13.3% above $1M. Using 12.3% for most users.
#   NY  8.82% is state-only; NYC residents add ~3.876% local (not modeled).
#   MD  5.75% is state-only; county/local typically adds 2.25–3.2% (not modeled).
#   NJ  10.75% applies above $1M; 8.97% is the more common top rate — using 10.75% conservatively.
#   DC  Top bracket 10.75% above $1M; 8.5% more common — using 10.75% conservatively.
#   WA  No wage income tax. 7% capital gains tax does NOT apply to RSU W-2 income.
#   NH  No tax on wages (phased out Hall Tax).
#   LA  3.0% flat effective 2025 (passed Nov 2024).
#   ND  2.5% flat effective 2024.
STATE_TAX_RATES = {
    # No income tax
    "Alaska":         0.000,
    "Florida":        0.000,
    "Nevada":         0.000,
    "New Hampshire":  0.000,
    "South Dakota":   0.000,
    "Tennessee":      0.000,
    "Texas":          0.000,
    "Washington":     0.000,
    "Wyoming":        0.000,
    # Flat-rate states
    "Arizona":        0.025,
    "Colorado":       0.044,
    "Georgia":        0.0549,
    "Illinois":       0.0495,
    "Indiana":        0.0305,
    "Kentucky":       0.040,
    "Massachusetts":  0.050,
    "Michigan":       0.0425,
    "North Carolina": 0.045,
    "Pennsylvania":   0.0307,
    "Utah":           0.0465,
    # Graduated — top marginal used
    "Alabama":        0.050,
    "Arkansas":       0.044,
    "California":     0.123,
    "Connecticut":    0.0699,
    "Delaware":       0.066,
    "Hawaii":         0.110,
    "Idaho":          0.058,
    "Iowa":           0.057,
    "Kansas":         0.057,
    "Louisiana":      0.030,
    "Maine":          0.0715,
    "Maryland":       0.0575,
    "Minnesota":      0.0985,
    "Mississippi":    0.047,
    "Missouri":       0.048,
    "Montana":        0.059,
    "Nebraska":       0.0664,
    "New Jersey":     0.1075,
    "New Mexico":     0.059,
    "New York":       0.0882,
    "North Dakota":   0.025,
    "Ohio":           0.035,
    "Oklahoma":       0.0475,
    "Oregon":         0.099,
    "Rhode Island":   0.0599,
    "South Carolina": 0.064,
    "Vermont":        0.0875,
    "Virginia":       0.0575,
    "Washington DC":  0.1075,
    "West Virginia":  0.065,
    "Wisconsin":      0.0765,
}

# ── Tenforty integration ──────────────────────────────────────────────────────
# tenforty supports real bracket-based state logic for these states.
# All others fall back to _calculate_rsu_tax_bracket() using flat-rate estimates.
# tenforty does not run on Windows natively — requires WSL2 or Linux.
TENFORTY_INCOME_TAX_STATES = {
    "Arizona", "California", "Massachusetts", "Michigan",
    "North Carolina", "New Jersey", "New York", "Ohio",
    "Oregon", "Pennsylvania", "Virginia",
}
TENFORTY_NO_TAX_STATES = {
    "Alaska", "Florida", "Nevada", "South Dakota",
    "Tennessee", "Texas", "Washington", "Wyoming",
}
TENFORTY_STATE_CODES = {
    "Arizona": "AZ", "California": "CA", "Massachusetts": "MA",
    "Michigan": "MI", "North Carolina": "NC", "New Jersey": "NJ",
    "New York": "NY", "Ohio": "OH", "Oregon": "OR",
    "Pennsylvania": "PA", "Virginia": "VA",
    "Alaska": "AK", "Florida": "FL", "Nevada": "NV",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Washington": "WA", "Wyoming": "WY",
}
TENFORTY_FILING_STATUS = {
    "Single": "Single",
    "Married Filing Jointly": "Married/Joint",
}


def calculate_federal_tax_detailed(gross_income: float, filing_status: str) -> list[dict]:
    """
    Return a row-by-row breakdown of how federal tax is computed across brackets.

    Each dict has:
        bracket_number, lower_bound, upper_bound, rate_pct,
        income_in_bracket, tax_from_bracket, cumulative_tax
    """
    deduction = STANDARD_DEDUCTIONS.get(filing_status, 15_000)
    taxable = max(0.0, gross_income - deduction)

    rows = []
    prev_limit = 0.0
    cumulative = 0.0

    for i, (limit, rate) in enumerate(FEDERAL_BRACKETS[filing_status], start=1):
        upper = limit if limit != float("inf") else taxable
        income_in = max(0.0, min(taxable, upper) - prev_limit)
        tax_from = income_in * rate
        cumulative += tax_from

        rows.append({
            "bracket_number":    i,
            "lower_bound":       prev_limit,
            "upper_bound":       limit if limit != float("inf") else "No limit",
            "rate_pct":          f"{rate * 100:.0f}%",
            "income_in_bracket": round(income_in, 2),
            "tax_from_bracket":  round(tax_from, 2),
            "cumulative_tax":    round(cumulative, 2),
        })

        prev_limit = limit
        if taxable <= limit:
            break

    return rows


def calculate_federal_tax(gross_income: float, filing_status: str) -> float:
    """Return total 2025 federal income tax for gross_income after standard deduction."""
    deduction = STANDARD_DEDUCTIONS.get(filing_status, 15_000)
    taxable = max(0.0, gross_income - deduction)

    tax = 0.0
    prev_limit = 0.0
    for limit, rate in FEDERAL_BRACKETS[filing_status]:
        if taxable <= limit:
            tax += (taxable - prev_limit) * rate
            break
        tax += (limit - prev_limit) * rate
        prev_limit = limit

    return round(tax, 2)


def calculate_marginal_rate(gross_income: float, filing_status: str) -> float:
    """Return the marginal federal bracket rate (0.0–1.0) for the top dollar of gross_income."""
    deduction = STANDARD_DEDUCTIONS.get(filing_status, 15_000)
    taxable = max(0.0, gross_income - deduction)

    prev_limit = 0.0
    for limit, rate in FEDERAL_BRACKETS[filing_status]:
        if taxable <= limit:
            return rate
        prev_limit = limit
    return 0.37


def get_state_rate(state_name: str) -> float:
    """Return the flat educational state tax rate for state_name."""
    return STATE_TAX_RATES.get(state_name, 0.0)


AMT_THRESHOLDS = {
    "Single":                 200_000,
    "Married Filing Jointly": 250_000,
}
AMT_RATE = 0.009


def _calculate_additional_medicare_tax(gross_income: float, filing_status: str) -> float:
    """Return the 0.9% Additional Medicare Tax on W-2 income above the filing-status threshold."""
    threshold = AMT_THRESHOLDS.get(filing_status, 200_000)
    return max(0.0, gross_income - threshold) * AMT_RATE


def _calculate_rsu_tax_bracket(
    base_income: float,
    rsu_value: float,
    filing_status: str,
    state_rate: float,
) -> dict:
    """
    Bracket-math fallback for calculate_rsu_tax_impact().
    Used when the user's state is not supported by tenforty, or when
    tenforty is unavailable (e.g. Windows environment without WSL).
    """
    federal_base = calculate_federal_tax(base_income, filing_status)
    federal_total = calculate_federal_tax(base_income + rsu_value, filing_status)

    federal_tax_on_rsu = federal_total - federal_base
    additional_medicare_tax = (
        _calculate_additional_medicare_tax(base_income + rsu_value, filing_status)
        - _calculate_additional_medicare_tax(base_income, filing_status)
    )
    state_tax_on_rsu = rsu_value * state_rate
    statutory_withholding = rsu_value * 0.22

    actual_liability = federal_tax_on_rsu + additional_medicare_tax + state_tax_on_rsu
    surprise_bill = actual_liability - statutory_withholding
    effective_rate = (actual_liability / rsu_value) if rsu_value > 0 else 0.0

    return {
        "rsu_value":               rsu_value,
        "statutory_withholding":   round(statutory_withholding, 2),
        "federal_tax_on_rsu":      round(federal_tax_on_rsu, 2),
        "additional_medicare_tax": round(additional_medicare_tax, 2),
        "state_tax_on_rsu":        round(state_tax_on_rsu, 2),
        "actual_liability":        round(actual_liability, 2),
        "surprise_bill":           round(surprise_bill, 2),
        "effective_rate_on_rsu":   round(effective_rate, 4),
        "marginal_federal_rate":   calculate_marginal_rate(base_income + rsu_value, filing_status),
        "state_rate":              state_rate,
        "standard_deduction":      STANDARD_DEDUCTIONS.get(filing_status, 15_000),
        "calculation_method":      "bracket_estimate",
    }


def calculate_rsu_tax_impact(
    base_income: float,
    rsu_value: float,
    filing_status: str,
    state_name: str,
) -> dict:
    """
    Calculate the full tax impact of an RSU vest on top of base_income.

    Tries tenforty first for supported states (real bracket-based logic including
    Additional Medicare Tax). Falls back to bracket-math estimate for all other
    states or if tenforty is unavailable (e.g. Windows without WSL2).

    Returns a dict with:
        rsu_value               - gross RSU value
        statutory_withholding   - 22% flat broker withholding
        federal_tax_on_rsu      - incremental federal income tax
        additional_medicare_tax - 0.9% delta (tenforty only; 0.0 in fallback)
        state_tax_on_rsu        - incremental state tax
        actual_liability        - federal + additional_medicare + state
        surprise_bill           - actual_liability - statutory_withholding
        effective_rate_on_rsu   - actual_liability / rsu_value
        marginal_federal_rate   - top bracket hit with RSU income
        state_rate              - flat rate used for display
        standard_deduction      - deduction applied
        calculation_method      - "tenforty" | "bracket_estimate"
    """
    use_tenforty = state_name in TENFORTY_INCOME_TAX_STATES or state_name in TENFORTY_NO_TAX_STATES

    if use_tenforty:
        try:
            from tenforty import evaluate_return

            tf_status  = TENFORTY_FILING_STATUS.get(filing_status, "Single")
            state_code = TENFORTY_STATE_CODES[state_name]

            base  = evaluate_return(year=2025, w2_income=base_income,
                                    state=state_code, filing_status=tf_status).model_dump()
            total = evaluate_return(year=2025, w2_income=base_income + rsu_value,
                                    state=state_code, filing_status=tf_status).model_dump()

            federal_tax_on_rsu      = total["federal_income_tax"]              - base["federal_income_tax"]
            additional_medicare_tax = total["federal_additional_medicare_tax"]  - base["federal_additional_medicare_tax"]
            state_tax_on_rsu        = total["state_total_tax"]                  - base["state_total_tax"]

            actual_liability  = federal_tax_on_rsu + additional_medicare_tax + state_tax_on_rsu
            statutory         = rsu_value * 0.22
            surprise_bill     = actual_liability - statutory
            effective_rate    = (actual_liability / rsu_value) if rsu_value > 0 else 0.0

            # marginal_federal_rate from tenforty is the bracket rate (e.g. 0.37)
            marginal = total.get("federal_tax_bracket", calculate_marginal_rate(base_income + rsu_value, filing_status))

            return {
                "rsu_value":               rsu_value,
                "statutory_withholding":   round(statutory, 2),
                "federal_tax_on_rsu":      round(federal_tax_on_rsu, 2),
                "additional_medicare_tax": round(additional_medicare_tax, 2),
                "state_tax_on_rsu":        round(state_tax_on_rsu, 2),
                "actual_liability":        round(actual_liability, 2),
                "surprise_bill":           round(surprise_bill, 2),
                "effective_rate_on_rsu":   round(effective_rate, 4),
                "marginal_federal_rate":   marginal,
                "state_rate":              get_state_rate(state_name),
                "standard_deduction":      STANDARD_DEDUCTIONS.get(filing_status, 15_000),
                "calculation_method":      "tenforty",
            }

        except Exception:
            pass  # fall through to bracket fallback

    return _calculate_rsu_tax_bracket(
        base_income, rsu_value, filing_status, get_state_rate(state_name)
    )
