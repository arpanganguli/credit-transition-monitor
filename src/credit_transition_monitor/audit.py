from datetime import datetime, timezone
from hashlib import sha256
import json
import sqlite3
import pandas as pd
from .validation import NUMERIC

MODEL_VERSION = "week2-v1.0"
def input_provenance(frame, source, digest):
    rows = []
    for _,r in frame.iterrows():
        for c in NUMERIC:
            rows.append({"borrower_id": r.borrower_id, "period": str(r.period), "field": c, "value": float(r[c]), "source": source, "sha256": digest})
    return pd.DataFrame(rows)

def audit_bundle(raw, results, original_bytes, source, scenario, stressed):
    digest = sha256(original_bytes).hexdigest()
    meta = {"calculated_at_utc": datetime.now(timezone.utc).isoformat(), "model_version": MODEL_VERSION, "input_sha256": digest, "source": source, "scenario": scenario, "warning": "Prototype assumptions; not calibrated or regulatory models", "pd_horizon": "Same horizon as lender-supplied baseline PD; no horizon conversion", "derived_source": "CALCULATED", "lgd_assumption": "1 - (1 - baseline_lgd) * (1 + collateral_shock), clipped [0,1]"}
    connection = sqlite3.connect(":memory:")
    for name,df in {"normalised_inputs":raw, "risk_results":results, "scenario_results":stressed, "input_provenance":input_provenance(raw,source,digest)}.items():
        df.to_sql(name,connection,index=False)
    connection.execute("CREATE TABLE run_metadata (json TEXT)")
    connection.execute("INSERT INTO run_metadata VALUES (?)", (json.dumps(meta),))
    connection.commit()
    payload = connection.serialize()
    connection.close()
    return meta, payload
