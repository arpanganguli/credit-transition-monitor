"""
The core data model (Week 1 of the build plan), as SQLite DDL.

    borrower:     borrower_id, company_name, company_number, sector, country
    exposure:     loan_id, borrower_id, ead, currency, seniority, maturity,
                  baseline_pd, baseline_lgd
    financials:   borrower_id, period, revenue, ebitda, debt, cash,
                  interest_expense, assets, source
    covenants:    loan_id, max_leverage, min_interest_cover, min_liquidity
    collateral:   loan_id, collateral_type, value, valuation_date
    risk_results: loan_id, date, risk_score, pd, lgd, expected_loss, risk_band

Plain sqlite3 (stdlib), no ORM -- deliberately, per the build plan's "do not
build a complicated architecture initially" guidance. ``financials`` carries
an extra ``source`` column beyond the spec's minimum so every number's
provenance (CUSTOMER_UPLOAD / COMPANIES_HOUSE / MANUAL_OVERRIDE) survives
into the database, not just the upload screen.
"""

from __future__ import annotations

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS borrower (
    borrower_id     TEXT PRIMARY KEY,
    company_name    TEXT NOT NULL,
    company_number  TEXT,
    sector          TEXT,
    country         TEXT
);

CREATE TABLE IF NOT EXISTS exposure (
    loan_id         TEXT PRIMARY KEY,
    borrower_id     TEXT NOT NULL REFERENCES borrower(borrower_id),
    ead             REAL NOT NULL,
    currency        TEXT DEFAULT 'GBP',
    seniority       TEXT,
    maturity        TEXT,
    baseline_pd     REAL,
    baseline_lgd    REAL
);

CREATE TABLE IF NOT EXISTS financials (
    borrower_id       TEXT NOT NULL REFERENCES borrower(borrower_id),
    period            TEXT NOT NULL,
    revenue           REAL,
    ebitda            REAL,
    debt              REAL,
    cash              REAL,
    interest_expense  REAL,
    assets            REAL,
    source            TEXT DEFAULT 'CUSTOMER_UPLOAD',
    PRIMARY KEY (borrower_id, period)
);

CREATE TABLE IF NOT EXISTS covenants (
    loan_id             TEXT PRIMARY KEY REFERENCES exposure(loan_id),
    max_leverage        REAL,
    min_interest_cover  REAL,
    min_liquidity       REAL
);

CREATE TABLE IF NOT EXISTS collateral (
    loan_id           TEXT PRIMARY KEY REFERENCES exposure(loan_id),
    collateral_type   TEXT,
    value             REAL,
    valuation_date    TEXT
);

CREATE TABLE IF NOT EXISTS risk_results (
    loan_id         TEXT NOT NULL REFERENCES exposure(loan_id),
    date            TEXT NOT NULL,
    risk_score      INTEGER,
    pd              REAL,
    lgd             REAL,
    expected_loss   REAL,
    risk_band       TEXT,
    PRIMARY KEY (loan_id, date)
);
"""
