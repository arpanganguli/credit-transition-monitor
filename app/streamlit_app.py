from dataclasses import asdict
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from credit_transition_monitor import analyse_portfolio, rank_borrowers
from credit_transition_monitor.validation import read_portfolio, validate_portfolio, ValidationError
from credit_transition_monitor.scenarios import Scenario, stress_portfolio
from credit_transition_monitor.early_warning import explain, MULTIPLIERS
from credit_transition_monitor.audit import audit_bundle

ROOT=Path(__file__).resolve().parents[1]
st.set_page_config(page_title="Credit Transition Monitor", page_icon="◈", layout="wide")
st.markdown("""<style>
.block-container {padding-top:4rem; max-width:1550px;}
h1 {font-size:2.25rem!important; letter-spacing:-.06rem;}
h2 {font-size:1.4rem!important;} h3 {font-size:1.1rem!important;}
[data-testid="stMetric"] {background:white;border:1px solid #e3e9ef;border-radius:12px;padding:18px;}
[data-testid="stMetricValue"] {font-size:1.8rem;}
[data-testid="stSidebar"] {border-right:1px solid #e3e9ef;}
.eyebrow {font-size:12px;letter-spacing:2px;color:#087f8c;font-weight:700;}
.notice {padding:10px 16px;border-left:3px solid #d3a343;background:#fff8e8;border-radius:4px;font-size:13px;margin:14px 0 22px;}
</style>""",unsafe_allow_html=True)
COLORS={"GREEN":"#21846D","AMBER":"#C38C27","RED":"#CD5959","CRITICAL":"#793F62"}

def money(v):
    if pd.isna(v): return "N/A"
    if abs(v) < .5: v = 0
    if abs(v) >= 1e9: return f"{currency} {v/1e9:,.2f}bn"
    return f"{currency} {v/1e6:,.2f}m" if abs(v)>=1e6 else f"{currency} {v:,.0f}"

def chart(fig):
    fig.update_layout(font=dict(family="Arial",color="#172B45"), paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=38,b=10),height=320,legend=dict(orientation="h",y=1.15,x=0))
    st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})

def ranking(frame,scenario=False):
    cols=["company_name","sector","ead","risk_score","risk_band","pd","lgd","expected_loss", "scenario_delta_el" if scenario else "delta_el"]
    display=frame[cols].copy()
    for c in ["ead","expected_loss","delta_el","scenario_delta_el"]:
        if c in display: display[c]=display[c].round(0)
    st.dataframe(display,hide_index=True,width="stretch",column_config={
        "company_name":st.column_config.TextColumn("Borrower",width="medium"),"sector":"Sector",
        "ead":st.column_config.NumberColumn(f"EAD · {currency}",format="localized"),
        "risk_score":st.column_config.ProgressColumn("Score",min_value=0,max_value=100,format="%d"),
        "risk_band":"Risk band","pd":st.column_config.NumberColumn("PD",format="percent"),
        "lgd":st.column_config.NumberColumn("LGD",format="percent"),
        "expected_loss":st.column_config.NumberColumn(f"EL · {currency}",format="localized"),
        "delta_el":st.column_config.NumberColumn("Period Δ EL",format="localized"),
        "scenario_delta_el":st.column_config.NumberColumn("Scenario Δ EL",format="localized")})

def waterfall(parts, title):
    labels=["Exposure / EAD","Probability / PD","Loss severity / LGD"]
    values=[float(parts.get(c,0)) for c in ("ead","pd","lgd")]
    chart(go.Figure(go.Waterfall(x=labels+["Total Δ EL"],y=values+[sum(values)],measure=["relative"]*3+["total"],increasing={"marker":{"color":"#CD5959"}},decreasing={"marker":{"color":"#21846D"}},totals={"marker":{"color":"#172B45"}})).update_layout(title=title,yaxis_title=currency))

with st.sidebar:
    st.markdown("### ◈ Credit Transition Monitor")
    st.caption("PRIVATE CREDIT · DEMONSTRATION")
    page=st.radio("Workspace",["Portfolio","Borrower","Risk Drivers","Stress Test"],label_visibility="collapsed")
    st.divider()
    mode=st.radio("Data source",["Synthetic demo","Upload portfolio"])
    upload=st.file_uploader("CSV or Excel",type=["csv","xlsx"]) if mode=="Upload portfolio" else None
    st.download_button("Download sample CSV",(ROOT/"sample_data/demo_portfolio.csv").read_bytes(),"demo_portfolio.csv","text/csv",width="stretch")
    st.caption("One consolidated exposure per borrower. Single currency. XLSX: first worksheet. See README for the required columns.")

if mode=="Upload portfolio" and upload is None:
    st.title("Bring your portfolio into focus")
    st.info("Choose a CSV or XLSX file in the sidebar. Use the sample CSV as a template.")
    st.stop()
try:
    original=upload.getvalue() if upload else (ROOT/"sample_data/demo_portfolio.csv").read_bytes()
    source=f"CUSTOMER_UPLOAD:{upload.name}" if upload else "SYNTHETIC_DEMO:seed42"
    raw=validate_portfolio(read_portfolio(original,upload.name if upload else "demo.csv"))
    results=analyse_portfolio(raw)
except (ValidationError,ValueError) as exc:
    st.title("Portfolio needs attention")
    st.error(str(exc))
    st.caption("No rows have been silently dropped. Correct the listed fields and upload again.")
    st.stop()
current=rank_borrowers(results)
currency=raw.currency.iloc[0]
st.sidebar.success(f"{len(current)} borrowers · {raw.period.nunique()} periods")
st.sidebar.caption(f"As of {raw.period.max():%d %b %Y} · {currency}")
if raw.period.nunique()<2: st.warning("One reporting date: period changes and attribution are unavailable; change-based score rules receive no points.")
if results.nonpositive_ebitda.any(): st.warning("Non-positive EBITDA observed. Leverage is undefined; leverage covenant breach and -100% headroom are conservatively assumed. See methodology.")
st.markdown('<div class="eyebrow">PRIVATE CREDIT / PORTFOLIO INTELLIGENCE</div>',unsafe_allow_html=True)
st.title({"Portfolio":"See deterioration. Understand the loss.","Borrower":"The borrower behind the numbers.","Risk Drivers":"Every point has a reason.","Stress Test":"Explore the downside."}[page])
st.caption(f"{page}  /  {raw.period.max():%d %B %Y}  /  {'Fictional demonstration portfolio' if not upload else 'Customer-supplied portfolio'}")
st.markdown('<div class="notice">PROTOTYPE · Score thresholds, PD multipliers and LGD stress are assumptions, not calibrated probabilities or validated regulatory models.</div>',unsafe_allow_html=True)

# Scenario controls are shared across pages and preserved in the current session.
for key in ["shock_ebitda", "shock_revenue", "shock_collateral", "shock_interest"]:
    st.session_state[key] = st.session_state.get(key, 0)
if page=="Stress Test":
    st.markdown("#### Scenario controls")
    st.caption("Shocks apply to the latest reporting date; financial history stays fixed. Zero shocks reproduce current EL.")
    a,b,c,d=st.columns(4)
    a.slider("EBITDA change (%)",-100,50,key="shock_ebitda",step=5)
    b.slider("Revenue change (%)",-90,50,key="shock_revenue",step=5)
    c.slider("Collateral change (%)",-100,50,key="shock_collateral",step=5)
    d.slider("Interest-rate change (bp)",-300,1000,key="shock_interest",step=25)
    def preset():
        st.session_state.update(shock_ebitda=-25,shock_revenue=-15,shock_collateral=-20,shock_interest=200)
    def reset():
        st.session_state.update(shock_ebitda=0,shock_revenue=0,shock_collateral=0,shock_interest=0)
    a,b,_=st.columns([1,1,3])
    a.button("Apply downside case",on_click=preset,width="stretch")
    b.button("Reset shocks",on_click=reset,width="stretch")
scenario=Scenario(st.session_state.shock_ebitda/100,st.session_state.shock_revenue/100,st.session_state.shock_collateral/100,st.session_state.shock_interest)
stressed=stress_portfolio(raw,scenario)

if page=="Portfolio":
    a,b,c,d=st.columns(4)
    a.metric("Portfolio EAD",money(current.ead.sum()))
    b.metric("Current EL",money(current.expected_loss.sum()),money(current.delta_el.sum(min_count=1)),delta_color="inverse")
    c.metric("Scenario EL",money(stressed.expected_loss.sum()),money(stressed.scenario_delta_el.sum()),delta_color="inverse")
    d.metric("Red / critical borrowers",f"{current.risk_band.eq('RED').sum()} / {current.risk_band.eq('CRITICAL').sum()}")
    st.caption("Current EL uses the Week 2 PD overlay. Period Δ compares the same borrowers at the preceding reporting date. Scenario EL reflects the Stress Test controls (initially zero).")
    left,right=st.columns([1.5,1])
    with left:
        st.subheader("Portfolio loss trajectory")
        totals=results.groupby("period",as_index=False)[["expected_loss","baseline_el"]].sum().rename(columns={"expected_loss":"Monitored EL","baseline_el":"Lender baseline EL"})
        chart(px.line(totals,x="period",y=["Monitored EL","Lender baseline EL"],markers=True,color_discrete_sequence=["#087F8C","#A9B6C6"],labels={"value":currency,"variable":"","period":"Reporting date"}))
    with right:
        st.subheader("Exposure by risk band")
        bands=current.groupby("risk_band",as_index=False).ead.sum()
        chart(px.bar(bands,x="risk_band",y="ead",color="risk_band",color_discrete_map=COLORS,category_orders={"risk_band":list(COLORS)},labels={"ead":currency,"risk_band":""}).update_layout(showlegend=False))
    st.subheader("Borrowers requiring attention")
    a,b,c=st.columns([2,2,2])
    selected=a.multiselect("Risk bands",list(COLORS),default=list(COLORS))
    sector=b.multiselect("Sectors",sorted(current.sector.unique()))
    sort=c.selectbox("Rank by",["EL deterioration","Risk score","Expected loss","Exposure"])
    filtered=current[current.risk_band.isin(selected)]
    if sector: filtered=filtered[filtered.sector.isin(sector)]
    filtered=filtered.sort_values({"EL deterioration":"delta_el","Risk score":"risk_score","Expected loss":"expected_loss","Exposure":"ead"}[sort],ascending=False)
    st.caption("Click any column header to sort. Filters affect this ranking only; summary figures remain portfolio-wide.")
    ranking(filtered)
    st.download_button("Export borrower ranking",filtered.to_csv(index=False),"borrower_ranking.csv","text/csv")

elif page in ("Borrower","Risk Drivers"):
    bid=st.selectbox("Select borrower",current.borrower_id,format_func=lambda x: f"{current.set_index('borrower_id').loc[x,'company_name']} · {x}")
    history=results[results.borrower_id.eq(bid)]
    row=history.iloc[-1]
    a,b,c,d=st.columns(4)
    a.metric(f"{row.risk_band} · Risk score",f"{row.risk_score}/100")
    b.metric("Indicative PD",f"{row.pd:.2%}",f"Baseline {row.baseline_pd:.2%}",delta_color="off")
    c.metric("LGD",f"{row.lgd:.1%}")
    d.metric("Expected loss",money(row.expected_loss),money(row.delta_el),delta_color="inverse")
    if page=="Borrower":
        st.subheader("Financial and credit trajectory")
        for pair in [[("revenue","Revenue"),("ebitda","EBITDA")],[("leverage","Leverage (x)"),("interest_cover","Interest cover (x)")],[("cash","Cash"),("pd","Indicative PD")],[("expected_loss","Expected loss")]]:
            for col,(field,title) in zip(st.columns(2),pair):
                with col:
                    chart(px.line(history,x="period",y=field,markers=True,title=title,color_discrete_sequence=["#087F8C"]).update_layout(xaxis_title=None,yaxis_title="%" if field=="pd" else None,yaxis_tickformat=".1%" if field=="pd" else None))
        st.subheader("Covenant monitoring")
        st.dataframe(pd.DataFrame({"Covenant":["Maximum leverage","Minimum interest cover","Minimum cash"],"Actual":[f"{row.leverage:.2f}x" if pd.notna(row.leverage) else "Undefined: non-positive EBITDA",f"{row.interest_cover:.2f}x",money(row.cash)],"Limit":[f"{row.max_leverage:.2f}x",f"{row.min_interest_cover:.2f}x",money(row.min_liquidity)],"Headroom":[f"{row.leverage_headroom:.1%}",f"{row.interest_headroom:.1%}",f"{row.liquidity_headroom:.1%}" if pd.notna(row.liquidity_headroom) else "N/A (zero minimum)"],"Breach":[row.leverage_breach,row.interest_breach,row.liquidity_breach]}),hide_index=True,width="stretch")
    else:
        st.subheader("Scorecard · latest reporting period")
        st.dataframe(explain(row),hide_index=True,width="stretch")
        st.caption(f"Raw points {row.raw_score} + cap adjustment {row.cap_adjustment} = score {row.risk_score}. Interest-cover and EBITDA tiers are mutually exclusive; separate covenant signals are additive.")
        st.info(f"PD: 1 − (1 − {row.baseline_pd:.6f}) ^ {row.pd_multiplier:.1f} = {row.pd:.6f}. Band {row.risk_band}; same horizon as the lender-supplied PD.")
        if row.has_previous:
            waterfall({c:row['attribution_'+c] for c in ['ead','pd','lgd']},"What changed expected loss since the previous period?")
            st.caption("Exact Shapley contributions average marginal effects across all six EAD/PD/LGD orders. These explain the arithmetic EL movement, not causal effects. Score points are not Shapley contributions.")
            st.metric("Reconciliation residual",money(row.delta_el-sum(row['attribution_'+c] for c in ['ead','pd','lgd'])))
        else: st.info("A previous reporting date is needed for EL movement attribution.")
    with st.expander("Source financials and calculated history"):
        st.dataframe(history,width="stretch",hide_index=True)
        st.caption(f"Source: {source}. Inputs supplied as a single uploaded record set; derived fields are CALCULATED. No public-data enrichment is represented.")

elif page=="Stress Test":
    a,b,c,d=st.columns(4)
    a.metric("Current EL",money(current.expected_loss.sum()))
    b.metric("Scenario EL",money(stressed.expected_loss.sum()))
    c.metric("Scenario Δ EL",money(stressed.scenario_delta_el.sum()))
    d.metric("Scenario breaches",int(stressed.covenant_breach.sum()))
    left,right=st.columns(2)
    with left:
        waterfall({c:stressed['scenario_attribution_'+c].sum() for c in ['ead','pd','lgd']},"Scenario EL movement · Shapley attribution")
    with right:
        st.subheader("Scenario assumptions")
        st.markdown("**PD:** rerun financial ratios, covenants and the Week 2 scorecard against unchanged history.\n\n**Interest:** all debt is floating rate; annual interest increases by debt × basis-point shock / 10,000 (floor above zero).\n\n**LGD:** all baseline recovery is assumed collateral-sensitive: `LGD* = clip(1 − (1 − LGD₀) × (1 + collateral shock), 0, 1)`. This is a prototype assumption, independent of EAD.\n\n**Revenue and EBITDA:** independent shocks; no implicit operating-cost model. Collateral changes do not alter PD. EAD stays fixed.")
    st.subheader("Borrower impact")
    ranking(stressed.sort_values("scenario_delta_el",ascending=False),scenario=True)
    st.download_button("Export scenario results",stressed.to_csv(index=False),"scenario_results.csv","text/csv")

st.divider()
with st.expander("Methodology, validation and audit trail"):
    st.markdown("**Source of rules:** 8-Week Build Plan, pp. 3–7. Week 2 multipliers: GREEN 1.0×, AMBER 1.5×, RED 2.5×, CRITICAL 4.0×. The illustrative Week 6 2.0× example does not override this table. Current LGD is lender supplied; the recovery haircut applies only in scenarios.\n\n**Validation:** complete finite inputs, probabilities in [0,1], unique borrower/date, one currency and a balanced reporting panel. No missing values are imputed. Changes compare adjacent supplied observations, without annualisation.\n\n**Boundary conventions:** EBITDA decline of exactly 10% or 20% scores 8; greater than 20% scores 15. Interest cover below 1.0× scores 20 rather than 35. Headroom is the smallest relative cushion across the three covenants. Covenant equality is not a breach.\n\n**Limits:** no live Companies House enrichment, multi-facility modelling, FX conversion, authenticated hosting or regulatory validation. All demonstration companies are fictional.")
    meta,db=audit_bundle(raw,results,original,source,asdict(scenario),stressed)
    st.json(meta)
    a,b=st.columns(2)
    a.download_button("Download audit database",db,"credit_monitor_audit.sqlite","application/vnd.sqlite3")
    b.download_button("Download run metadata",json.dumps(meta,indent=2),"run_metadata.json","application/json")
st.caption("CREDIT TRANSITION MONITOR  /  Explainable by design  /  Prototype v0.1.0")
