"""
Upload validation: turn a raw CSV/Excel loan book into clean, typed rows plus
a list of every row that was rejected and why.

"Missing-data handling is part of the product" (Week 3 of the build plan) --
so this module never silently drops a bad row. Every rejection is returned
with the original row number and a human-readable reason, ready to show in
the Streamlit upload screen (e.g. "487 loans loaded; 3 validation errors").
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from credit.portfolio import normalise_columns


class PortfolioRow(BaseModel):
    """
    One row of the wide-format portfolio file: one borrower, one loan, one
    reporting period, with its financials, covenants and collateral attached.
    This is deliberately denormalised (matches how a credit team actually
    exports a loan book) -- the database layer splits it into the six
    normalised core-data-model tables on ingest.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    borrower_id: str = Field(min_length=1)
    company_name: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    company_number: Optional[str] = None

    loan_id: Optional[str] = None
    seniority: Optional[str] = None
    maturity: Optional[str] = None

    period: Optional[str] = None
    ead: float = Field(gt=0)
    baseline_pd: float = Field(ge=0.0, lt=1.0)
    baseline_lgd: float = Field(ge=0.0, le=1.0)

    revenue: float = Field(ge=0)
    ebitda: float
    debt: float = Field(ge=0)
    cash: float = Field(ge=0)
    interest_expense: float = Field(ge=0)
    assets: Optional[float] = None

    max_leverage: Optional[float] = None
    min_interest_cover: Optional[float] = None
    min_liquidity: Optional[float] = None

    collateral_type: Optional[str] = None
    collateral_value: Optional[float] = Field(default=None, ge=0)
    valuation_date: Optional[str] = None

    @field_validator("loan_id", mode="before")
    @classmethod
    def _default_loan_id(cls, v, info):
        return v

    @field_validator("ebitda")
    @classmethod
    def _ebitda_sane(cls, v):
        # EBITDA can legitimately be negative (loss-making borrower) -- that
        # is exactly the kind of borrower this product exists to flag. We
        # only reject implausible magnitudes that are almost certainly a
        # data-entry error (e.g. a stray extra zero).
        if abs(v) > 1e12:
            raise ValueError("EBITDA magnitude is implausibly large -- check units")
        return v


def load_portfolio_file(path_or_buffer) -> pd.DataFrame:
    """Read a CSV or Excel file into a raw (unvalidated) DataFrame."""
    name = getattr(path_or_buffer, "name", str(path_or_buffer))
    if str(name).lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path_or_buffer)
    else:
        df = pd.read_csv(path_or_buffer)
    return normalise_columns(df)


def validate_portfolio(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Validate every row of a raw, column-normalised portfolio DataFrame.

    Returns (valid_df, errors) where valid_df contains only the rows that
    passed validation (with a ``loan_id`` filled in if one was missing), and
    errors is a list of {"row": <1-based row number>, "borrower_id": ..., "error": ...}.
    """
    valid_rows: list[dict] = []
    errors: list[dict] = []

    for i, raw_row in enumerate(df.to_dict(orient="records")):
        row_number = i + 2  # +1 for 0-index, +1 for the header row
        try:
            record = PortfolioRow(**raw_row)
        except ValidationError as exc:
            messages = "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in exc.errors())
            errors.append(
                {
                    "row": row_number,
                    "borrower_id": raw_row.get("borrower_id", "?"),
                    "error": messages,
                }
            )
            continue

        d = record.model_dump()
        if not d.get("loan_id"):
            d["loan_id"] = f"{d['borrower_id']}-L1"
        if not d.get("company_name"):
            d["company_name"] = d["borrower_id"]
        valid_rows.append(d)

    valid_df = pd.DataFrame(valid_rows)
    return valid_df, errors


def load_and_validate(path_or_buffer) -> tuple[pd.DataFrame, list[dict], int]:
    """
    Convenience wrapper: load a file and validate it in one call.

    Returns (valid_df, errors, total_rows_seen).
    """
    raw_df = load_portfolio_file(path_or_buffer)
    valid_df, errors = validate_portfolio(raw_df)
    return valid_df, errors, len(raw_df)
