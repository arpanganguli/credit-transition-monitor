import pandas as pd
import pytest

from credit_transition_monitor.calculate_changes import calculate_changes

@pytest.mark.parametrize(
    "borrower_id", "period", "ebitda", "revenue", "leverage", "interest_cover", "delta_ebitda", "delta_revenue",
    "delta_leverage", "delta_interest_cover", "ebitda_change_pct", "revenue_change_pct", "leverage_change_pct",
    "interest_cover_change_pct",
    [
        (1, 202603, 100, 25, 12, 3, ,
        (2, 202603),
    ],
)

