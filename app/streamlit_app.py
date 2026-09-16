"""Home: branding, data loading (demo or upload), and an executive summary."""

import sys
from pathlib import Path

_here = Path(__file__).resolve()
for _parent in [_here] + list(_here.parents):
    if (_parent / "credit").is_dir() and (_parent / "database").is_dir():
        if str(_parent) not in sys.path:
            sys.path.insert(0, str(_parent))
        break

import pandas as pd
import streamlit as st

from app import data_pipeline as dp
from app.charts import band_distribution_chart, top_deterioration_chart
from app.theme import badge_html, brand_header, fmt_gbp, inject_css

st.set_page_config(
    page_title="Early-Warning & Loss Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

with st.sidebar:
    st.markdown('<div class="cm-eyebrow">PRIVATE CREDIT</div>', unsafe_allow_html=True)
    st.markdown("### Early-Warning & Loss Monitor")
    st.caption("Portfolio credit-quality transition, explained.")
    st.markdown("---")
    st.markdown("**Load a portfolio**")
    if st.button("Load demo portfolio (50 borrowers)", use_container_width=True):
        dp.load_demo_portfolio()
        st.toast("Demo portfolio loaded.", icon="✅")

    with st.expander("Upload your own loan book"):
        st.caption(
            "CSV or Excel, one row per borrower per reporting period. "
            "Minimum columns: borrower_id, ead, baseline_pd, baseline_lgd, "
            "revenue, ebitda, debt, cash, interest_expense."
        )
        uploaded = st.file_uploader("Portfolio file", type=["csv", "xlsx", "xls"], label_visibility="collapsed")
        if uploaded is not None:
            try:
                dp.load_uploaded_portfolio(uploaded)
                st.toast("Portfolio uploaded and validated.", icon="✅")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not process this file: {exc}")

        template = pd.DataFrame(
            [
                {
                    "borrower_id": "ACME-01", "company_name": "Acme Trading Ltd", "sector": "Industrials",
                    "country": "United Kingdom", "loan_id": "LN-001", "period": "2026-06-30",
                    "ead": 10000000, "baseline_pd": 0.03, "baseline_lgd": 0.40,
                    "revenue": 40000000, "ebitda": 5000000, "debt": 18000000, "cash": 2000000,
                    "interest_expense": 1300000, "max_leverage": 4.0, "min_interest_cover": 1.75,
                    "min_liquidity": 800000, "collateral_type": "All-asset debenture", "collateral_value": 7000000,
                }
            ]
        )
        st.download_button(
            "Download CSV template",
            template.to_csv(index=False),
            file_name="portfolio_template.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("---")
    if dp.has_data():
        errors = st.session_state.get("validation_errors", [])
        total = st.session_state.get("rows_seen", 0)
        st.success(f"{total - len(errors)} of {total} rows loaded")
        if errors:
            st.warning(f"{len(errors)} row(s) failed validation")

brand_header(
    "Early-Warning & Loss Monitor",
    "Upload a loan book, see which borrowers are deteriorating, and understand exactly why.",
)

if not dp.has_data():
    st.markdown(
        """
        <div class="cm-card">
        <p style="font-size:1.02rem; margin-bottom:0.6rem;">
        This prototype turns a private-credit loan book into a ranked, explainable view of
        <b>where credit quality is moving and why</b> &mdash; without a black-box model.
        </p>
        <p style="color:#52636F; margin-bottom:0;">
        Use the sidebar to load the 50-borrower demo portfolio, or upload your own CSV/Excel loan book,
        then explore the <b>Portfolio</b>, <b>Borrower</b>, <b>Risk Drivers</b> and <b>Stress Test</b> pages.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("#### How the numbers are built")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div class="cm-card"><b>1. Ratios &amp; scorecard</b><br><span style="color:#52636F;">'
            "Leverage, interest cover, EBITDA margin and period-on-period changes feed an "
            "explainable, capped-at-100 early-warning score.</span></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="cm-card"><b>2. PD / LGD overlay</b><br><span style="color:#52636F;">'
            "A hazard-rate transform and a collateral-aware adjustment turn the lender's baseline "
            "PD/LGD into an indicative stressed PD/LGD.</span></div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="cm-card"><b>3. Expected loss &amp; attribution</b><br><span style="color:#52636F;">'
            "EL = EAD x PD x LGD. Every change in EL is decomposed into exposure, PD and LGD "
            "contributions via Shapley attribution.</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="cm-disclaimer" style="margin-top:1rem;">'
        "<b>Important:</b> scorecard thresholds, PD/LGD multipliers and risk-band boundaries are "
        "prototype assumptions to test with users &mdash; not statistically calibrated probabilities, "
        "not a regulatory model, and not investment advice."
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

df = dp.get_analysed_df()
total_ead = df["ead"].sum()
total_el = df["expected_loss"].sum()
total_el_prev = df["expected_loss_previous"].sum() if df["expected_loss_previous"].notna().any() else None
delta = (total_el - total_el_prev) if total_el_prev is not None else None
counts = df["risk_band"].value_counts()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio EAD", fmt_gbp(total_ead, millions=True))
c2.metric(
    "Expected loss",
    fmt_gbp(total_el, millions=True),
    delta=f"{fmt_gbp(delta, millions=True)} since previous period" if delta is not None else None,
    delta_color="inverse",
)
c3.metric("Red + Critical borrowers", int(counts.get("RED", 0) + counts.get("CRITICAL", 0)))
c4.metric("Borrowers monitored", len(df))

st.markdown("<hr class='cm-divider'/>", unsafe_allow_html=True)

left, right = st.columns([3, 2])
with left:
    st.markdown("#### Borrowers requiring attention")
    watchlist = df[df["risk_band"].isin(["RED", "CRITICAL"])].sort_values("expected_loss", ascending=False)
    if watchlist.empty:
        st.info("No borrowers currently in RED or CRITICAL.")
    else:
        show = watchlist[["company_name", "ead", "score", "risk_band", "pd", "lgd", "expected_loss"]].head(10).copy()
        show.insert(3, "band", show.pop("risk_band").apply(badge_html))
        show["ead"] = show["ead"].apply(lambda x: fmt_gbp(x, millions=True))
        show["expected_loss"] = show["expected_loss"].apply(lambda x: fmt_gbp(x, millions=True, decimals=2))
        show["pd"] = (show["pd"] * 100).round(1).astype(str) + "%"
        show["lgd"] = (show["lgd"] * 100).round(1).astype(str) + "%"
        show.columns = ["Borrower", "EAD", "Score", "Band", "PD", "LGD", "Expected loss"]
        st.markdown(show.to_html(escape=False, index=False), unsafe_allow_html=True)
    st.caption("Open **Portfolio** in the sidebar for the full, sortable ranking.")

with right:
    st.plotly_chart(band_distribution_chart(df), use_container_width=True, config={"displayModeBar": False})

st.plotly_chart(top_deterioration_chart(df), use_container_width=True, config={"displayModeBar": False})
