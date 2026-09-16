"""
Shared session-state data pipeline used by every page: load a portfolio
(demo or uploaded), validate it, run it through the credit engine, and cache
the result in ``st.session_state`` so pages don't each reload/recompute.

Session-state keys
-------------------
raw_df            validated wide-format DataFrame, one row per (borrower, period)
analysed_df       one row per borrower (latest period), fully scored and explained
validation_errors list of {"row", "borrower_id", "error"} from the last upload
rows_seen         total rows in the last uploaded/loaded file (before validation)
data_source       "demo" or "upload"
selected_borrower borrower_id currently focused on the Borrower / Risk Drivers pages
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from credit.portfolio import analyse_portfolio_df
from data.validation import load_and_validate

DEMO_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "demo_portfolio.csv"


def load_demo_portfolio() -> None:
    valid_df, errors, total = load_and_validate(str(DEMO_PATH))
    _set_session(valid_df, errors, total, source="demo")


def load_uploaded_portfolio(uploaded_file) -> None:
    valid_df, errors, total = load_and_validate(uploaded_file)
    _set_session(valid_df, errors, total, source="upload")


def _set_session(valid_df: pd.DataFrame, errors: list[dict], total: int, source: str) -> None:
    st.session_state["raw_df"] = valid_df
    st.session_state["validation_errors"] = errors
    st.session_state["rows_seen"] = total
    st.session_state["data_source"] = source
    if not valid_df.empty:
        st.session_state["analysed_df"] = analyse_portfolio_df(valid_df)
        borrowers = st.session_state["analysed_df"]["borrower_id"].tolist()
        if st.session_state.get("selected_borrower") not in borrowers:
            st.session_state["selected_borrower"] = borrowers[0] if borrowers else None
    else:
        st.session_state["analysed_df"] = pd.DataFrame()
        st.session_state["selected_borrower"] = None


def has_data() -> bool:
    df = st.session_state.get("analysed_df")
    return df is not None and not df.empty


def get_analysed_df() -> pd.DataFrame:
    return st.session_state.get("analysed_df", pd.DataFrame())


def get_raw_df() -> pd.DataFrame:
    return st.session_state.get("raw_df", pd.DataFrame())


def require_data_or_stop() -> pd.DataFrame:
    """
    Every analytical page calls this first. If there's no data loaded yet,
    show a friendly prompt (rather than crashing on an empty DataFrame) and
    halt the page.
    """
    if not has_data():
        st.info(
            "No portfolio loaded yet. Go to **Home** in the sidebar to load the "
            "demo portfolio or upload your own loan book."
        )
        st.stop()
    return get_analysed_df()
