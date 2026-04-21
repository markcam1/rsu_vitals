from datetime import date
from fpdf import FPDF
from fpdf.enums import XPos, YPos


def generate_pdf_report(user_data: dict, results: dict) -> bytes:
    """
    Generate a text-based PDF summary using fpdf2.

    user_data keys: ticker, num_shares, grant_date, frequency, income_bucket,
                    state, filing_status, net_worth, price
    results keys:   total_rsu_value, tax_impact (dict), concentration (dict)
    """
    def safe(text: str) -> str:
        """Replace characters outside Latin-1 so Helvetica doesn't crash."""
        return (
            text
            .replace("\u2014", "-")   # em dash
            .replace("\u2013", "-")   # en dash
            .replace("\u2019", "'")   # right single quote
            .replace("\u2018", "'")   # left single quote
            .replace("\u201c", '"')   # left double quote
            .replace("\u201d", '"')   # right double quote
            .encode("latin-1", errors="replace")
            .decode("latin-1")
        )

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    # ── Header ──────────────────────────────────────────────────────────────
    pdf.set_fill_color(30, 58, 95)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 14, "RSU Vitals - Risk & Tax Impact Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align="C")

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0, 8,
        safe(f"Ticker: {user_data['ticker']}   |   Generated: {date.today().strftime('%B %d, %Y')}"),
        new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align="C",
    )
    pdf.ln(6)

    # Reset colors
    pdf.set_text_color(0, 0, 0)

    # ── Section helper ───────────────────────────────────────────────────────
    def section_title(title: str):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(220, 230, 242)
        pdf.cell(0, 9, safe(f"  {title}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(2)

    def row(label: str, value: str):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(80, 7, safe(label), new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, safe(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Input Summary ────────────────────────────────────────────────────────
    section_title("Grant Details")
    row("Ticker Symbol:",       user_data["ticker"])
    row("Total Shares:",        f"{int(user_data['num_shares']):,}")
    row("Grant Date:",          str(user_data["grant_date"]))
    row("Vesting Frequency:",   user_data["frequency"])
    row("Share Price Used:",    f"${user_data['price']:,.2f}")
    row("Total RSU Value:",     f"${results['total_rsu_value']:,.2f}")
    pdf.ln(4)

    section_title("Personal Financials")
    row("Annual Income (bucket):",  user_data["income_bucket"])
    row("State of Residence:",      user_data["state"])
    row("Filing Status:",           user_data["filing_status"])
    row("Total Net Worth:",         f"${user_data['net_worth']:,.0f}")
    pdf.ln(4)

    # ── Tax Analysis ─────────────────────────────────────────────────────────
    tax = results["tax_impact"]
    section_title("Tax Impact Analysis (Educational Estimate)")
    row("Gross RSU Value:",             f"${tax['rsu_value']:,.2f}")
    row("Statutory Withholding (22%):", f"${tax['statutory_withholding']:,.2f}")
    row("Federal Tax on RSUs:",         f"${tax['federal_tax_on_rsu']:,.2f}")
    row("State Tax on RSUs:",           f"${tax['state_tax_on_rsu']:,.2f}  ({tax['state_rate']*100:.2f}% est.)")
    if tax.get("additional_medicare_tax", 0) > 0:
        row("Additional Medicare Tax (0.9%):", f"${tax['additional_medicare_tax']:,.2f}")
    row("Total Actual Tax Liability:",  f"${tax['actual_liability']:,.2f}")
    row("Net Value After Tax:",         f"${tax['rsu_value'] - tax['actual_liability']:,.2f}")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    surprise = tax["surprise_bill"]
    surprise_label = "Estimated Surprise Tax Bill:" if surprise >= 0 else "Estimated Refund Opportunity:"
    pdf.set_text_color(180, 0, 0) if surprise > 0 else pdf.set_text_color(0, 130, 0)
    pdf.cell(80, 8, safe(surprise_label), new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(0, 8, safe(f"${abs(surprise):,.2f}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)

    row("Effective Rate on RSUs:",      f"{tax['effective_rate_on_rsu']*100:.1f}%")
    row("Marginal Federal Bracket:",    f"{tax['marginal_federal_rate']*100:.0f}%")
    row("Tax Calculation Engine:",      safe(tax.get("calculation_method", "bracket_estimate")))
    pdf.ln(4)

    # ── Concentration ─────────────────────────────────────────────────────────
    conc = results["concentration"]
    section_title("Concentration Risk")
    row("RSU Concentration:", f"{conc['concentration_pct']:.1f}% of net worth")
    row("Risk Level:",        conc["warning_level"].capitalize())

    if conc["is_warning"]:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(180, 0, 0)
        pdf.multi_cell(
            0, 7,
            safe(
                "WARNING: Your RSU holdings exceed 10% of your stated net worth. "
                "Financial planners generally recommend keeping single-stock exposure below 10% "
                "to reduce risk."
            ),
        )
        pdf.set_text_color(0, 0, 0)

    pdf.ln(8)

    # ── Disclaimer ────────────────────────────────────────────────────────────
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        0, 5,
        safe(
            "DISCLAIMER: This report is generated for educational purposes only and does not "
            "constitute financial, tax, or legal advice. All calculations are estimates based on "
            "2025 U.S. federal tax brackets and flat-rate state estimates. Actual tax liability "
            "depends on your complete tax situation, deductions, credits, and applicable local taxes. "
            "Always consult a qualified CPA or financial advisor before making investment or tax decisions."
        ),
        fill=True,
    )

    return bytes(pdf.output())
