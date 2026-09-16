from io import BytesIO
import json
import sqlite3
import numpy as np
import pytest
from credit_transition_monitor import analyse_portfolio
from credit_transition_monitor.validation import validate_portfolio,read_portfolio,ValidationError
from credit_transition_monitor.audit import audit_bundle
from credit_transition_monitor.scenarios import stress_portfolio,Scenario

@pytest.mark.parametrize("field,value",[("baseline_pd",6),("baseline_lgd",-1),("ebitda",np.nan),("ead",np.inf),("cash",-1),("interest_expense",0),("revenue",0),("period","bad"),("company_name",""),("currency","EURO")])
def test_bad_values(simple,field,value):
    simple.loc[0,field]=value
    with pytest.raises(ValidationError): validate_portfolio(simple)

def test_missing_column(simple):
    with pytest.raises(ValidationError,match='Missing columns'): validate_portfolio(simple.drop(columns='cash'))

def test_duplicate(simple):
    with pytest.raises(ValidationError,match='Duplicate borrower'): validate_portfolio(simple.iloc[[0,0]])

def test_unbalanced(demo):
    with pytest.raises(ValidationError,match='balanced'): validate_portfolio(demo.iloc[1:])

def test_mixed_currency(simple):
    simple.loc[1,'currency']='USD'
    with pytest.raises(ValidationError,match='currency'): validate_portfolio(simple)

def test_aliases(simple):
    d=simple.rename(columns={'baseline_pd':'PD','baseline_lgd':'LGD','interest_expense':'interest'})
    assert len(validate_portfolio(d))==2

def test_empty(simple):
    with pytest.raises(ValidationError,match='no rows'): validate_portfolio(simple.iloc[:0])

def test_csv_xlsx_round_trip(simple):
    csv=simple.to_csv(index=False).encode()
    buffer=BytesIO(); simple.to_excel(buffer,index=False)
    for data,name in [(csv,'upload.csv'),(buffer.getvalue(),'upload.xlsx')]:
        assert len(validate_portfolio(read_portfolio(data,name)))==2

def test_bad_file():
    with pytest.raises(ValidationError): read_portfolio(b'garbage','a.xlsx')
    with pytest.raises(ValidationError): read_portfolio(b'garbage','a.txt')

def test_single_period(simple):
    r=analyse_portfolio(simple.iloc[:1])
    assert not r.has_previous.any() and r.delta_el.isna().all()

def test_audit_roundtrip(simple,tmp_path):
    raw=validate_portfolio(simple)
    metadata,blob=audit_bundle(raw,analyse_portfolio(raw),b'original','CUSTOMER_UPLOAD:test.csv',{},stress_portfolio(raw,Scenario()))
    path=tmp_path/'audit.sqlite'; path.write_bytes(blob)
    con=sqlite3.connect(path)
    assert con.execute('SELECT COUNT(*) FROM normalised_inputs').fetchone()[0]==2
    assert con.execute('SELECT COUNT(*) FROM input_provenance').fetchone()[0]==24
    assert json.loads(con.execute('SELECT json FROM run_metadata').fetchone()[0])==metadata
    assert len(metadata['input_sha256'])==64
    con.close()


def test_duplicate_alias_headers(simple):
    simple['PD']=simple.baseline_pd
    with pytest.raises(ValidationError,match='Duplicate columns'): validate_portfolio(simple)
