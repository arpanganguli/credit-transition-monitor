"""Screen 2 - Borrower: profile, score/band, PD/LGD/EL, and trend charts."""

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
from app.charts import borrower_trend_chart
from app.theme import badge, brand_header, fmt_gbp, fmt_pct, fmt_x, inject_css
from data.companies_house import get_company

st.set_page_config(page_title="Borrower | Early-Warning Monitor", page_icon="🏢", layout="wide")
inject_css()
brand_header("Borrower", "One borrower's full picture: level, trend, and the two reporting periods behind it.")

df = dp.require_data_or_stop()

borrowers = df["borrower_id"].tolist()
default = st.session_state.get("selected_borrower", borrowers[0])
if default not in borrowers:
    default = borrowers[0]

label_map = {row["borrower_id"]: f'{row.get("company_name", row["borrower_id"])}' for _, row in df.iterrows()}
choice = st.selectbox(
    "Select borrower",
    options=borrowers,
    index=borrowers.index(default),
    format_func=lambda b: f"{label_map[b]}  ·  {df.set_index('borrower_id').loc[b, 'risk_band']}",
)
st.session_state["selected_borrower"] = choice
row = df.set_index("borrower_id").loc[choice]

# --- Profile header -----------------------------------------------------
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown(f"### {row.get('company_name', choice)}")
    meta_bits = [str(row.get(k)) for k in ("sector", "country") if row.get(k)]
    st.caption(" · ".join(meta_bits) if meta_bits else "")
with h2:
    badge(row["risk_band"])
    st.caption(f"Score {int(row['score'])} / 100")

c1, c2, c3, c4 = st.columns(4)
c1.metric("EAD", fmt_gbp(row["ead"], millions=True))
c2.metric("PD (stressed)", fmt_pct(row["pd"]), delta=(f"vs {fmt_pct(row['pd_previous'])} prior" if row.get("pd_previous") is not None else None))
c3.metric("LGD (stressed)", fmt_pct(row["lgd"]), delta=(f"vs {fmt_pct(row['lgd_previous'])} prior" if row.get("lgd_previous") is not None else None))
c4.metric(
    "Expected loss",
    fmt_gbp(row["expected_loss"], millions=True, decimals=2),
    delta=(f"{fmt_gbp(row['delta_el'], millions=True, decimals=2)} vs prior" if row.get("delta_el") is not None else None),
    delta_color="inverse",
)

with st.expander("Loan & company detail"):
    d1, d2, d3 = st.columns(3)
    d1.write(f"**Loan ID:** {row.get('loan_id', 'n/a')}")
    d1.write(f"**Seniority:** {row.get('seniority', 'n/a')}")
    d2.write(f"**Maturity:** {row.get('maturity', 'n/a')}")
    d2.write(f"**Company number:** {row.get('company_number', 'n/a')}")
    d3.write(f"**Baseline PD / LGD:** {fmt_pct(row.get('baseline_pd'))} / {fmt_pct(row.get('baseline_lgd'))}")
    d3.write(f"**Collateral value:** {fmt_gbp(row.get('collateral_value'))}")

    company_number = row.get("company_number")
    if company_number and st.button("Look up at Companies House"):
        result = get_company(str(company_number))
        if result.source == "COMPANIES_HOUSE":
            st.success(f"{result.company_name} — status: {result.company_status}")
        else:
            st.warning(result.message)

st.markdown("<hr class='cm-divider'/>", unsafe_allow_html=True)
st.markdown("#### Trend across reporting periods")

periods = ["Previous", "Current"]


def _pair(prev_key, cur_key):
    return [row.get(prev_key), row.get(cur_key)]


trend_specs = [
    ("Revenue", _pair("revenue_previous", "revenue"), ",.0f"),
    ("EBITDA", _pair("ebitda_previous", "ebitda"), ",.0f"),
    ("Leverage (Debt/EBITDA)", _pair("leverage_previous", "leverage"), ".2f"),
    ("Interest cover", _pair("interest_cover_previous", "interest_cover"), ".2f"),
    ("Cash", _pair("cash_previous", "cash"), ",.0f"),
    ("Expected loss", _pair("expected_loss_previous", "expected_loss"), ",.0f"),
]

has_previous = row.get("revenue_previous") is not None
if not has_previous:
    st.info("This borrower has only one reporting period on file, so no trend can be shown yet.")
else:
    cols = st.columns(3)
    for i, (title, values, fmt) in enumerate(trend_specs):
        if any(v is None for v in values):
            continue
        with cols[i % 3]:
            st.plotly_chart(
                borrower_trend_chart(periods, values, title, title, fmt=fmt),
                use_container_width=True,
                config={"displayModeBar": False},
            )

st.page_link("pages/3_Risk_Drivers.py", label="Explain this score on the Risk Drivers screen ->", icon="🔎")
