from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover
    XGBClassifier = None


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"


def build_preprocessor() -> ColumnTransformer:
    numeric_features = [
        "temperature",
        "humidity",
        "moisture",
        "nitrogen",
        "phosphorus",
        "potassium",
    ]
    categorical_features = ["soil_type"]

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )


def clean_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.rename(
        columns={
            "Temparature": "temperature",
            "Humidity": "humidity",
            "Moisture": "moisture",
            "Soil Type": "soil_type",
            "Crop Type": "crop_type",
            "Nitrogen": "nitrogen",
            "Potassium": "potassium",
            "Phosphorous": "phosphorus",
            "Fertilizer Name": "fertilizer_name",
        }
    ).copy()

    cleaned["soil_type"] = cleaned["soil_type"].astype(str).str.strip().str.title()
    cleaned["crop_type"] = cleaned["crop_type"].astype(str).str.strip().str.title()
    cleaned["fertilizer_name"] = cleaned["fertilizer_name"].astype(str).str.strip()

    numeric_columns = [
        "temperature",
        "humidity",
        "moisture",
        "nitrogen",
        "phosphorus",
        "potassium",
    ]
    for column in numeric_columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.dropna(subset=["crop_type", "soil_type"])
    cleaned[numeric_columns] = cleaned[numeric_columns].fillna(cleaned[numeric_columns].median())
    return cleaned


def main() -> None:
    dataset_path = DATA_DIR / "soil_recommendation_core.csv"
    if not dataset_path.exists():
        raise FileNotFoundError(
            "soil_recommendation_core.csv not found. Copy the provided soil dataset into backend/data first."
        )

    frame = clean_dataset(pd.read_csv(dataset_path))
    feature_columns = [
        "temperature",
        "humidity",
        "moisture",
        "soil_type",
        "nitrogen",
        "phosphorus",
        "potassium",
    ]

    label_encoder = LabelEncoder()
    X = frame[feature_columns]
    y = label_encoder.fit_transform(frame["crop_type"])

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    candidate_models = {
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=14,
            random_state=42,
            n_jobs=-1,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=180,
            learning_rate=0.08,
            max_depth=3,
            random_state=42,
        ),
    }

    if XGBClassifier is not None:
        candidate_models["xgboost"] = XGBClassifier(
            n_estimators=180,
            learning_rate=0.08,
            max_depth=6,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
        )

    evaluations = []
    for model_name, estimator in candidate_models.items():
        pipeline = Pipeline(
            [
                ("preprocessor", build_preprocessor()),
                ("model", estimator),
            ]
        )
        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)
        evaluations.append(
            {
                "model_name": model_name,
                "pipeline": pipeline,
                "accuracy": float(accuracy_score(y_test, predictions)),
                "f1_weighted": float(f1_score(y_test, predictions, average="weighted")),
            }
        )

    best_result = sorted(
        evaluations,
        key=lambda item: (-item["accuracy"], -item["f1_weighted"]),
    )[0]

    fertilizer_lookup = (
        frame.groupby(["crop_type", "soil_type"])["fertilizer_name"]
        .agg(lambda series: series.mode().iat[0] if not series.mode().empty else series.iloc[0])
        .reset_index()
        .to_dict(orient="records")
    )

    crop_profiles = (
        frame.groupby(["crop_type", "soil_type"], as_index=False)
        .agg(
            temperature=("temperature", "median"),
            humidity=("humidity", "median"),
            moisture=("moisture", "median"),
            nitrogen=("nitrogen", "median"),
            phosphorus=("phosphorus", "median"),
            potassium=("potassium", "median"),
        )
        .to_dict(orient="records")
    )

    metrics = {
        "best_model": best_result["model_name"],
        "accuracy": round(best_result["accuracy"], 4),
        "f1_weighted": round(best_result["f1_weighted"], 4),
        "candidate_models": [
            {
                "model_name": item["model_name"],
                "accuracy": round(item["accuracy"], 4),
                "f1_weighted": round(item["f1_weighted"], 4),
            }
            for item in evaluations
        ],
        "samples": int(len(frame)),
        "xgboost_available": XGBClassifier is not None,
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_result["pipeline"], MODEL_DIR / "crop_model.pkl")
    joblib.dump(
        {
            "label_encoder": label_encoder,
            "feature_columns": feature_columns,
            "fertilizer_lookup": fertilizer_lookup,
            "crop_profiles": crop_profiles,
        },
        MODEL_DIR / "encoders.pkl",
    )
    (MODEL_DIR / "crop_model_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("Crop recommendation model training completed.")
    print(metrics)


if __name__ == "__main__":
    main()

