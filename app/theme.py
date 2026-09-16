"""
Shared visual identity for the app: an institutional navy/teal theme intended
to read as "credit risk software", not "internal hackathon tool" -- and a
small set of formatting helpers used by every page.

Status colours (GREEN/AMBER/RED/CRITICAL) follow a validated, colour-vision-
deficiency-checked palette rather than default hues, and every badge pairs
colour with a text label so risk band is never conveyed by colour alone.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
NAVY_900 = "#0A1E33"
NAVY_800 = "#0F2A44"
NAVY_700 = "#16324A"
TEAL_600 = "#0F7173"
TEAL_500 = "#14918F"
SLATE_600 = "#52636F"
SLATE_400 = "#8A99A8"
PAPER = "#FFFFFF"
PAPER_MUTED = "#F4F6F8"
BORDER = "#E1E6EA"

# Status palette (validated: colour-vision-deficiency safe, paired with labels)
STATUS_COLORS = {
    "GREEN": "#0ca30c",
    "AMBER": "#c98500",  # darkened from the raw #fab219 for readable text-on-white
    "RED": "#c9583a",
    "CRITICAL": "#d03b3b",
}
STATUS_BG = {
    "GREEN": "#E6F5E6",
    "AMBER": "#FDF1DA",
    "RED": "#FBE7E1",
    "CRITICAL": "#FAE0E0",
}
STATUS_ORDER = ["GREEN", "AMBER", "RED", "CRITICAL"]

CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#4a3aa7"]
SEQUENTIAL_BLUE = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#0d366b"]


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {PAPER_MUTED};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {NAVY_900};
        }}
        section[data-testid="stSidebar"] * {{
            color: #E7EDF2 !important;
        }}
        section[data-testid="stSidebar"] .stButton>button {{
            background-color: {TEAL_600};
            color: white !important;
            border: none;
        }}
        h1, h2, h3 {{
            color: {NAVY_800};
            font-weight: 700;
        }}
        .cm-eyebrow {{
            color: {TEAL_600};
            font-weight: 700;
            letter-spacing: 0.08em;
            font-size: 0.78rem;
            text-transform: uppercase;
            margin-bottom: 0.15rem;
        }}
        .cm-card {{
            background: {PAPER};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 1.1rem 1.3rem;
            box-shadow: 0 1px 2px rgba(10, 30, 51, 0.04);
        }}
        .cm-kpi-label {{
            color: {SLATE_600};
            font-size: 0.82rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}
        .cm-kpi-value {{
            color: {NAVY_900};
            font-size: 1.9rem;
            font-weight: 700;
            line-height: 1.2;
        }}
        .cm-kpi-delta-up {{ color: #b23b3b; font-weight: 600; font-size: 0.92rem; }}
        .cm-kpi-delta-down {{ color: #0ca30c; font-weight: 600; font-size: 0.92rem; }}
        .cm-badge {{
            display: inline-block;
            padding: 0.18rem 0.65rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.78rem;
            letter-spacing: 0.02em;
        }}
        .cm-divider {{
            border: none;
            border-top: 1px solid {BORDER};
            margin: 1.1rem 0;
        }}
        .cm-reason-row {{
            display: flex;
            justify-content: space-between;
            padding: 0.55rem 0.1rem;
            border-bottom: 1px solid {BORDER};
        }}
        .cm-disclaimer {{
            background: #FBF6E9;
            border: 1px solid #EADDAE;
            border-radius: 8px;
            padding: 0.7rem 1rem;
            font-size: 0.85rem;
            color: {NAVY_700};
        }}
        div[data-testid="stMetricValue"] {{
            color: {NAVY_900};
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
        }}
        table th {{
            text-align: left;
            color: {SLATE_600};
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            border-bottom: 2px solid {BORDER};
            padding: 0.5rem 0.6rem;
        }}
        table td {{
            padding: 0.5rem 0.6rem;
            border-bottom: 1px solid {BORDER};
            color: {NAVY_900};
        }}
        table tr:hover td {{
            background: {PAPER_MUTED};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def brand_header(title: str, subtitle: Optional[str] = None) -> None:
    st.markdown('<div class="cm-eyebrow">PRIVATE CREDIT</div>', unsafe_allow_html=True)
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)


def badge_html(band: str) -> str:
    band = (band or "GREEN").upper()
    color = STATUS_COLORS.get(band, SLATE_600)
    bg = STATUS_BG.get(band, PAPER_MUTED)
    return (
        f'<span class="cm-badge" style="background:{bg}; color:{color};">{band}</span>'
    )


def badge(band: str) -> None:
    st.markdown(badge_html(band), unsafe_allow_html=True)


def fmt_gbp(x, millions: bool = False, decimals: int = 1) -> str:
    if x is None or (isinstance(x, float) and (x != x)):
        return "n/a"
    if millions:
        return f"£{x / 1_000_000:,.{decimals}f}m"
    return f"£{x:,.0f}"


def fmt_pct(x, decimals: int = 1) -> str:
    if x is None or (isinstance(x, float) and (x != x)):
        return "n/a"
    return f"{x * 100:.{decimals}f}%"


def fmt_x(x, decimals: int = 2) -> str:
    if x is None or (isinstance(x, float) and (x != x)):
        return "n/a"
    return f"{x:.{decimals}f}x"


def kpi_card(label: str, value: str, delta: Optional[str] = None, delta_bad: bool = True) -> str:
    delta_html = ""
    if delta:
        cls = "cm-kpi-delta-up" if delta_bad else "cm-kpi-delta-down"
        delta_html = f'<div class="{cls}">{delta}</div>'
    return (
        f'<div class="cm-card"><div class="cm-kpi-label">{label}</div>'
        f'<div class="cm-kpi-value">{value}</div>{delta_html}</div>'
    )
