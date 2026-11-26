"""Random Forest model for application-level suspicious-session detection."""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

FEATURES = [
    "requests_per_min", "failed_logins", "not_found_count",
    "client_error_count", "server_error_count", "unique_routes",
    "route_entropy", "post_ratio", "admin_requests",
    "suspicious_pattern_hits", "burstiness", "distinct_methods"
]
MODEL_PATH = Path("models/attacker_model.pkl")
DATA_PATH = Path("data/app_security_training.csv")

def make_demo_dataset(rows=6000, seed=42):
    """Creates transparent, labelled app-telemetry examples for reproducible training.
    Replace/augment this CSV with labelled sessions exported from your own app.
    """
    rng = np.random.default_rng(seed)
    labels = rng.choice([0, 1], size=rows, p=[0.65, 0.35])
    records = []
    for y in labels:
        if y == 0:
            vals = [
                rng.gamma(2, 2), rng.poisson(.08), rng.poisson(.15),
                rng.poisson(.25), rng.poisson(.03), rng.integers(2, 10),
                rng.uniform(.5, 2.3), rng.uniform(0, .35), rng.poisson(.02),
                rng.poisson(.01), rng.uniform(.05, .65), rng.integers(1, 4)
            ]
        else:
            kind = rng.integers(0, 4)
            vals = [
                rng.uniform(18, 100) if kind in (0, 1) else rng.uniform(2, 35),
                rng.poisson(5 if kind == 1 else 1.5),
                rng.poisson(7 if kind == 2 else 2),
                rng.poisson(12), rng.poisson(1.5), rng.integers(1, 18),
                rng.uniform(0, 3.5), rng.uniform(.2, .95),
                rng.poisson(4 if kind == 3 else 1),
                rng.poisson(5 if kind in (2, 3) else 2),
                rng.uniform(.35, 1), rng.integers(1, 5)
            ]
        records.append(vals + [int(y)])
    return pd.DataFrame(records, columns=FEATURES + ["label"])

def train_model(csv_path=DATA_PATH, model_path=MODEL_PATH):
    csv_path, model_path = Path(csv_path), Path(model_path)
    if not csv_path.exists():
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        make_demo_dataset().to_csv(csv_path, index=False)
        print(f"[DATA] Created reproducible labelled demo dataset: {csv_path}")
    df = pd.read_csv(csv_path)
    missing = set(FEATURES + ["label"]) - set(df.columns)
    if missing:
        raise ValueError(f"Training CSV is missing columns: {sorted(missing)}")
    X = df[FEATURES].replace([np.inf, -np.inf], np.nan)
    y = df["label"].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("rf", RandomForestClassifier(
            n_estimators=300, max_depth=14, min_samples_leaf=2,
            class_weight="balanced", random_state=42, n_jobs=-1
        ))
    ])
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    print("\n=== Random Forest evaluation (held-out test split) ===")
    print(classification_report(y_test, pred, target_names=["normal", "suspicious"]))
    print("Confusion matrix:\n", confusion_matrix(y_test, pred))
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES}, model_path)
    print(f"[SAVED] {model_path.resolve()}")
    return model

def load_model(model_path=MODEL_PATH):
    obj = joblib.load(model_path)
    return obj["model"]

def predict_session(model, features):
    row = pd.DataFrame([{k: features.get(k, 0) for k in FEATURES}], columns=FEATURES)
    probability = float(model.predict_proba(row)[0][1])
    return probability, probability >= 0.65


if __name__ == "__main__":
    train_model()
