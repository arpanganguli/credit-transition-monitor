from pathlib import Path
from streamlit.testing.v1 import AppTest
APP=Path(__file__).resolve().parents[1]/"app/streamlit_app.py"

def test_four_screens_and_stress():
    app=AppTest.from_file(str(APP),default_timeout=30).run()
    assert not app.exception
    assert len(app.metric)==4
    for page in ["Borrower","Risk Drivers","Stress Test"]:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception
    app.slider[0].set_value(-25).run()
    assert not app.exception
    assert app.metric[2].value not in ('GBP 0','GBP 0.00')
    app.sidebar.radio[0].set_value('Portfolio').run()
    assert not app.exception
    assert app.metric[2].delta not in ('GBP 0','GBP 0.00')
    app.run()
    assert app.metric[2].delta not in ('GBP 0','GBP 0.00')
    app.sidebar.radio[0].set_value('Stress Test').run()
    assert app.slider[0].value == -25
    app.button[1].click().run()
    assert app.slider[0].value == 0
    assert app.metric[2].value == 'GBP 0'

def test_upload_empty_state():
    app=AppTest.from_file(str(APP),default_timeout=30).run()
    app.sidebar.radio[1].set_value('Upload portfolio').run()
    assert not app.exception
    assert 'Choose a CSV' in app.info[0].value
