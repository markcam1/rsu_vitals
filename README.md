# RSU Vitals

An educational RSU (Restricted Stock Unit) risk and tax impact calculator built with Streamlit and Python. Powered by the [tenforty](https://github.com/mmacpherson/tenforty) tax engine for supported states, with a bracket-based fallback for all others.

> **Disclaimer:** This tool is for educational purposes only. It is not financial, tax, or legal advice. Always consult a qualified CPA or financial advisor before making investment or tax decisions.

---

## What It Does

Enter your RSU grant details and get an instant visual breakdown of:

- **The Cliff Chart** — bar chart of every vest date and its estimated gross value over your 4-year schedule
- **Uncle Sam's Slice** — donut chart showing how your vest is split between net value, statutory withholding (22%), and the potential "surprise tax bill" at filing time
- **Concentration Gauge** — indicator showing what percentage of your net worth is tied up in a single stock, with a warning above 10%

After entering your email, both a **PDF summary** and a **CSV audit trail** are unlocked for download.

---

## Tax Engine

Tax calculations use a two-call delta approach: the engine runs once for your base income, once for base + RSU vest value, and the difference is the incremental tax caused by the vest.

| State coverage | Method |
|---|---|
| AZ, CA, MA, MI, NC, NJ, NY, OH, OR, PA, VA | **tenforty** — real bracket-based federal + state logic |
| AK, FL, NV, SD, TN, TX, WA, WY | **tenforty** — federal logic, $0 state tax (no income tax) |
| All other states | **Bracket estimate** — 2025 federal brackets + flat top-marginal state rate |

**Additional Medicare Tax** (0.9% on W-2 income above $200K single / $250K MFJ) is included in the surprise bill calculation for tenforty-supported states. NIIT is excluded — RSU income is W-2, not investment income.

The UI shows a badge indicating which engine ran for the selected state.

> **Windows note:** tenforty does not run natively on Windows. On Windows the app automatically falls back to the bracket estimate for all states. To run the full tenforty engine locally, use WSL2 (see below).

---

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- WSL2 (Windows only, required to run tenforty locally)

---

## Setup

### 1. Install uv

```bash
# macOS / Linux / WSL2
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell) — for running the app without tenforty
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone / navigate to the project

```bash
cd path/to/claude-code
```

### 3. Install dependencies

```bash
uv sync
```

This creates a `.venv` virtual environment and installs all packages from `uv.lock`. No manual `pip install` needed.

> **Windows users:** `uv sync` will warn that `tenforty` cannot be installed. The app still runs — the bracket estimate fallback activates automatically. To get the full tenforty engine, run these steps inside WSL2.

### 4. Configure Mailchimp (optional)

The PDF and CSV downloads are gated behind an email capture form. If you skip this step, the app still works — it just won't sync emails to Mailchimp.

Copy the secrets template:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml`:

```toml
MAILCHIMP_API_KEY = "your-api-key"         # Account → Extras → API Keys
MAILCHIMP_LIST_ID = "your-audience-id"     # Audience → Settings → Audience name & defaults
MAILCHIMP_SERVER_PREFIX = "us1"            # Prefix from your API key, e.g. "us1", "us6"
```

> `secrets.toml` is gitignored — never commit it.

### 5. Run the app

```bash
uv run streamlit run app.py
```

The app opens at [http://localhost:8501](http://localhost:8501).

---

## Project Structure

```
claude-code/
├── app.py                          # Main Streamlit entrypoint
├── pyproject.toml                  # Project metadata and dependencies
├── uv.lock                         # Locked dependency versions
├── .streamlit/
│   └── secrets.toml.example        # Mailchimp credentials template
├── logic/
│   ├── taxes.py                    # Tax engine: tenforty + bracket fallback, state rate table
│   ├── financials.py               # Vesting schedule, stock price fetch, concentration
│   ├── pdf_gen.py                  # fpdf2 PDF report generator
│   └── csv_gen.py                  # Multi-section audit trail CSV generator
├── components/
│   ├── charts.py                   # Plotly figure factories (Cliff, Donut, Gauge)
│   └── ui.py                       # Disclaimer modal, sidebar inputs, email gate, footer
└── integrations/
    └── mailchimp.py                # Mailchimp API subscriber upsert
```

---

## How the Tax Math Works

The surprise bill = `actual_liability - statutory_withholding (22%)`, where:

- **`actual_liability`** = federal income tax on RSU + Additional Medicare Tax (if applicable) + state tax on RSU
- **Federal income tax** — computed via tenforty or 2025 IRS bracket math (marginal increment only)
- **Additional Medicare Tax** — 0.9% on the portion of W-2 income above $200K (Single) / $250K (MFJ); tenforty-supported states only
- **State tax** — real bracket logic via tenforty (11 states) or flat top-marginal rate estimate (all others)
- **Standard deductions** — $15,000 Single / $30,000 MFJ (2025)

The income slider uses bucket midpoints (e.g. `$100K–$200K` → `$150,000`) so users don't need to know their exact income.

---

## CSV Audit Trail

The downloaded CSV contains 7 labeled sections for review:

1. Report Metadata (including which tax engine ran)
2. User Inputs
3. Federal Bracket Audit — Base Income
4. Federal Bracket Audit — Base + RSU Income
5. Tax Impact Summary (line-by-line reconciliation with notes)
6. Concentration Risk
7. Full Vesting Schedule (pro-rata tax estimates per vest event)

Sections 3 and 4 always use the bracket math as an independent cross-check, regardless of which engine computed the summary figures.

---

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect the repo.
3. Set the main file to `app.py`.
4. Add your Mailchimp secrets under **Settings → Secrets** (same key names as `secrets.toml`).

Streamlit Community Cloud runs on Linux — tenforty installs and runs automatically for all supported states.

---

## Running Without uv

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

---

## License

Educational use only. Not for commercial redistribution.
