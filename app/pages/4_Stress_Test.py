"""Screen 4 - Stress Test: EBITDA / revenue / collateral / rate / EAD shocks, applied portfolio-wide."""

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
from app.charts import band_migration_chart, el_comparison_bar
from app.theme import STATUS_ORDER, badge_html, brand_header, fmt_gbp, inject_css
from credit.scenarios import Shock, apply_shock_to_borrower

st.set_page_config(page_title="Stress Test | Early-Warning Monitor", page_icon="🧪", layout="wide")
inject_css()
brand_header("Stress Test", "Move the sliders, recompute the whole portfolio's expected loss immediately.")

df = dp.require_data_or_stop()

st.markdown("#### Scenario")
s1, s2, s3 = st.columns(3)
with s1:
    ebitda_shock = st.slider("EBITDA shock", -60, 30, -25, step=5, format="%d%%") / 100
    revenue_shock = st.slider("Revenue shock", -60, 30, 0, step=5, format="%d%%") / 100
with s2:
    collateral_shock = st.slider("Collateral value shock", -100, 0, 0, step=5, format="%d%%") / 100
    ead_shock = st.slider("Drawn exposure (EAD) shock", -20, 50, 0, step=5, format="%d%%") / 100
with s3:
    rate_shock = st.slider("Interest-rate shock (bps)", 0, 500, 200, step=25)

shock = Shock(
    ebitda_shock_pct=ebitda_shock,
    revenue_shock_pct=revenue_shock,
    collateral_shock_pct=collateral_shock,
    rate_shock_bps=rate_shock,
    ead_shock_pct=ead_shock,
)
st.caption(f"Applying: **{shock.label()}** to every borrower in the portfolio.")


@st.cache_data(show_spinner=False)
def _run_scenario(df_key: str, records: list[dict], shock_key: tuple) -> pd.DataFrame:
    shock_obj = Shock(*shock_key)
    rows = []
    for rec in records:
        result = apply_shock_to_borrower(
            borrower_id=rec["borrower_id"],
            baseline_pd=rec["baseline_pd"],
            baseline_lgd=rec["baseline_lgd"],
            ead=rec["ead"],
            revenue=rec["revenue"],
            ebitda=rec["ebitda"],
            debt=rec["debt"],
            cash=rec["cash"],
            interest_expense=rec["interest_expense"],
            max_leverage=rec.get("max_leverage"),
            min_interest_cover=rec.get("min_interest_cover"),
            min_liquidity=rec.get("min_liquidity"),
            collateral_value=rec.get("collateral_value"),
            previous_ebitda=rec.get("ebitda_previous"),
            previous_revenue=rec.get("revenue_previous"),
            previous_cash=rec.get("cash_previous"),
            previous_leverage=rec.get("leverage_previous"),
            shock=shock_obj,
        )
        d = result.to_dict()
        d["company_name"] = rec.get("company_name", rec["borrower_id"])
        rows.append(d)
    return pd.DataFrame(rows)


records = df.to_dict(orient="records")
shock_key = (
    shock.ebitda_shock_pct, shock.revenue_shock_pct, shock.collateral_shock_pct,
    shock.rate_shock_bps, shock.ead_shock_pct,
)
stressed = _run_scenario(str(len(df)), records, shock_key)

baseline_el = df["expected_loss"].sum()
stressed_el = stressed["expected_loss_stressed"].sum()
baseline_counts = df["risk_band"].value_counts().to_dict()
stressed_counts = stressed["band"].value_counts().to_dict()

st.markdown("<hr class='cm-divider'/>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Baseline portfolio EL", fmt_gbp(baseline_el, millions=True))
c2.metric("Stressed portfolio EL", fmt_gbp(stressed_el, millions=True), delta=fmt_gbp(stressed_el - baseline_el, millions=True), delta_color="inverse")
migrations = int((stressed.set_index("borrower_id")["band"] != df.set_index("borrower_id")["risk_band"]).sum())
c3.metric("Borrowers changing band", migrations)
newly_critical = int(((stressed["band"] == "CRITICAL") & (df.set_index("borrower_id").loc[stressed["borrower_id"], "risk_band"].values != "CRITICAL")).sum())
c4.metric("Newly CRITICAL", newly_critical)

st.markdown("<hr class='cm-divider'/>", unsafe_allow_html=True)
gc1, gc2 = st.columns(2)
with gc1:
    st.plotly_chart(el_comparison_bar(baseline_el, stressed_el), use_container_width=True, config={"displayModeBar": False})
with gc2:
    st.plotly_chart(band_migration_chart(baseline_counts, stressed_counts), use_container_width=True, config={"displayModeBar": False})

st.markdown("#### Borrowers with the largest stressed EL increase")
merged = stressed.merge(
    df[["borrower_id", "expected_loss", "risk_band"]].rename(columns={"expected_loss": "expected_loss_baseline", "risk_band": "band_baseline"}),
    on="borrower_id",
    how="left",
)
merged["el_increase"] = merged["expected_loss_stressed"] - merged["expected_loss_baseline"]
merged = merged.sort_values("el_increase", ascending=False).head(15)

show = merged[["company_name", "band_baseline", "band", "expected_loss_baseline", "expected_loss_stressed", "el_increase"]].copy()
show["band_baseline"] = show["band_baseline"].apply(badge_html)
show["band"] = show["band"].apply(badge_html)
for c in ["expected_loss_baseline", "expected_loss_stressed", "el_increase"]:
    show[c] = show[c].apply(lambda x: fmt_gbp(x))
show.columns = ["Borrower", "Baseline band", "Stressed band", "Baseline EL", "Stressed EL", "EL increase"]
st.markdown(show.to_html(escape=False, index=False), unsafe_allow_html=True)

st.markdown(
    '<div class="cm-disclaimer" style="margin-top:1rem;">'
    "The drawn-exposure (EAD) shock deliberately does not change LGD: collateral coverage is "
    "computed against each loan's on-record EAD, not a hypothetical stressed EAD, so an EAD-only "
    "shock moves expected loss purely through exposure &mdash; see credit/scenarios.py."
    "</div>",
    unsafe_allow_html=True,
)
