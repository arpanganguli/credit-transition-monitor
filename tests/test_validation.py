"""Upload validation: bad rows are rejected with a clear reason, good rows pass through."""

import io

import pandas as pd

from credit.portfolio import normalise_columns
from data.validation import validate_portfolio

GOOD_ROW = {
    "borrower": "ABC Ltd", "EAD": 18_000_000, "PD": 0.06, "LGD": 0.45,
    "revenue": 50_000_000, "EBITDA": 8_000_000, "debt": 35_000_000,
    "cash": 4_000_000, "interest": 5_000_000,
}


def _df(rows):
    return normalise_columns(pd.DataFrame(rows))


def test_valid_row_passes():
    valid_df, errors = validate_portfolio(_df([GOOD_ROW]))
    assert len(valid_df) == 1
    assert errors == []
    assert valid_df.iloc[0]["loan_id"] == "ABC Ltd-L1"  # auto-generated when missing


def test_negative_ead_is_rejected_with_row_number():
    bad = dict(GOOD_ROW, borrower="Bad Co", EAD=-5)
    valid_df, errors = validate_portfolio(_df([GOOD_ROW, bad]))
    assert len(valid_df) == 1
    assert len(errors) == 1
    assert errors[0]["borrower_id"] == "Bad Co"
    assert errors[0]["row"] == 3  # header + 1-indexed data row
    assert "ead" in errors[0]["error"]


def test_pd_out_of_range_is_rejected():
    bad = dict(GOOD_ROW, borrower="Bad PD", PD=1.5)
    valid_df, errors = validate_portfolio(_df([bad]))
    assert valid_df.empty
    assert len(errors) == 1


def test_missing_borrower_id_is_rejected():
    bad = dict(GOOD_ROW)
    bad["borrower"] = ""
    valid_df, errors = validate_portfolio(_df([bad]))
    assert valid_df.empty
    assert len(errors) == 1


def test_multiple_good_and_bad_rows_are_partitioned_correctly():
    rows = [GOOD_ROW, dict(GOOD_ROW, borrower="Also Good"), dict(GOOD_ROW, borrower="Bad", LGD=-0.1)]
    valid_df, errors = validate_portfolio(_df(rows))
    assert len(valid_df) == 2
    assert len(errors) == 1


def test_company_name_defaults_to_borrower_id_when_missing():
    valid_df, _ = validate_portfolio(_df([GOOD_ROW]))
    assert valid_df.iloc[0]["company_name"] == "ABC Ltd"
