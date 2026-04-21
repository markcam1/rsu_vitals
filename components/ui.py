import streamlit as st
from datetime import date, timedelta
from logic.financials import INCOME_BUCKETS, get_income_midpoint
from logic.taxes import STATE_TAX_RATES

INCOME_BUCKET_LABELS = list(INCOME_BUCKETS.keys())
STATE_NAMES = sorted(STATE_TAX_RATES.keys())


def show_disclaimer() -> None:
    """
    Render a mandatory legal disclaimer modal.
    Blocks all app content (via st.stop()) until the user clicks through.
    The footer is shown even on this screen.
    """
    if "disclaimer_accepted" not in st.session_state:
        st.session_state["disclaimer_accepted"] = False

    if not st.session_state["disclaimer_accepted"]:
        st.warning(
            "### Before You Continue\n\n"
            "**RSU Vitals is an educational calculator — not financial, tax, or legal advice.**\n\n"
            "- Tax calculations are estimates based on 2025 U.S. federal brackets and flat-rate state estimates.\n"
            "- Your actual tax liability will differ based on your complete financial picture, deductions, and local taxes.\n"
            "- Do not make investment or tax decisions based solely on this tool.\n"
            "- Always consult a qualified CPA or financial advisor."
        )
        if st.button("I Understand This Is Not Financial Advice", type="primary"):
            st.session_state["disclaimer_accepted"] = True
            st.rerun()
        show_footer()
        st.stop()


def render_sidebar_inputs() -> dict:
    """
    Render all sidebar input widgets and return a dict of values.

    Keys returned:
        ticker, num_shares, grant_date, frequency, income_bucket,
        income_midpoint, state, net_worth, filing_status
    """
    st.sidebar.header("RSU Grant Details")

    ticker = st.sidebar.text_input(
        "Ticker Symbol",
        value="AAPL",
        max_chars=5,
        help="e.g. AAPL, GOOGL, MSFT",
    ).upper().strip()

    num_shares = st.sidebar.number_input(
        "Number of Shares",
        min_value=1,
        value=1_000,
        step=100,
    )

    default_grant = date.today() - timedelta(days=365)
    grant_date = st.sidebar.date_input(
        "Grant Date",
        value=default_grant,
        help="The date your RSU grant was awarded.",
    )

    frequency = st.sidebar.selectbox(
        "Vesting Frequency",
        options=["Monthly", "Quarterly", "Annually"],
        index=1,
    )

    st.sidebar.header("Personal Financials")

    income_bucket = st.sidebar.select_slider(
        "Annual Gross Income",
        options=INCOME_BUCKET_LABELS,
        value="$100K–$200K",
        help="Select the range closest to your annual W-2 income (excluding RSUs).",
    )
    income_midpoint = get_income_midpoint(income_bucket)
    st.sidebar.caption(f"Using midpoint: ${income_midpoint:,.0f} for calculations")

    state = st.sidebar.selectbox(
        "State of Residence",
        options=STATE_NAMES,
        index=STATE_NAMES.index("California") if "California" in STATE_NAMES else 0,
        help="Used to estimate state income tax on your RSU income.",
    )

    net_worth = st.sidebar.number_input(
        "Total Net Worth ($)",
        min_value=0,
        value=500_000,
        step=50_000,
        help="Approximate total net worth (used for concentration risk only).",
    )

    filing_status = st.sidebar.radio(
        "Filing Status",
        options=["Single", "Married Filing Jointly"],
        index=0,
    )

    return {
        "ticker":         ticker,
        "num_shares":     int(num_shares),
        "grant_date":     grant_date,
        "frequency":      frequency,
        "income_bucket":  income_bucket,
        "income_midpoint": income_midpoint,
        "state":          state,
        "net_worth":      float(net_worth),
        "filing_status":  filing_status,
    }


def show_email_gate(pdf_bytes: bytes, csv_bytes: bytes) -> None:
    """
    Render email capture form gated in front of the download buttons.
    On submission, calls Mailchimp and reveals both PDF and CSV downloads.
    """
    from integrations.mailchimp import subscribe_email

    if "email_captured" not in st.session_state:
        st.session_state["email_captured"] = False
    if "email_value" not in st.session_state:
        st.session_state["email_value"] = ""

    st.subheader("Download Your Summary Report")
    st.write("Enter your email to unlock your reports. We'll send you occasional RSU planning tips — unsubscribe anytime.")

    col_email, col_btn = st.columns([3, 1])
    with col_email:
        email = st.text_input(
            "Email Address",
            value=st.session_state["email_value"],
            placeholder="you@example.com",
            label_visibility="collapsed",
        )
    with col_btn:
        unlock_clicked = st.button("Unlock Reports", type="primary")

    if unlock_clicked:
        if not email or "@" not in email:
            st.error("Please enter a valid email address.")
        else:
            st.session_state["email_value"] = email
            with st.spinner("Saving your email..."):
                try:
                    api_key       = st.secrets.get("MAILCHIMP_API_KEY", "")
                    list_id       = st.secrets.get("MAILCHIMP_LIST_ID", "")
                    server_prefix = st.secrets.get("MAILCHIMP_SERVER_PREFIX", "us1")
                except Exception:
                    api_key, list_id, server_prefix = "", "", "us1"

                result = subscribe_email(email, api_key, list_id, server_prefix)

            if result["success"]:
                st.success("You're on the list! Your downloads are ready below.")
            else:
                st.caption("Your downloads are ready below.")

            st.session_state["email_captured"] = True

    if st.session_state["email_captured"]:
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                label="Download PDF Summary",
                data=pdf_bytes,
                file_name="rsu_vitals_summary.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        with dl_col2:
            st.download_button(
                label="Download CSV Audit Trail",
                data=csv_bytes,
                file_name="rsu_vitals_audit.csv",
                mime="text/csv",
                use_container_width=True,
            )


def show_footer() -> None:
    """Render persistent disclaimer footer."""
    st.markdown("---")
    st.caption(
        "RSU Vitals is an **educational tool only** — not financial, tax, or legal advice. "
        "Federal tax estimates use 2025 IRS brackets. State rates are flat educational estimates. "
        "Consult a qualified CPA or financial advisor before making any decisions."
    )
