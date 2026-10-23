#!/usr/bin/env python3
"""Validate CICFlowMeter CSV features and classify compatible network flows."""
import argparse
import re
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "chronosentinel_supervised.joblib"
SEVERITY = {
    "Normal": "Info",
    "Brute_Force": "High",
    "Port_Scan": "Medium",
    "HTTP_DDoS": "Critical",
    "ICMP_Flood": "High",
    "Web_Crwling": "Low",
}

# Normalization handles the extra quote characters in the training CSV headers.
def norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower().strip().strip("'\"`"))

# Common CICFlowMeter spellings mapped to the MSCAD training feature names.
ALIASES = {
    "flowbytss": "Flow Byts/s",
    "flowbytess": "Flow Byts/s",
    "flowpktss": "Flow Pkts/s",
    "fwdpktss": "Fwd Pkts/s",
    "bwdpktss": "Bwd Pkts/s",
    "totlenfwdpkts": "TotLen Fwd Pkts",
    "totlenbwdpkts": "TotLen Bwd Pkts",
    "fwdpshflags": "Fwd PSH Flags",
    "bwdpshflags": "Bwd PSH Flags",
    "fwdu rgflags": "Fwd URG Flags",
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="CICFlowMeter flow CSV")
    parser.add_argument("--output", default="reports/flow_predictions.csv")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = ROOT / csv_path
    if not csv_path.is_file():
        sys.exit(f"Input CSV not found: {csv_path}")
    if not MODEL_PATH.is_file():
        sys.exit(f"Model not found: {MODEL_PATH}")

    print(f"Reading flows: {csv_path}")
    raw = pd.read_csv(csv_path, low_memory=False)
    raw.columns = [str(c).strip() for c in raw.columns]
    if raw.empty:
        sys.exit("Input CSV has no flow rows.")

    bundle = joblib.load(MODEL_PATH)
    feature_columns = bundle["feature_columns"]
    classes = list(bundle["class_names"])
    pipeline = bundle["pipeline"]

    # Resolve incoming columns to the exact feature names used in training.
    incoming_by_norm = {}
    for col in raw.columns:
        key = norm(col)
        incoming_by_norm.setdefault(key, col)

    resolved = {}
    missing = []
    for trained_name in feature_columns:
        target_key = norm(trained_name)
        source_col = incoming_by_norm.get(target_key)

        if source_col is None:
            alias_target = ALIASES.get(target_key)
            if alias_target:
                source_col = incoming_by_norm.get(norm(alias_target))

        if source_col is None:
            missing.append(trained_name)
        else:
            resolved[trained_name] = source_col

    print(f"Rows: {len(raw):,}")
    print(f"Required model features: {len(feature_columns)}")
    print(f"Matched features: {len(resolved)}")

    if missing:
        print("\nINCOMPATIBLE FLOW SCHEMA — predictions were NOT generated.")
        print("Missing model features:")
        for col in missing:
            print(f"  - {col}")
        print("\nAvailable input columns:")
        for col in raw.columns:
            print(f"  - {col}")
        sys.exit(
            "\nDo not fill missing features with arbitrary zeros. "
            "We need to reconcile extractor fields and training definitions first."
        )

    X = pd.DataFrame(index=raw.index)
    for trained_name in feature_columns:
        X[trained_name] = pd.to_numeric(
            raw[resolved[trained_name]], errors="coerce"
        )

    # Reject rows with invalid feature values rather than inventing measurements.
    valid = np.isfinite(X.to_numpy(dtype=float)).all(axis=1)
    invalid_count = int((~valid).sum())
    if not valid.any():
        sys.exit("No rows have complete, finite numeric values for all required features.")
    if invalid_count:
        print(f"Skipping {invalid_count} rows with missing/non-finite feature values.")

    X_valid = X.loc[valid]
    predictions = pipeline.predict(X_valid)
    probabilities = pipeline.predict_proba(X_valid)
    confidence = probabilities.max(axis=1)

    result = raw.loc[valid].copy()
    result["Predicted_Attack"] = [classes[int(i)] for i in predictions]
    result["Confidence"] = np.round(confidence, 4)
    result["Severity"] = result["Predicted_Attack"].map(SEVERITY).fillna("Review")
    result["Model"] = "MSCAD-trained Random Forest"

    # Confidence is model probability, not calibrated certainty.
    result["Interpretation_Note"] = (
        "Offline model prediction; validate against labelled, representative traffic."
    )

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    print("\nPredicted class counts:")
    print(result["Predicted_Attack"].value_counts().to_string())
    print(f"\nSaved predictions: {output_path}")
    print("No firewall or network settings were changed.")

if __name__ == "__main__":
    main()
