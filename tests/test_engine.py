import numpy as np
import pandas as pd
import pytest
from credit_transition_monitor import analyse_portfolio, rank_borrowers
from credit_transition_monitor.ratios import calculate_ratios
from credit_transition_monitor.expected_loss import calculate_expected_loss
from credit_transition_monitor.early_warning import risk_band, explain
from credit_transition_monitor.pd_overlay import calculate_stressed_pd
from credit_transition_monitor.attribution import shapley_el
from credit_transition_monitor.scenarios import Scenario, stress_portfolio

def test_plan_example():
    d=pd.DataFrame([dict(debt=35e6,cash=4e6,ebitda=8e6,interest_expense=5e6,revenue=50e6,ead=18e6,pd=.06,lgd=.45)])
    r=calculate_expected_loss(calculate_ratios(d)).iloc[0]
    assert r.net_debt==31e6
    assert r.leverage==4.375
    assert r.net_leverage==3.875
    assert r.interest_cover==1.6
    assert r.ebitda_margin==.16
    assert r.expected_loss==486000

@pytest.mark.parametrize("score,band",[(0,"GREEN"),(24,"GREEN"),(25,"AMBER"),(49,"AMBER"),(50,"RED"),(74,"RED"),(75,"CRITICAL"),(100,"CRITICAL")])
def test_bands(score,band): assert risk_band(score)==band

@pytest.mark.parametrize("p",[0,.01,.06,.5,.999,1])
@pytest.mark.parametrize("m",[1,1.5,2.5,4])
def test_hazard(p,m):
    actual=calculate_stressed_pd(p,m)
    assert actual==pytest.approx(1-(1-p)**m)
    assert p<=actual+1e-14<=1+1e-14

@pytest.mark.parametrize("p,m",[(-.01,1),(1.1,1),(.1,0),(np.nan,1),(.1,np.inf)])
def test_hazard_invalid(p,m):
    with pytest.raises(ValueError): calculate_stressed_pd(p,m)

@pytest.mark.parametrize("decline,points",[(0,0),(.0999,0),(.1,8),(.2,8),(.2001,15)])
def test_ebitda_boundaries(simple,decline,points):
    simple.loc[1,"ebitda"]=200*(1-decline)
    assert analyse_portfolio(simple).iloc[-1].points_ebitda==points

@pytest.mark.parametrize("cover,points",[(1.5,0),(1.499,15),(1.,15),(.999,20)])
def test_interest_tiers(simple,cover,points):
    simple["interest_expense"]=simple.ebitda/cover
    assert analyse_portfolio(simple).iloc[-1].points_interest_cover==points

@pytest.mark.parametrize("field,base,shock,point",[("cash",200,150,0),("cash",200,149,10),("revenue",1000,850,0),("revenue",1000,849,8)])
def test_decline_boundaries(simple,field,base,shock,point):
    simple.loc[0,field]=base; simple.loc[1,field]=shock
    assert analyse_portfolio(simple).iloc[-1]['points_'+field]==point

@pytest.mark.parametrize("leverage,point",[(4,0),(4.001,15)])
def test_leverage_change_boundary(simple,leverage,point):
    simple.loc[1,"debt"]=leverage*200
    assert analyse_portfolio(simple).iloc[-1].points_leverage_change==point

def test_score_capped_and_explained(simple):
    simple.loc[1,["ebitda","cash","revenue","debt"]]=[40,20,600,1000]
    r=analyse_portfolio(simple).iloc[-1]
    assert r.raw_score==128 and r.risk_score==100 and r.cap_adjustment==-28
    assert explain(r).Points.sum()==128

@pytest.mark.parametrize("debt,breach",[(1000,False),(1001,True)])
def test_covenant_equality(simple,debt,breach):
    simple["debt"]=debt
    r=analyse_portfolio(simple).iloc[-1]
    assert r.leverage_breach==breach
    assert r.leverage_headroom==pytest.approx((5-debt/200)/5)

@pytest.mark.parametrize("debt,points",[(900,0),(901,15)])
def test_headroom_threshold(simple,debt,points):
    simple["debt"]=debt
    assert analyse_portfolio(simple).iloc[-1].points_headroom==points

def test_nonpositive_ebitda(simple):
    simple.loc[1,"ebitda"]=-10
    r=analyse_portfolio(simple).iloc[-1]
    assert pd.isna(r.leverage) and r.leverage_breach and r.points_leverage_covenant==20
    assert r.covenant_headroom<=-1

def test_zero_cash_base(simple):
    simple.loc[0,"cash"]=0
    r=analyse_portfolio(simple).iloc[-1]
    assert pd.isna(r.cash_change_pct) and r.points_cash==0

def test_changes_order_and_no_cross_borrower(simple):
    second=simple.copy(); second["borrower_id"]="B"; second["company_name"]="Other"; second["ebitda"]*=2
    simple.loc[1,"ebitda"]=150
    r=analyse_portfolio(pd.concat([simple,second]).sample(frac=1,random_state=2))
    assert r.loc[r.borrower_id.eq("A"),"delta_ebitda"].iloc[-1]==-50
    assert r.loc[r.borrower_id.eq("B"),"delta_ebitda"].iloc[-1]==0
    assert r.groupby("borrower_id").head(1).delta_el.isna().all()

def test_shapley_known_and_efficiency():
    b=[100,.1,.2]; a=[200,.2,.4]
    s=shapley_el(b,a)
    assert list(s.values())==pytest.approx([14/3]*3)
    assert sum(s.values())==pytest.approx(14)
    rng=np.random.default_rng(9)
    for _ in range(100):
        b=rng.random(3); a=rng.random(3)
        assert sum(shapley_el(b,a).values())==pytest.approx(np.prod(a)-np.prod(b))

def test_shapley_single_factor_and_reverse():
    b=[100,.1,.2]; a=[120,.1,.2]
    assert shapley_el(b,a)==pytest.approx(dict(ead=.4,pd=0,lgd=0))
    assert shapley_el(a,b)==pytest.approx(dict(ead=-.4,pd=0,lgd=0))

def test_shapley_bad_shape():
    with pytest.raises(ValueError): shapley_el([1,2],[1,2,3])

def test_demo_and_attribution(demo):
    r=analyse_portfolio(demo)
    assert len(r)==200 and len(rank_borrowers(r))==50
    rows=r[r.has_previous]
    np.testing.assert_allclose(rows.filter(regex="^attribution_").sum(axis=1),rows.delta_el,atol=1e-8)
    assert set(r.risk_band)=={"GREEN","AMBER","RED","CRITICAL"}

def test_zero_scenario_identity(demo):
    b=rank_borrowers(analyse_portfolio(demo)).set_index('borrower_id').sort_index()
    s=stress_portfolio(demo,Scenario()).set_index('borrower_id').sort_index()
    for field in ['ead','pd','lgd','risk_score','expected_loss']:
        np.testing.assert_allclose(b[field],s[field])
    assert s.scenario_delta_el.eq(0).all()

def test_ebitda_stress(demo):
    b=rank_borrowers(analyse_portfolio(demo)).set_index('borrower_id')
    s=stress_portfolio(demo,Scenario(ebitda_pct=-.25)).set_index('borrower_id').reindex(b.index)
    assert (s.risk_score>=b.risk_score).all()
    assert s.expected_loss.sum()>b.expected_loss.sum()

def test_debt_reduction(simple):
    simple.loc[1,"debt"]=1400
    b=analyse_portfolio(simple).iloc[-1]
    simple.loc[1,"debt"]=300
    a=analyse_portfolio(simple).iloc[-1]
    assert a.leverage<b.leverage and a.risk_score<b.risk_score

@pytest.mark.parametrize("shock",[-1,-.5,-.2,0,.5,1])
def test_collateral_only(simple,shock):
    b=rank_borrowers(analyse_portfolio(simple)).iloc[0]
    s=stress_portfolio(simple,Scenario(collateral_pct=shock)).iloc[0]
    assert s.pd==pytest.approx(b.pd)
    assert s.lgd==pytest.approx(np.clip(1-(1-b.lgd)*(1+shock),0,1))
    assert s.expected_loss==pytest.approx(s.ead*s.pd*s.lgd)
    assert s.scenario_attribution_pd==0

def test_ead_only(simple):
    b=analyse_portfolio(simple).iloc[-1]
    simple.loc[1,'ead']*=2
    a=analyse_portfolio(simple).iloc[-1]
    assert a.pd==b.pd and a.lgd==b.lgd
    assert a.expected_loss==2*b.expected_loss

def test_interest_stress_and_reconciliation(demo):
    r=stress_portfolio(demo,Scenario(-.25,-.15,-.2,200))
    np.testing.assert_allclose(r.filter(regex='^scenario_attribution_').sum(axis=1),r.scenario_delta_el,atol=1e-8)
    b=rank_borrowers(analyse_portfolio(demo)).set_index('borrower_id').reindex(r.borrower_id)
    np.testing.assert_allclose(r.interest_expense.to_numpy(),b.interest_expense+b.debt*.02)

def test_extreme_scenario(simple):
    r=stress_portfolio(simple,Scenario(-1,-.9,-1,1000)).iloc[0]
    assert r.lgd==1 and r.risk_score<=100 and r.leverage_breach
    assert np.isfinite(r.expected_loss)

@pytest.mark.parametrize("kwargs",[{"ebitda_pct":-1.1},{"revenue_pct":-1},{"interest_bps":1001},{"collateral_pct":np.nan}])
def test_invalid_scenario(kwargs):
    with pytest.raises(ValueError): Scenario(**kwargs)


def test_stressed_period_attribution_consistent(demo):
    r=stress_portfolio(demo,Scenario(collateral_pct=-.3))
    np.testing.assert_allclose(r.filter(regex='^attribution_').sum(axis=1),r.delta_el,atol=1e-8)
