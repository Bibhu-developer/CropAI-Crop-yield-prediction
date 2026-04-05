from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
sys.path.append(str(BASE_DIR))

from app.utils.encoder import build_preprocessor

try:
    from xgboost import XGBRegressor
except ImportError:  # pragma: no cover - depends on local environment
    XGBRegressor = None


def evaluate_model(name: str, pipeline: Pipeline, X_train, y_train, X_test, y_test) -> dict:
    cv_sample_size = min(20000, len(X_train))
    cv_indices = X_train.sample(n=cv_sample_size, random_state=42).index
    X_cv = X_train.loc[cv_indices]
    y_cv = y_train.loc[cv_indices]
    cv = KFold(n_splits=3, shuffle=True, random_state=42)
    cv_r2 = cross_val_score(pipeline, X_cv, y_cv, cv=cv, scoring="r2", n_jobs=1)
    cv_rmse = -cross_val_score(
        pipeline,
        X_cv,
        y_cv,
        cv=cv,
        scoring="neg_root_mean_squared_error",
        n_jobs=1,
    )

    fitted_pipeline = clone(pipeline)
    fitted_pipeline.fit(X_train, y_train)
    predictions = fitted_pipeline.predict(X_test)

    return {
        "name": name,
        "pipeline": fitted_pipeline,
        "r2_score": float(r2_score(y_test, predictions)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
        "cv_r2_mean": float(cv_r2.mean()),
        "cv_rmse_mean": float(cv_rmse.mean()),
    }


def extract_feature_importance(best_pipeline: Pipeline) -> pd.DataFrame:
    transformed_names = best_pipeline.named_steps["preprocessor"].get_feature_names_out()
    model = best_pipeline.named_steps["model"]
    frame = pd.DataFrame(
        {
            "feature": transformed_names,
            "importance": model.feature_importances_,
        }
    )
    return frame.sort_values("importance", ascending=False).reset_index(drop=True)


def main() -> None:
    # Step 5: Load the processed district-wise dataset.
    dataset_path = DATA_DIR / "processed_training_data.csv"
    if not dataset_path.exists():
        raise FileNotFoundError(
            "processed_training_data.csv not found. Run scripts/preprocess_data.py first."
        )

    df = pd.read_csv(dataset_path)
    feature_columns = [
        "state_name",
        "district_name",
        "crop_name",
        "year",
        "period_group",
        "area_hectares",
        "lagged_yield_1y",
        "rolling_yield_3y",
        "yield_volatility_3y",
        "production_growth_rate",
        "area_growth_rate",
    ]
    target_column = "yield_kg_per_hectare"

    train_df = df[df["year"] <= 2012].copy()
    test_df = df[df["year"] > 2012].copy()
    X_train = train_df[feature_columns]
    y_train = train_df[target_column]
    X_test = test_df[feature_columns]
    y_test = test_df[target_column]

    categorical = ["state_name", "district_name", "crop_name", "period_group"]
    numeric = [column for column in feature_columns if column not in categorical]
    preprocessor = build_preprocessor(categorical, numeric)

    # Step 6: Train multiple models and compare performance.
    candidate_models = {
        "random_forest": RandomForestRegressor(
            n_estimators=140,
            max_depth=18,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
        "gradient_boosting": GradientBoostingRegressor(
            n_estimators=140,
            learning_rate=0.05,
            max_depth=3,
            random_state=42,
        ),
    }
    if XGBRegressor is not None:
        candidate_models["xgboost"] = XGBRegressor(
            n_estimators=180,
            learning_rate=0.06,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_lambda=1.0,
            objective="reg:squarederror",
            random_state=42,
            tree_method="hist",
            n_jobs=-1,
        )

    evaluations = []
    for name, model in candidate_models.items():
        pipeline = Pipeline([("preprocessor", clone(preprocessor)), ("model", model)])
        evaluations.append(evaluate_model(name, pipeline, X_train, y_train, X_test, y_test))

    best_result = sorted(
        evaluations,
        key=lambda item: (-item["r2_score"], item["rmse"]),
    )[0]
    best_pipeline = best_result["pipeline"]
    feature_importances = extract_feature_importance(best_pipeline)

    performance_summary = [
        {
            "model_name": item["name"],
            "r2_score": round(item["r2_score"], 4),
            "rmse": round(item["rmse"], 4),
            "cv_r2_mean": round(item["cv_r2_mean"], 4),
            "cv_rmse_mean": round(item["cv_rmse_mean"], 4),
        }
        for item in evaluations
    ]

    metrics = {
        "best_model": best_result["name"],
        "r2_score": round(best_result["r2_score"], 4),
        "rmse": round(best_result["rmse"], 4),
        "cv_r2_mean": round(best_result["cv_r2_mean"], 4),
        "cv_rmse_mean": round(best_result["cv_rmse_mean"], 4),
        "samples": int(len(df)),
        "train_samples": int(len(train_df)),
        "test_samples": int(len(test_df)),
        "training_features": feature_columns,
        "candidate_models": performance_summary,
        "xgboost_available": XGBRegressor is not None,
        "year_split": {"train_end_year": 2012, "test_start_year": 2013},
    }

    # Step 7: Save model assets and performance logs.
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_pipeline, MODEL_DIR / "yield_model.joblib")
    joblib.dump(metrics, MODEL_DIR / "model_metrics.joblib")
    feature_importances.to_csv(MODEL_DIR / "feature_importance.csv", index=False)
    (MODEL_DIR / "model_performance_log.json").write_text(
        json.dumps(performance_summary, indent=2),
        encoding="utf-8",
    )

    print("Training completed.")
    print(metrics)
    print(feature_importances.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
