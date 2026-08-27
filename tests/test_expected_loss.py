import pandas as pd
import pytest

from credit_transition_monitor.expected_loss import calculate_expected_loss

@pytest.mark.parametrize(
    "pd, lgd, ead, expected_loss",
    [
        (0.398942278406721, 0.45, 50003.9894227974, 8976.91746139037),
        (0.398942272422587,0.45,50007.9788455548,8977.63352395783),
        (0.398942262449031,0.45,50011.9682682325,8978.34949670602),
        (0.398942248486052,0.45,50015.9576907905,8979.06537960624),
        (0.398942230533651,0.45,50019.9471131889,8979.78117262988),
        (0.398942208591829,0.45,50023.9365353879,8980.49687574831),
        (0.398942182660586,0.45,50027.9259573475,8981.21248893288),
        (0.398942152739923,0.45,50031.9153790278,8981.92801215496),
        (0.398942152739923,0.45,50031.9153790278,8981.92801215496),
    ],
)

def test_expected_loss(pd, lgd, ead, expected_loss):
    df = pd.DataFrame({
        "pd": [pd],
        "lgd": [lgd],
        "ead": [ead],
    })

    result = calculate_expected_loss(df)

    assert result["expected_loss"].iloc[0] == pytest.approx(expected_loss, rel=1e-9)