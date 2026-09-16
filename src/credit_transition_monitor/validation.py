from io import BytesIO
from pathlib import Path
import numpy as np
import pandas as pd

NUMERIC = ["ead", "baseline_pd", "baseline_lgd", "revenue", "ebitda", "debt", "cash", "interest_expense", "max_leverage", "min_interest_cover", "min_liquidity", "collateral_value"]
REQUIRED = ["borrower_id", "company_name", "period", "currency", *NUMERIC]
ALIASES = {"borrower": "company_name", "pd": "baseline_pd", "lgd": "baseline_lgd", "interest": "interest_expense", "max_leverage_covenant": "max_leverage"}
class ValidationError(ValueError):
    """Actionable input errors; no partial or silently repaired analysis."""

def read_portfolio(source, filename=None):
    name = filename or str(source)
    suffix = Path(name).suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(BytesIO(source) if isinstance(source, bytes) else source, dtype={"borrower_id": str, "loan_id": str, "company_number": str})
        if suffix == ".xlsx":
            return pd.read_excel(BytesIO(source) if isinstance(source, bytes) else source, sheet_name=0, dtype={"borrower_id": str, "loan_id": str, "company_number": str})
    except Exception as exc:
        raise ValidationError(f"Could not read {suffix} file: {exc}") from exc
    raise ValidationError("Use a CSV or XLSX file; XLSX uses the first worksheet.")

def validate_portfolio(frame):
    d = frame.copy()
    d.columns = [ALIASES.get(str(c).strip().lower(), str(c).strip().lower()) for c in d.columns]
    if d.columns.duplicated().any():
        raise ValidationError("Duplicate columns after normalising headers.")
    missing = sorted(set(REQUIRED) - set(d))
    if missing:
        raise ValidationError("Missing columns: " + ", ".join(missing))
    if d.empty:
        raise ValidationError("Portfolio contains no rows.")
    errors = []
    for c in ["borrower_id", "company_name", "currency"]:
        if d[c].isna().any() or d[c].astype(str).str.strip().eq("").any():
            errors.append(f"{c}: blank values")
        d[c] = d[c].astype(str).str.strip()
    d["currency"] = d.currency.str.upper()
    if d.currency.nunique() != 1 or not d.currency.str.fullmatch(r"[A-Z]{3}").all():
        errors.append("Use one three-letter currency throughout; no FX conversion is assumed")
    d["period"] = pd.to_datetime(d.period, errors="coerce", format="mixed")
    if d.period.isna().any():
        errors.append("period: invalid date; use YYYY-MM-DD")
    for c in NUMERIC:
        d[c] = pd.to_numeric(d[c], errors="coerce").astype(float)
        bad = ~np.isfinite(d[c])
        if bad.any():
            errors.append(f"{c}: missing/non-finite numeric values at data rows {list(np.flatnonzero(bad)[:5]+1)}")
    for c in set(NUMERIC) - {"ebitda"}:
        if (d[c] < 0).any():
            errors.append(f"{c}: cannot be negative")
    for c in ["revenue", "interest_expense", "max_leverage", "min_interest_cover"]:
        if (d[c] <= 0).any():
            errors.append(f"{c}: must be greater than zero")
    for c in ["baseline_pd", "baseline_lgd"]:
        if (d[c] > 1).any():
            errors.append(f"{c}: use decimal probabilities between 0 and 1")
    if d.duplicated(["borrower_id", "period"]).any():
        errors.append("Duplicate borrower/period: this MVP accepts one consolidated exposure per borrower")
    if d.groupby("borrower_id").company_name.nunique().gt(1).any():
        errors.append("company_name must be consistent within borrower_id")
    if d.groupby("borrower_id").period.nunique().ne(d.period.nunique()).any():
        errors.append("Every borrower must have all reporting dates; use a balanced panel for comparable portfolio movements")
    if errors:
        raise ValidationError("\n".join(errors))
    d["sector"] = d.get("sector", "Unspecified")
    return d.sort_values(["borrower_id", "period"]).reset_index(drop=True)
