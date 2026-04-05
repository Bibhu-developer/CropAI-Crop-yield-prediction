from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .data_repository import DataRepository


@dataclass
class PredictionResult:
    yield_kg_per_hectare: float
    yield_tons_per_hectare: float
    total_yield_tons: float
    confidence_percent: float


class ModelService:
    def __init__(self, model_dir: Path, data_dir: Path, repository: DataRepository) -> None:
        self.model_path = model_dir / "yield_model.joblib"
        self.metrics_path = model_dir / "model_metrics.joblib"
        self.feature_importance_path = model_dir / "feature_importance.csv"
        self.training_data_path = data_dir / "processed_training_data.csv"
        self.repository = repository
        self._model = None
        self._metrics = None

    def load_assets(self) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(
                "Trained model not found. Run backend/scripts/preprocess_data.py and backend/scripts/train_model.py."
            )
        if not self.training_data_path.exists():
            raise FileNotFoundError(
                "Processed training data missing. Run backend/scripts/preprocess_data.py."
            )
        self._model = joblib.load(self.model_path)
        self._metrics = joblib.load(self.metrics_path)

    @property
    def model(self):
        if self._model is None:
            self.load_assets()
        return self._model

    @property
    def metrics(self) -> dict[str, Any]:
        if self._metrics is None:
            self.load_assets()
        return self._metrics

    def predict(self, payload: dict[str, Any], context: dict[str, Any] | None = None) -> PredictionResult:
        model_input = pd.DataFrame([payload])
        prediction = float(self.model.predict(model_input)[0])
        confidence = self._calculate_confidence(prediction, payload, context or {})
        total_yield_tons = prediction * float(payload["area_hectares"]) / 1000
        return PredictionResult(
            yield_kg_per_hectare=round(prediction, 2),
            yield_tons_per_hectare=round(prediction / 1000, 3),
            total_yield_tons=round(total_yield_tons, 2),
            confidence_percent=round(confidence, 1),
        )

    def recommend_best_crop(self, payload: dict[str, Any]) -> dict[str, Any]:
        crop_candidates = self.repository.get_available_crops_for_district(
            payload["state_name"],
            payload["district_name"],
        )
        if not crop_candidates:
            crop_candidates = self.repository.get_supported_crops()

        target_forecast_year = int(payload["year"])
        target_history_year = target_forecast_year - 1
        scored_predictions = []
        for crop_name in crop_candidates:
            district_profile = self.repository.get_district_crop_profile_for_year(
                payload["state_name"],
                payload["district_name"],
                crop_name,
                target_history_year,
            )
            if district_profile is None:
                continue

            scenario = {
                "state_name": payload["state_name"],
                "district_name": payload["district_name"],
                "crop_name": crop_name,
                "year": target_forecast_year,
                "period_group": self._infer_period_group(target_forecast_year),
                "area_hectares": float(payload["area_hectares"]),
                "lagged_yield_1y": district_profile["lagged_yield_1y"],
                "rolling_yield_3y": district_profile["rolling_yield_3y"],
                "yield_volatility_3y": district_profile["yield_volatility_3y"],
                "production_growth_rate": district_profile["production_growth_rate"],
                "area_growth_rate": district_profile["area_growth_rate"],
            }
            result = self.predict(scenario, context=district_profile)
            crop_stats = self.repository.get_crop_statistics(crop_name) or {
                "median_yield_kg_per_hectare": max(result.yield_kg_per_hectare, 1.0),
                "median_area_hectares": max(float(payload["area_hectares"]), 1.0),
            }
            suitability_score = self._calculate_suitability_score(
                predicted_yield=result.yield_kg_per_hectare,
                district_profile=district_profile,
                crop_stats=crop_stats,
                confidence_percent=result.confidence_percent,
                target_history_year=target_history_year,
            )
            recency_gap = max(target_history_year - district_profile["year"], 0)
            scored_predictions.append(
                {
                    "crop_name": crop_name,
                    "yield_kg_per_hectare": result.yield_kg_per_hectare,
                    "yield_tons_per_hectare": result.yield_tons_per_hectare,
                    "confidence_percent": result.confidence_percent,
                    "suitability_score": suitability_score,
                    "recency_gap_years": recency_gap,
                }
            )

        reliable_candidates = [
            item
            for item in scored_predictions
            if item["confidence_percent"] >= 60 and item["recency_gap_years"] <= 2
        ]
        ranked_candidates = sorted(
            reliable_candidates or scored_predictions,
            key=lambda item: item["suitability_score"],
            reverse=True,
        )
        best = ranked_candidates[0]
        return {
            "best_crop": best,
            "alternatives": ranked_candidates[:4],
        }

    @staticmethod
    def _infer_period_group(year: int) -> str:
        if year <= 1987:
            return "1978-1987"
        if year <= 1997:
            return "1988-1997"
        if year <= 2007:
            return "1998-2007"
        return "2008-2017"

    @staticmethod
    def _calculate_suitability_score(
        predicted_yield: float,
        district_profile: dict[str, Any],
        crop_stats: dict[str, Any],
        confidence_percent: float,
        target_history_year: int,
    ) -> float:
        median_yield = max(crop_stats["median_yield_kg_per_hectare"], 1.0)
        median_area = max(crop_stats["median_area_hectares"], 1.0)
        rolling_yield = max(district_profile["rolling_yield_3y"], 1.0)
        recency_gap = max(target_history_year - district_profile["year"], 0)

        relative_yield = predicted_yield / median_yield
        growth_component = max(0.55, min(1.45, 1 + district_profile["production_growth_rate"]))
        area_component = max(0.5, min(1.25, district_profile["last_recorded_area_hectares"] / median_area))
        stability_component = 1 / (1 + (district_profile["yield_volatility_3y"] / rolling_yield))
        confidence_component = max(0.6, min(confidence_percent / 100, 0.95))
        recency_component = max(0.45, 1 - (recency_gap * 0.08))

        score = (
            (relative_yield * 0.4)
            + (growth_component * 0.12)
            + (area_component * 0.12)
            + (stability_component * 0.12)
            + (confidence_component * 0.14)
            + (recency_component * 0.1)
        )
        return round(score, 3)

    def _calculate_confidence(
        self,
        prediction: float,
        payload: dict[str, Any],
        context: dict[str, Any],
    ) -> float:
        base_confidence = 45 + (float(self.metrics["r2_score"]) * 28)

        rolling_yield = max(float(context.get("rolling_yield_3y", payload.get("rolling_yield_3y", 0)) or 0), 1.0)
        lagged_yield = max(float(context.get("lagged_yield_1y", payload.get("lagged_yield_1y", 0)) or 0), 1.0)
        volatility = max(float(context.get("yield_volatility_3y", payload.get("yield_volatility_3y", 0)) or 0), 0.0)
        production_growth = float(
            context.get("production_growth_rate", payload.get("production_growth_rate", 0)) or 0
        )
        area_growth = float(context.get("area_growth_rate", payload.get("area_growth_rate", 0)) or 0)

        deviation_from_recent = abs(prediction - rolling_yield) / rolling_yield
        deviation_from_last_year = abs(prediction - lagged_yield) / lagged_yield
        volatility_ratio = volatility / rolling_yield
        growth_penalty = min(abs(production_growth) + abs(area_growth), 1.2)

        confidence = (
            base_confidence
            - (deviation_from_recent * 14)
            - (deviation_from_last_year * 10)
            - (volatility_ratio * 16)
            - (growth_penalty * 8)
        )

        if deviation_from_recent < 0.08:
            confidence += 3.0
        if volatility_ratio < 0.12:
            confidence += 2.0

        return max(52.0, min(94.0, round(confidence, 1)))

    def get_feature_importance(self) -> list[dict[str, Any]]:
        frame = pd.read_csv(self.feature_importance_path).head(10)
        return frame.to_dict(orient="records")

    def get_yearly_yield_trend(self, crop_name: str | None = None) -> list[dict[str, Any]]:
        frame = pd.read_csv(self.training_data_path)
        if crop_name:
            frame = frame[frame["crop_name"].str.lower() == crop_name.lower()].copy()
        return (
            frame.groupby("year", as_index=False)["yield_kg_per_hectare"]
            .mean()
            .rename(columns={"yield_kg_per_hectare": "average_yield_kg_per_ha"})
            .sort_values("year")
            .to_dict(orient="records")
        )
