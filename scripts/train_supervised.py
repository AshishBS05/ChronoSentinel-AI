from pathlib import Path
import argparse
import json
import sys
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    precision_recall_fscore_support
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, LabelEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "datasets"
REPORT_DIR = ROOT / "reports"
MODEL_DIR = ROOT / "models"

LABEL_NAMES = {
    "label", "labels", "target", "class", "attack", "attack_type",
    "attack type", "category", "label_name", "traffic_type"
}
IGNORE_COLUMNS = {
    "id", "flow id", "flow_id", "timestamp", "time",
    "source", "source_ip", "destination", "destination_ip"
}

def main():
    parser = argparse.ArgumentParser(
        description="Train and honestly evaluate a supervised network-attack classifier."
    )
    parser.add_argument(
        "--csv", type=Path,
        help="Path to a labelled network-traffic CSV."
    )
    args = parser.parse_args()

    if args.csv:
        csv_path = args.csv.expanduser().resolve()
    else:
        candidates = [
            p for p in DATA_DIR.rglob("*.csv")
            if p.name.lower() not in {
                "local_waf_test_results.csv", "predictions.csv"
            }
            and "report" not in p.parts
        ]
        if len(candidates) == 1:
            csv_path = candidates[0]
        elif not candidates:
            print("\nNO LABELLED DATASET FOUND.")
            print(f"Copy your labelled network-traffic CSV into: {DATA_DIR}")
            print("Then run:")
            print("python scripts/train_supervised.py --csv data/datasets/your_dataset.csv")
            print("\nDo not use local_waf_test_results.csv as the training dataset.")
            sys.exit(2)
        else:
            print("Several CSV files found. Choose the actual labelled dataset:")
            for p in candidates:
                print(f"  {p.relative_to(ROOT)}")
            print("\nRun with --csv <dataset-path>.")
            sys.exit(2)

    if not csv_path.exists():
        sys.exit(f"Dataset not found: {csv_path}")

    print(f"Loading dataset: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    if len(df) < 20:
        sys.exit("Dataset is too small for a meaningful train/test evaluation.")

    # Find the label column using common IDS dataset conventions.
    lookup = {c.lower().strip(): c for c in df.columns}
    label_col = next((lookup[n] for n in LABEL_NAMES if n in lookup), None)
    if label_col is None:
        print("Could not identify the target/label column.")
        print("Columns:", ", ".join(df.columns))
        print("Re-run after checking which column contains the true attack labels.")
        sys.exit(2)

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=[label_col]).drop_duplicates()
    y_raw = df[label_col].astype(str).str.strip()
    valid = y_raw.ne("")
    df, y_raw = df.loc[valid].copy(), y_raw.loc[valid]

    if y_raw.nunique() < 2:
        sys.exit("Need at least two distinct label classes to train a classifier.")

    # Exclude labels and likely identifiers. Keep traffic features.
    excluded = {label_col}
    excluded.update(c for c in df.columns if c.lower().strip() in IGNORE_COLUMNS)
    X = df.drop(columns=list(excluded), errors="ignore")
    X = X.dropna(axis=1, how="all")

    # Avoid accidentally training on a dataset that has no usable features.
    if X.empty:
        sys.exit("No usable feature columns found after excluding labels/identifiers.")

    # Convert numeric-looking strings; retain categorical features when genuinely categorical.
    for col in X.columns:
        if X[col].dtype == "object":
            converted = pd.to_numeric(X[col], errors="coerce")
            nonmissing = X[col].notna().sum()
            if nonmissing and converted.notna().sum() / nonmissing >= 0.95:
                X[col] = converted

    # Remove constant features.
    X = X.loc[:, X.nunique(dropna=False) > 1]
    if X.empty:
        sys.exit("All feature columns are constant or unusable.")

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)

    # A stratified holdout is only possible if each class has enough samples.
    counts = pd.Series(y).value_counts()
    if counts.min() < 2:
        rare = list(label_encoder.classes_[counts.index[counts < 2]])
        sys.exit(
            "At least one class has fewer than 2 rows; a stratified test split "
            f"is not valid. Rare classes: {rare}"
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    numeric_cols = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_cols = [c for c in X.columns if c not in numeric_cols]

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler())
    ])
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encode", OneHotEncoder(handle_unknown="ignore"))
    ])

    transformers = []
    if numeric_cols:
        transformers.append(("numeric", numeric_pipeline, numeric_cols))
    if categorical_cols:
        transformers.append(("categorical", categorical_pipeline, categorical_cols))

    preprocessor = ColumnTransformer(transformers=transformers)
    model = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(
            n_estimators=250,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
            min_samples_leaf=1
        ))
    ])

    print(f"Rows after cleaning: {len(df):,}")
    print(f"Feature columns before encoding: {X.shape[1]}")
    print(f"Classes: {dict(pd.Series(y_raw).value_counts())}")
    print(f"Train rows: {len(X_train):,} | Test rows: {len(X_test):,}")
    print("Training Random Forest...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(X_train, y_train)

    predicted = model.predict(X_test)
    accuracy = accuracy_score(y_test, predicted)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, predicted, average="weighted", zero_division=0
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    bundle = {
        "pipeline": model,
        "label_encoder": label_encoder,
        "feature_columns": X.columns.tolist(),
        "label_column": label_col,
        "class_names": label_encoder.classes_.tolist(),
        "dataset_path": str(csv_path),
        "test_size": 0.2,
        "random_state": 42,
    }
    joblib.dump(bundle, MODEL_DIR / "chronosentinel_supervised.joblib")

    report = classification_report(
        y_test, predicted,
        labels=np.arange(len(label_encoder.classes_)),
        target_names=label_encoder.classes_,
        zero_division=0,
        output_dict=True
    )
    (REPORT_DIR / "supervised_classification_report.json").write_text(
        json.dumps(report, indent=2, default=float)
    )
    (REPORT_DIR / "supervised_metrics.json").write_text(json.dumps({
        "dataset": str(csv_path),
        "rows_after_cleaning": int(len(df)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "feature_count": int(X.shape[1]),
        "label_column": label_col,
        "classes": label_encoder.classes_.tolist(),
        "accuracy": float(accuracy),
        "weighted_precision": float(precision),
        "weighted_recall": float(recall),
        "weighted_f1": float(f1),
        "confusion_matrix": confusion_matrix(
            y_test, predicted,
            labels=np.arange(len(label_encoder.classes_))
        ).tolist(),
        "note": "Holdout results only; performance depends on dataset quality and representativeness."
    }, indent=2))

    cm = confusion_matrix(
        y_test, predicted,
        labels=np.arange(len(label_encoder.classes_))
    )
    pd.DataFrame(
        cm, index=label_encoder.classes_, columns=label_encoder.classes_
    ).to_csv(REPORT_DIR / "supervised_confusion_matrix.csv")

    print("\n=== HELD-OUT TEST RESULTS ===")
    print(f"Accuracy:          {accuracy:.4f}")
    print(f"Weighted precision:{precision:.4f}")
    print(f"Weighted recall:   {recall:.4f}")
    print(f"Weighted F1:       {f1:.4f}")
    print("\nPer-class report:")
    print(classification_report(
        y_test, predicted,
        labels=np.arange(len(label_encoder.classes_)),
        target_names=label_encoder.classes_,
        zero_division=0
    ))
    print("Saved model:   models/chronosentinel_supervised.joblib")
    print("Saved metrics: reports/supervised_metrics.json")
    print("Saved report:  reports/supervised_classification_report.json")
    print("Saved matrix:  reports/supervised_confusion_matrix.csv")
    print("\nThese are test-set results, not a guarantee of real-world detection performance.")

if __name__ == "__main__":
    main()
