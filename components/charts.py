import plotly.graph_objects as go
import pandas as pd

# Brand palette (matches style guide)
BLUE   = "#2563eb"
BLUE_HOVER = "#3b82f6"
GREEN  = "#22c55e"
RED    = "#ef4444"
YELLOW = "#f59e0b"
GRAY   = "#94a3b8"
BG_DARK  = "#0f172a"
BG_MID   = "#1e293b"
TEXT     = "#e2e8f0"
BORDER   = "#334155"

_LAYOUT_BASE = dict(
    paper_bgcolor=BG_MID,
    plot_bgcolor=BG_MID,
    font=dict(family="'Space Mono', 'Roboto Mono', 'Courier New', monospace", color=TEXT),
    xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
)


def create_cliff_chart(df: pd.DataFrame) -> go.Figure:
    """
    Plotly bar chart of RSU vesting schedule.
    df must have columns: date, shares, value (gross value = shares * price).
    """
    hover_text = [
        f"<b>{row['date'].strftime('%b %Y')}</b><br>"
        f"Shares: {row['shares']:,.0f}<br>"
        f"Gross Value: ${row['value']:,.0f}"
        for _, row in df.iterrows()
    ]

    fig = go.Figure(go.Bar(
        x=df["date"],
        y=df["value"],
        marker_color=BLUE,
        hovertext=hover_text,
        hoverinfo="text",
    ))

    fig.update_layout(
        **_LAYOUT_BASE,
        title={"text": "Vesting Schedule — The 'Cliff' (Educational Estimate)", "font": {"size": 15}},
        xaxis_title="Vest Date",
        yaxis_title="Estimated Gross Value ($)",
        yaxis_tickprefix="$",
        yaxis_tickformat=",.0f",
        showlegend=False,
        margin=dict(t=50, b=40, l=60, r=20),
    )
    return fig


def create_tax_donut_chart(impact: dict) -> go.Figure:
    """
    Donut chart showing how an RSU vest is split between:
      - Net Value (after all taxes)
      - Statutory Withholding (22% broker hold)
      - Surprise Tax Bill (gap between actual liability and withholding)

    impact is the dict returned by calculate_rsu_tax_impact().
    """
    rsu_value          = impact["rsu_value"]
    statutory          = impact["statutory_withholding"]
    surprise           = max(0.0, impact["surprise_bill"])
    net_value          = max(0.0, rsu_value - impact["actual_liability"])

    labels = ["Net Value (After Tax)", "Statutory Withholding (22%)", "Surprise Tax Bill"]
    values = [net_value, statutory, surprise]
    colors = [GREEN, BLUE, RED]

    # Drop the surprise slice if zero (e.g., low-income users)
    if surprise == 0:
        labels = labels[:2]
        values = values[:2]
        colors = colors[:2]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker=dict(colors=colors),
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f} (%{percent})<extra></extra>",
    ))

    fig.update_layout(
        **_LAYOUT_BASE,
        title={"text": "Uncle Sam's Slice (Educational Estimate)", "font": {"size": 15}},
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(color=TEXT)),
        margin=dict(t=50, b=60, l=20, r=20),
    )
    return fig


def create_concentration_gauge(concentration_pct: float, warning_level: str) -> go.Figure:
    """
    Gauge indicator showing single-stock concentration as % of net worth.
    Threshold lines at 10% (caution) and 25% (danger).
    Axis scales beyond 100% when unvested RSU value exceeds stated net worth.
    """
    if warning_level == "danger":
        bar_color = RED
    elif warning_level == "caution":
        bar_color = YELLOW
    else:
        bar_color = GREEN

    # Scale axis to fit values above 100% (e.g. when RSU value > net worth)
    axis_max = max(100, round(concentration_pct * 1.25 / 10) * 10)

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=concentration_pct,
        number={"suffix": "%", "valueformat": ".1f"},
        delta={"reference": 10, "increasing": {"color": RED}, "decreasing": {"color": GREEN}},
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Unvested RSU Concentration<br><span style='font-size:0.8em;color:gray'>% of Current Net Worth</span>"},
        gauge={
            "axis": {"range": [0, axis_max], "ticksuffix": "%"},
            "bar": {"color": bar_color},
            "steps": [
                {"range": [0, 10],          "color": "#14532d"},
                {"range": [10, 25],         "color": "#713f12"},
                {"range": [25, axis_max],   "color": "#7f1d1d"},
            ],
            "threshold": {
                "line": {"color": RED, "width": 3},
                "thickness": 0.75,
                "value": 10,
            },
        },
    ))

    fig.update_layout(
        **_LAYOUT_BASE,
        height=280,
        margin=dict(t=60, b=20, l=30, r=30),
    )
    return fig
