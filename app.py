import streamlit as st

from logic.financials import fetch_stock_price, generate_vesting_schedule, calculate_concentration
from logic.taxes import calculate_rsu_tax_impact
from logic.pdf_gen import generate_pdf_report
from logic.csv_gen import generate_csv_report
from components.charts import create_cliff_chart, create_tax_donut_chart, create_concentration_gauge
from components.ui import show_disclaimer, render_sidebar_inputs, show_email_gate, show_footer

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RSU Vitals",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Mono', 'Roboto Mono', 'Courier New', monospace !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
}

button[kind="primary"], .stDownloadButton > button {
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    border-radius: 4px !important;
    transition: all 0.2s ease-in-out !important;
}

*:focus-visible {
    outline: 2px solid #2563eb !important;
    outline-offset: 2px !important;
}

html { scroll-behavior: smooth; }
</style>
""", unsafe_allow_html=True)

# ── Session State Init ────────────────────────────────────────────────────────
for key, default in [
    ("disclaimer_accepted", False),
    ("email_captured", False),
    ("email_value", ""),
    ("pdf_bytes", None),
    ("csv_bytes", None),
    ("last_inputs_key", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Disclaimer Gate ───────────────────────────────────────────────────────────
# show_disclaimer() calls st.stop() until accepted; also renders footer.
show_disclaimer()

# ── Sidebar Inputs ────────────────────────────────────────────────────────────
inputs = render_sidebar_inputs()

# ── Main Header ───────────────────────────────────────────────────────────────
st.title("📈 RSU Vitals")
st.subheader("Your Personal Risk & Tax Impact Analysis")
st.markdown(
    "Enter your RSU grant details in the sidebar, then hit **Calculate** to see your results.",
    help="All calculations are educational estimates. See footer for full disclaimer.",
)

calculate = st.sidebar.button("Calculate", type="primary", use_container_width=True)

if not calculate and st.session_state["pdf_bytes"] is None:
    st.info("Fill in your grant details in the sidebar and click **Calculate** to get started.")
    show_footer()
    st.stop()

# ── Stock Price Fetch ─────────────────────────────────────────────────────────
ticker = inputs["ticker"]
if not ticker:
    st.error("Please enter a ticker symbol.")
    show_footer()
    st.stop()

with st.spinner(f"Fetching live price for {ticker}..."):
    price_result = fetch_stock_price(ticker)

if price_result["success"]:
    price = price_result["price"]
    st.success(f"Live price for **{ticker}**: ${price:,.2f}")
    # Method badge rendered after tax_impact is computed (see below)
else:
    st.warning(
        f"Could not fetch a live price for **{ticker}** "
        f"({price_result.get('error', 'unknown error')}). Enter it manually:"
    )
    price = st.number_input("Share Price ($)", min_value=0.01, value=100.0, step=1.0)
    if price <= 0:
        show_footer()
        st.stop()

# ── Computations ──────────────────────────────────────────────────────────────
df_schedule = generate_vesting_schedule(inputs["grant_date"], inputs["num_shares"], inputs["frequency"])
df_schedule["value"] = df_schedule["shares"] * price

total_rsu_value = float(df_schedule["value"].sum())

tax_impact = calculate_rsu_tax_impact(
    base_income=inputs["income_midpoint"],
    rsu_value=total_rsu_value,
    filing_status=inputs["filing_status"],
    state_name=inputs["state"],
)

concentration = calculate_concentration(total_rsu_value, inputs["net_worth"])

# ── Calculation method badge ──────────────────────────────────────────────────
if tax_impact["calculation_method"] == "tenforty":
    st.caption("Tax engine: **tenforty** — real bracket logic (federal + state + Additional Medicare Tax)")
else:
    st.caption(f"Tax engine: **flat-rate estimate** — {inputs['state']} not yet in tenforty; using top marginal rate")

# ── Charts ────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 1.2, 1])

with col1:
    st.plotly_chart(create_cliff_chart(df_schedule), use_container_width=True)

with col2:
    st.plotly_chart(create_tax_donut_chart(tax_impact), use_container_width=True)

    # Key metrics
    st.metric(
        "Statutory Withholding (22%)",
        f"${tax_impact['statutory_withholding']:,.0f}",
        help="What your broker withholds at vest — often not enough.",
    )
    surprise = tax_impact["surprise_bill"]
    delta_str = f"{'You may owe' if surprise >= 0 else 'Possible refund'}: ${abs(surprise):,.0f}"
    st.metric(
        "Actual Tax Liability (Fed + State)",
        f"${tax_impact['actual_liability']:,.0f}",
        delta=delta_str,
        delta_color="inverse" if surprise > 0 else "normal",
    )
    st.metric(
        "Effective Rate on RSUs",
        f"{tax_impact['effective_rate_on_rsu'] * 100:.1f}%",
    )

with col3:
    st.plotly_chart(create_concentration_gauge(
        concentration["concentration_pct"],
        concentration["warning_level"],
    ), use_container_width=True)

    level = concentration["warning_level"]
    pct = concentration["concentration_pct"]
    if pct > 100:
        st.error(
            f"**Extreme Concentration:** Your unvested RSUs ({pct:.1f}% of stated net worth) "
            "exceed your total stated net worth. Note: if your net worth figure already includes "
            "vested shares, this percentage will be overstated."
        )
    elif level == "danger":
        st.error(
            f"**Danger:** Unvested RSUs are {pct:.1f}% of your net worth. "
            "Planners recommend keeping single-stock exposure below 10%."
        )
    elif level == "caution":
        st.warning(
            f"**Caution:** Unvested RSUs are {pct:.1f}% of your net worth. "
            "Consider whether this concentration aligns with your risk tolerance."
        )
    else:
        st.success(f"Unvested RSUs are {pct:.1f}% of net worth — within the 10% guideline.")

# ── Tax Breakdown Expander ────────────────────────────────────────────────────
st.markdown("---")
with st.expander("Tax Breakdown Details", expanded=False):
    breakdown_col1, breakdown_col2 = st.columns(2)

    with breakdown_col1:
        st.markdown("**Inputs Used**")
        st.write({
            "Filing Status":       inputs["filing_status"],
            "Annual Income":       f"${inputs['income_midpoint']:,.0f} (midpoint of {inputs['income_bucket']})",
            "State":               inputs["state"],
            "State Rate (est.)":   f"{tax_impact['state_rate'] * 100:.2f}%",
            "Total RSU Value":     f"${total_rsu_value:,.2f}",
            "Standard Deduction":  f"${tax_impact['standard_deduction']:,}",
            "Tax Engine":          tax_impact["calculation_method"],
        })

    with breakdown_col2:
        st.markdown("**Tax Calculation**")
        breakdown = {
            "Statutory Withholding (22%)": f"${tax_impact['statutory_withholding']:,.2f}",
            "Federal Tax on RSUs":         f"${tax_impact['federal_tax_on_rsu']:,.2f}",
            "State Tax on RSUs":           f"${tax_impact['state_tax_on_rsu']:,.2f}",
            "Total Actual Liability":      f"${tax_impact['actual_liability']:,.2f}",
            "Surprise Bill / Refund":      f"${tax_impact['surprise_bill']:,.2f}",
            "Marginal Federal Bracket":    f"{tax_impact['marginal_federal_rate'] * 100:.0f}%",
        }
        if tax_impact["additional_medicare_tax"] > 0:
            breakdown["Additional Medicare Tax (0.9%)"] = f"${tax_impact['additional_medicare_tax']:,.2f}"
        st.write(breakdown)

# ── PDF Generation & Email Gate ──────────────────────────────────────────────
st.markdown("---")

# Build or retrieve cached PDF bytes
inputs_key = (ticker, inputs["num_shares"], str(inputs["grant_date"]),
              inputs["frequency"], inputs["income_bucket"], inputs["state"],
              inputs["filing_status"], inputs["net_worth"], price)

if st.session_state["last_inputs_key"] != inputs_key:
    user_data = {
        "ticker":          ticker,
        "num_shares":      inputs["num_shares"],
        "grant_date":      inputs["grant_date"],
        "frequency":       inputs["frequency"],
        "income_bucket":   inputs["income_bucket"],
        "income_midpoint": inputs["income_midpoint"],
        "state":           inputs["state"],
        "filing_status":   inputs["filing_status"],
        "net_worth":       inputs["net_worth"],
        "price":           price,
    }
    results = {
        "total_rsu_value": total_rsu_value,
        "tax_impact":      tax_impact,
        "concentration":   concentration,
    }
    st.session_state["pdf_bytes"] = generate_pdf_report(user_data, results)
    st.session_state["csv_bytes"] = generate_csv_report(user_data, results, df_schedule)
    st.session_state["last_inputs_key"] = inputs_key
    st.session_state["email_captured"] = False  # Reset gate if inputs changed

show_email_gate(st.session_state["pdf_bytes"], st.session_state["csv_bytes"])

# ── Footer ────────────────────────────────────────────────────────────────────
show_footer()
