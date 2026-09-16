"""
Shared Plotly chart builders.

Follows the house rules for data visualisation used across the app: one hue
per encoded job (status colour for risk band, a single sequential blue for
magnitude), never a dual-axis chart, thin marks, a visible legend whenever
more than one series is on screen, and direct labels on the marks that
matter rather than a label on every point.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from app.theme import CATEGORICAL, SEQUENTIAL_BLUE, STATUS_COLORS, STATUS_ORDER

CHART_FONT = dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color="#0B1F33")
GRIDCOLOR = "#E1E0D9"
PLOT_BG = "#FCFCFB"


def _base_layout(height: int = 360, **kwargs) -> dict:
    layout = dict(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        font=CHART_FONT,
        plot_bgcolor=PLOT_BG,
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    layout.update(kwargs)
    return layout


def band_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Donut of portfolio EAD by risk band -- identity, not magnitude, so status colour is correct here."""
    counts = df.groupby("risk_band")["ead"].sum().reindex(STATUS_ORDER).fillna(0)
    fig = go.Figure(
        data=[
            go.Pie(
                labels=counts.index,
                values=counts.values,
                hole=0.58,
                marker=dict(colors=[STATUS_COLORS[b] for b in counts.index], line=dict(color="white", width=2)),
                textinfo="label+percent",
                sort=False,
            )
        ]
    )
    fig.update_layout(**_base_layout(height=320, showlegend=False, title="Portfolio EAD by risk band"))
    return fig


def top_deterioration_chart(df: pd.DataFrame, n: int = 12) -> go.Figure:
    """Horizontal bar of the N borrowers with the largest Delta EL, coloured by risk band (identity)."""
    top = df.dropna(subset=["delta_el"]).sort_values("delta_el", ascending=False).head(n)
    top = top.iloc[::-1]  # largest at top when plotted horizontally
    colors = [STATUS_COLORS.get(b, "#8A99A8") for b in top["risk_band"]]
    labels = top.get("company_name", top["borrower_id"])
    fig = go.Figure(
        data=[
            go.Bar(
                x=top["delta_el"],
                y=labels,
                orientation="h",
                marker=dict(color=colors),
                text=[f"+£{v/1000:,.0f}k" for v in top["delta_el"]],
                textposition="outside",
                hovertemplate="%{y}<br>Delta EL: £%{x:,.0f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        **_base_layout(
            height=max(320, 28 * len(top)),
            title="Largest expected-loss deterioration",
            xaxis=dict(title="Delta EL (£)", gridcolor=GRIDCOLOR, zeroline=True, zerolinecolor="#C3C2B7"),
            yaxis=dict(title=None),
        )
    )
    return fig


def borrower_trend_chart(periods: list[str], values: list[float], title: str, y_title: str, fmt: str = ",.0f") -> go.Figure:
    """A single-series small-multiple trend line -- one metric, one axis, no dual scales."""
    fig = go.Figure(
        data=[
            go.Scatter(
                x=periods,
                y=values,
                mode="lines+markers",
                line=dict(color=SEQUENTIAL_BLUE[2], width=2),
                marker=dict(size=9, color=SEQUENTIAL_BLUE[3]),
                hovertemplate=f"%{{x}}<br>{y_title}: %{{y:{fmt}}}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        **_base_layout(
            height=220,
            title=title,
            showlegend=False,
            xaxis=dict(gridcolor=GRIDCOLOR),
            yaxis=dict(gridcolor=GRIDCOLOR, tickformat=fmt),
        )
    )
    return fig


def el_attribution_waterfall(el_baseline: float, contributions: dict, el_current: float, labels: dict | None = None) -> go.Figure:
    """
    Bridge chart from baseline EL to current EL via the Shapley contributions
    of EAD, PD and LGD -- the right form for "explain a change via additive
    parts", per the build plan's differentiator (Week 5).
    """
    labels = labels or {"ead": "Exposure", "pd": "PD deterioration", "lgd": "LGD deterioration"}
    order = ["ead", "pd", "lgd"]
    x_labels = ["Baseline EL"] + [labels[k] for k in order] + ["Current EL"]
    measures = ["absolute"] + ["relative"] * len(order) + ["total"]
    values = [el_baseline] + [contributions[k] for k in order] + [el_current]

    fig = go.Figure(
        go.Waterfall(
            x=x_labels,
            measure=measures,
            y=values,
            connector=dict(line=dict(color="#C3C2B7", width=1)),
            increasing=dict(marker=dict(color=STATUS_COLORS["RED"])),
            decreasing=dict(marker=dict(color=STATUS_COLORS["GREEN"])),
            totals=dict(marker=dict(color="#16324A")),
            text=[f"£{v:,.0f}" for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(**_base_layout(height=380, title="Expected-loss bridge: baseline to current", showlegend=False))
    return fig


def band_migration_chart(baseline_counts: dict, stressed_counts: dict) -> go.Figure:
    """Grouped bar comparing borrower counts by band, baseline vs stressed."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Baseline",
            x=STATUS_ORDER,
            y=[baseline_counts.get(b, 0) for b in STATUS_ORDER],
            marker=dict(color="#B7C2CC"),
        )
    )
    fig.add_trace(
        go.Bar(
            name="Stressed",
            x=STATUS_ORDER,
            y=[stressed_counts.get(b, 0) for b in STATUS_ORDER],
            marker=dict(color=[STATUS_COLORS[b] for b in STATUS_ORDER]),
        )
    )
    fig.update_layout(
        **_base_layout(
            height=340,
            title="Borrower count by risk band: baseline vs stressed",
            barmode="group",
            xaxis=dict(title=None),
            yaxis=dict(title="Borrowers", gridcolor=GRIDCOLOR),
        )
    )
    return fig


def el_comparison_bar(baseline_el: float, stressed_el: float) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Bar(
                x=["Baseline", "Stressed"],
                y=[baseline_el, stressed_el],
                marker=dict(color=["#16324A", STATUS_COLORS["RED"]]),
                text=[f"£{baseline_el/1_000_000:,.1f}m", f"£{stressed_el/1_000_000:,.1f}m"],
                textposition="outside",
                width=[0.5, 0.5],
            )
        ]
    )
    fig.update_layout(
        **_base_layout(
            height=320,
            title="Portfolio expected loss: baseline vs stressed",
            showlegend=False,
            xaxis=dict(title=None),
            yaxis=dict(title="Expected loss (£)", gridcolor=GRIDCOLOR),
        )
    )
    return fig
