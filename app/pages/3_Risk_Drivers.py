"""Screen 3 - Risk Drivers: point-by-point explanation + EL attribution waterfall.

This is the screen the build plan calls essential: "AI predicts ABC is high
risk" is not an acceptable answer to a credit committee. Every point on the
score and every pound of Delta EL traces back to a named, reproducible cause.
"""

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
from app.charts import el_attribution_waterfall
from app.theme import STATUS_COLORS, badge, brand_header, fmt_gbp, fmt_pct, inject_css

st.set_page_config(page_title="Risk Drivers | Early-Warning Monitor", page_icon="🔎", layout="wide")
inject_css()
brand_header("Risk Drivers", "Why this score, why this movement in expected loss — in plain, reproducible steps.")

df = dp.require_data_or_stop()

borrowers = df["borrower_id"].tolist()
default = st.session_state.get("selected_borrower", borrowers[0])
if default not in borrowers:
    default = borrowers[0]
label_map = {row["borrower_id"]: row.get("company_name", row["borrower_id"]) for _, row in df.iterrows()}
choice = st.selectbox("Select borrower", options=borrowers, index=borrowers.index(default), format_func=lambda b: label_map[b])
st.session_state["selected_borrower"] = choice
row = df.set_index("borrower_id").loc[choice]

h1, h2 = st.columns([3, 1])
with h1:
    st.markdown(f"### {row.get('company_name', choice)}")
with h2:
    badge(row["risk_band"])
    st.caption(f"Score {int(row['score'])} / 100")

left, right = st.columns([2, 3])

with left:
    st.markdown("#### Score breakdown")
    reasons = row.get("reasons") or []
    if not reasons:
        st.success("No deterioration signals triggered this period. Score 0 (GREEN).")
    else:
        for reason in reasons:
            r = reason.to_dict() if hasattr(reason, "to_dict") else reason
            st.markdown(
                f"""<div class="cm-reason-row">
                    <span>{r['label']}</span>
                    <span style="font-weight:700; color:{STATUS_COLORS.get(row['risk_band'], '#0B1F33')};">+{r['points']}</span>
                </div>
                <div style="color:#8A99A8; font-size:0.82rem; margin-bottom:0.4rem;">{r['detail']}</div>
                """,
                unsafe_allow_html=True,
            )
        total = sum((reason.to_dict() if hasattr(reason, "to_dict") else reason)["points"] for reason in reasons)
        st.markdown(
            f"<div style='display:flex; justify-content:space-between; padding-top:0.6rem; font-weight:700;'>"
            f"<span>Total (capped at 100)</span><span>{min(100, total)}</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("#### Covenant position")
    cc1, cc2 = st.columns(2)
    cc1.metric("Leverage", f"{row['leverage']:.2f}x" if row.get("leverage") is not None else "n/a", help="vs covenant max shown alongside")
    cc2.metric("Covenant max leverage", f"{row['max_leverage']:.2f}x" if row.get("max_leverage") else "n/a")
    cc3, cc4 = st.columns(2)
    cc3.metric("Interest cover", f"{row['interest_cover']:.2f}x" if row.get("interest_cover") is not None else "n/a")
    cc4.metric("Covenant min cover", f"{row['min_interest_cover']:.2f}x" if row.get("min_interest_cover") else "n/a")
    if row.get("covenant_breached"):
        st.error("One or more covenants are currently breached.")
    elif row.get("covenant_headroom") is not None:
        st.info(f"Tightest covenant headroom: {fmt_pct(row['covenant_headroom'])}")

with right:
    st.markdown("#### Expected-loss attribution")
    if row.get("delta_el") is None:
        st.info("This borrower has only one reporting period on file, so Delta EL cannot be attributed yet.")
    else:
        contributions = {
            "ead": row["attribution_ead"],
            "pd": row["attribution_pd"],
            "lgd": row["attribution_lgd"],
        }
        fig = el_attribution_waterfall(row["expected_loss_previous"], contributions, row["expected_loss"])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        total_delta = row["delta_el"]
        share_rows = []
        for key, label in [("ead", "Exposure (EAD)"), ("pd", "PD deterioration"), ("lgd", "LGD deterioration")]:
            val = contributions[key]
            share = (val / total_delta * 100) if total_delta else 0
            share_rows.append((label, val, share))

        for label, val, share in share_rows:
            st.markdown(
                f"<div class='cm-reason-row'><span>{label}</span>"
                f"<span>{fmt_gbp(val)} &nbsp;({share:.0f}%)</span></div>",
                unsafe_allow_html=True,
            )

        st.caption(
            "Contributions are computed with Shapley attribution: the average marginal effect of "
            "each factor across every order in which EAD, PD and LGD could be imagined to change. "
            "They always sum exactly to Delta EL."
        )

st.markdown("<hr class='cm-divider'/>", unsafe_allow_html=True)
st.markdown(
    '<div class="cm-disclaimer">Risk-band thresholds, PD/LGD overlay multipliers and covenant '
    "headroom rules are prototype assumptions, documented in the README, not statistically "
    "calibrated probabilities or a regulatory model.</div>",
    unsafe_allow_html=True,
)
