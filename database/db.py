"""
Thin SQLite helper: open a connection, apply the schema, and load/save the
normalised core-data-model tables from/to a validated wide-format DataFrame.

No ORM, no migrations framework -- plain sqlite3 and pandas, matching the
build plan's "Python + Pandas + SQLite + Streamlit + Pytest" MVP architecture.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from database.schema import SCHEMA_SQL

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "credit_monitor.db"


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = get_connection(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def save_portfolio(conn: sqlite3.Connection, valid_df: pd.DataFrame, source: str = "CUSTOMER_UPLOAD") -> None:
    """
    Split a validated wide-format portfolio DataFrame into the five
    normalised input tables and upsert them.
    """
    if valid_df.empty:
        return

    borrower_cols = ["borrower_id", "company_name", "company_number", "sector", "country"]
    borrowers = valid_df[[c for c in borrower_cols if c in valid_df.columns]].drop_duplicates("borrower_id")
    for _, row in borrowers.iterrows():
        conn.execute(
            """INSERT INTO borrower (borrower_id, company_name, company_number, sector, country)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(borrower_id) DO UPDATE SET
                 company_name=excluded.company_name,
                 company_number=excluded.company_number,
                 sector=excluded.sector,
                 country=excluded.country""",
            (
                row.get("borrower_id"),
                row.get("company_name"),
                row.get("company_number"),
                row.get("sector"),
                row.get("country"),
            ),
        )

    exposure_cols = ["loan_id", "borrower_id", "ead", "seniority", "maturity", "baseline_pd", "baseline_lgd"]
    exposures = valid_df[[c for c in exposure_cols if c in valid_df.columns]].drop_duplicates("loan_id", keep="last")
    for _, row in exposures.iterrows():
        conn.execute(
            """INSERT INTO exposure (loan_id, borrower_id, ead, seniority, maturity, baseline_pd, baseline_lgd)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(loan_id) DO UPDATE SET
                 ead=excluded.ead, seniority=excluded.seniority, maturity=excluded.maturity,
                 baseline_pd=excluded.baseline_pd, baseline_lgd=excluded.baseline_lgd""",
            (
                row.get("loan_id"),
                row.get("borrower_id"),
                row.get("ead"),
                row.get("seniority"),
                row.get("maturity"),
                row.get("baseline_pd"),
                row.get("baseline_lgd"),
            ),
        )

    fin_cols = ["borrower_id", "period", "revenue", "ebitda", "debt", "cash", "interest_expense", "assets"]
    financials = valid_df[[c for c in fin_cols if c in valid_df.columns]].drop_duplicates(["borrower_id", "period"], keep="last")
    for _, row in financials.iterrows():
        conn.execute(
            """INSERT INTO financials (borrower_id, period, revenue, ebitda, debt, cash, interest_expense, assets, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(borrower_id, period) DO UPDATE SET
                 revenue=excluded.revenue, ebitda=excluded.ebitda, debt=excluded.debt,
                 cash=excluded.cash, interest_expense=excluded.interest_expense,
                 assets=excluded.assets, source=excluded.source""",
            (
                row.get("borrower_id"),
                str(row.get("period")),
                row.get("revenue"),
                row.get("ebitda"),
                row.get("debt"),
                row.get("cash"),
                row.get("interest_expense"),
                row.get("assets"),
                source,
            ),
        )

    if "max_leverage" in valid_df.columns:
        cov_cols = ["loan_id", "max_leverage", "min_interest_cover", "min_liquidity"]
        covenants = valid_df[[c for c in cov_cols if c in valid_df.columns]].drop_duplicates("loan_id", keep="last")
        for _, row in covenants.iterrows():
            conn.execute(
                """INSERT INTO covenants (loan_id, max_leverage, min_interest_cover, min_liquidity)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(loan_id) DO UPDATE SET
                     max_leverage=excluded.max_leverage,
                     min_interest_cover=excluded.min_interest_cover,
                     min_liquidity=excluded.min_liquidity""",
                (row.get("loan_id"), row.get("max_leverage"), row.get("min_interest_cover"), row.get("min_liquidity")),
            )

    if "collateral_value" in valid_df.columns:
        col_cols = ["loan_id", "collateral_type", "collateral_value", "valuation_date"]
        collateral = valid_df[[c for c in col_cols if c in valid_df.columns]].drop_duplicates("loan_id", keep="last")
        for _, row in collateral.iterrows():
            conn.execute(
                """INSERT INTO collateral (loan_id, collateral_type, value, valuation_date)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(loan_id) DO UPDATE SET
                     collateral_type=excluded.collateral_type,
                     value=excluded.value,
                     valuation_date=excluded.valuation_date""",
                (row.get("loan_id"), row.get("collateral_type"), row.get("collateral_value"), row.get("valuation_date")),
            )

    conn.commit()


def save_risk_results(conn: sqlite3.Connection, results_df: pd.DataFrame, as_of: str, loan_id_col: str = "loan_id") -> None:
    """Persist one snapshot of computed risk results."""
    if results_df.empty:
        return
    for _, row in results_df.iterrows():
        conn.execute(
            """INSERT INTO risk_results (loan_id, date, risk_score, pd, lgd, expected_loss, risk_band)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(loan_id, date) DO UPDATE SET
                 risk_score=excluded.risk_score, pd=excluded.pd, lgd=excluded.lgd,
                 expected_loss=excluded.expected_loss, risk_band=excluded.risk_band""",
            (
                row.get(loan_id_col),
                as_of,
                int(row.get("score", 0)) if pd.notna(row.get("score")) else None,
                row.get("pd"),
                row.get("lgd"),
                row.get("expected_loss"),
                row.get("risk_band"),
            ),
        )
    conn.commit()


def load_table(conn: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {table_name}", conn)  # noqa: S608 -- fixed internal table names only
