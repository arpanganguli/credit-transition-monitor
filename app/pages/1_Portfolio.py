"""Screen 1 - Portfolio: EAD, current EL, stressed EL, red/critical counts, sortable ranking."""

import sys
from pathlib import Path

_here = Path(__file__).resolve()
for _parent in [_here] + list(_here.parents):
    if (_parent / "credit").is_dir() and (_parent / "database").is_dir():
        if str(_parent) not in sys.path:
            sys.path.insert(0, str(_parent))
        break

import streamlit as st

from app import data_pipeline as dp
from app.charts import band_distribution_chart, top_deterioration_chart
from app.theme import STATUS_ORDER, brand_header, fmt_gbp, fmt_pct, fmt_x, inject_css

st.set_page_config(page_title="Portfolio | Early-Warning Monitor", page_icon="📊", layout="wide")
inject_css()
brand_header("Portfolio", "Every borrower, ranked and sortable, with the movement that matters.")

df = dp.require_data_or_stop()

total_ead = df["ead"].sum()
total_el = df["expected_loss"].sum()
total_el_prev = df["expected_loss_previous"].sum() if df["expected_loss_previous"].notna().any() else None
counts = df["risk_band"].value_counts()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Portfolio EAD", fmt_gbp(total_ead, millions=True))
c2.metric(
    "Expected loss (current)",
    fmt_gbp(total_el, millions=True),
    delta=(f"{fmt_gbp(total_el - total_el_prev, millions=True)} vs prior period" if total_el_prev is not None else None),
    delta_color="inverse",
)
c3.metric("Prior-period EL", fmt_gbp(total_el_prev, millions=True) if total_el_prev is not None else "n/a")
c4.metric("RED", int(counts.get("RED", 0)))
c5.metric("CRITICAL", int(counts.get("CRITICAL", 0)))

st.markdown("<hr class='cm-divider'/>", unsafe_allow_html=True)

col_chart1, col_chart2 = st.columns([3, 2])
with col_chart1:
    st.plotly_chart(top_deterioration_chart(df, n=15), use_container_width=True, config={"displayModeBar": False})
with col_chart2:
    st.plotly_chart(band_distribution_chart(df), use_container_width=True, config={"displayModeBar": False})

st.markdown("<hr class='cm-divider'/>", unsafe_allow_html=True)
st.markdown("#### Full ranking")

fc1, fc2, fc3 = st.columns([2, 2, 2])
with fc1:
    band_filter = st.multiselect("Risk band", STATUS_ORDER, default=STATUS_ORDER)
with fc2:
    sectors = sorted(df["sector"].dropna().unique().tolist()) if "sector" in df.columns else []
    sector_filter = st.multiselect("Sector", sectors, default=sectors)
with fc3:
    search = st.text_input("Search borrower name", "")

view = df[df["risk_band"].isin(band_filter)]
if sectors:
    view = view[view["sector"].isin(sector_filter)]
if search:
    name_col = view["company_name"] if "company_name" in view.columns else view["borrower_id"]
    view = view[name_col.str.contains(search, case=False, na=False)]

display_cols = {
    "company_name": "Borrower",
    "sector": "Sector",
    "ead": "EAD",
    "score": "Score",
    "risk_band": "Band",
    "pd": "PD",
    "lgd": "LGD",
    "expected_loss": "Expected loss",
    "delta_el": "Delta EL",
    "leverage": "Leverage",
    "interest_cover": "Interest cover",
}
cols_present = [c for c in display_cols if c in view.columns]
table = view[cols_present].rename(columns=display_cols).copy()
if "PD" in table.columns:
    table["PD"] = table["PD"] * 100
if "LGD" in table.columns:
    table["LGD"] = table["LGD"] * 100

st.dataframe(
    table,
    use_container_width=True,
    height=560,
    hide_index=True,
    column_config={
        "EAD": st.column_config.NumberColumn(format="£%,.0f"),
        "Expected loss": st.column_config.NumberColumn(format="£%,.0f"),
        "Delta EL": st.column_config.NumberColumn(format="£%,.0f"),
        "PD": st.column_config.NumberColumn(format="%.1f%%"),
        "LGD": st.column_config.NumberColumn(format="%.1f%%"),
        "Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        "Leverage": st.column_config.NumberColumn(format="%.2fx"),
        "Interest cover": st.column_config.NumberColumn(format="%.2fx"),
    },
)
st.caption(f"Showing {len(table):,} of {len(df):,} borrowers. Click any column header to sort.")

st.markdown("#### Open a borrower")
if not view.empty:
    label_map = {row["borrower_id"]: f'{row.get("company_name", row["borrower_id"])} ({row["risk_band"]})' for _, row in view.iterrows()}
    choice = st.selectbox("Borrower", options=list(label_map.keys()), format_func=lambda b: label_map[b])
    if st.button("Go to Borrower screen ->"):
        st.session_state["selected_borrower"] = choice
        st.switch_page("pages/2_Borrower.py")
