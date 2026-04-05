from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd


class CropRecommendationService:
    def __init__(self, model_dir: Path) -> None:
        self.model_path = model_dir / "crop_model.pkl"
        self.encoders_path = model_dir / "encoders.pkl"
        self.metrics_path = model_dir / "crop_model_metrics.json"
        self._model = None
        self._assets = None
        self._feature_ranges = None

    CROP_ALIAS_MAP = {
        "rice": "Paddy",
        "paddy": "Paddy",
        "wheat": "Wheat",
        "maize": "Maize",
        "cotton": "Cotton",
        "barley": "Barley",
        "sugarcane": "Sugarcane",
        "tobacco": "Tobacco",
        "groundnut": "Ground Nuts",
        "ground nuts": "Ground Nuts",
        "soyabean": "Oil Seeds",
        "soybean": "Oil Seeds",
        "sesamum": "Oil Seeds",
        "safflower": "Oil Seeds",
        "linseed": "Oil Seeds",
        "oilseeds": "Oil Seeds",
        "oil seeds": "Oil Seeds",
        "rapeseed": "Oil Seeds",
        "mustard": "Oil Seeds",
        "sunflower": "Oil Seeds",
        "castor": "Oil Seeds",
        "nigerseed": "Oil Seeds",
        "niger seed": "Oil Seeds",
        "pigeonpea": "Pulses",
        "pulses": "Pulses",
        "minor pulses": "Pulses",
        "gram": "Pulses",
        "peas & beans": "Pulses",
        "peas and beans": "Pulses",
        "moong": "Pulses",
        "urad": "Pulses",
        "jowar": "Millets",
        "bajra": "Millets",
        "ragi": "Millets",
        "millets": "Millets",
    }

    def load_assets(self) -> None:
        if not self.model_path.exists() or not self.encoders_path.exists():
            raise FileNotFoundError(
                "Crop recommendation model assets are missing. Run backend/scripts/train_crop_recommendation_model.py first."
            )
        self._model = joblib.load(self.model_path)
        self._assets = joblib.load(self.encoders_path)

    @property
    def model(self):
        if self._model is None:
            self.load_assets()
        return self._model

    @property
    def assets(self):
        if self._assets is None:
            self.load_assets()
        return self._assets

    @property
    def feature_ranges(self) -> dict[str, tuple[float, float]]:
        if self._feature_ranges is None:
            numeric_features = [
                "temperature",
                "humidity",
                "moisture",
                "nitrogen",
                "phosphorus",
                "potassium",
            ]
            profiles = self.assets.get("crop_profiles", [])
            self._feature_ranges = {}
            for feature in numeric_features:
                values = [float(row[feature]) for row in profiles if row.get(feature) is not None]
                if not values:
                    self._feature_ranges[feature] = (0.0, 1.0)
                    continue
                self._feature_ranges[feature] = (min(values), max(values))
        return self._feature_ranges

    def recommend(
        self,
        weather: dict[str, Any],
        soil_profile: dict[str, Any],
        candidate_crops: list[str] | None = None,
        candidate_priors: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "temperature": float(weather["temperature_c"]),
            "humidity": float(weather["humidity_percent"]),
            "moisture": float(soil_profile["moisture"]),
            "soil_type": str(soil_profile["soil_type"]).title(),
            "nitrogen": float(soil_profile["nitrogen"]),
            "phosphorus": float(soil_profile["phosphorus"]),
            "potassium": float(soil_profile["potassium"]),
        }
        model_input = pd.DataFrame([payload])[self.assets["feature_columns"]]
        predicted_encoded = self.model.predict(model_input)[0]
        probabilities = self.model.predict_proba(model_input)[0]

        label_encoder = self.assets["label_encoder"]
        model_classes = [str(label) for label in label_encoder.classes_]
        probability_lookup = {
            crop_name: float(probabilities[index]) for index, crop_name in enumerate(model_classes)
        }

        normalized_candidates = self._resolve_candidate_crops(candidate_crops, model_classes)
        ranked_candidates = self._rank_candidates(
            payload,
            probability_lookup,
            normalized_candidates,
            candidate_priors or {},
        )

        recommended_crop = ranked_candidates[0]["crop_name"] if ranked_candidates else str(
            label_encoder.inverse_transform([predicted_encoded])[0]
        )
        recommended_fertilizer = self._resolve_fertilizer(recommended_crop, payload["soil_type"])

        top_candidates = ranked_candidates[:3]

        return {
            "recommended_crop": recommended_crop,
            "recommended_fertilizer": recommended_fertilizer,
            "top_crop_candidates": top_candidates,
            "input_vector": payload,
        }

    def _resolve_candidate_crops(
        self,
        candidate_crops: list[str] | None,
        model_classes: list[str],
    ) -> list[str]:
        if not candidate_crops:
            return model_classes

        normalized = []
        seen = set()
        for crop_name in candidate_crops:
            mapped_crop = self.CROP_ALIAS_MAP.get(str(crop_name).strip().lower())
            if mapped_crop and mapped_crop in model_classes and mapped_crop not in seen:
                normalized.append(mapped_crop)
                seen.add(mapped_crop)

        return normalized or model_classes

    def _rank_candidates(
        self,
        payload: dict[str, float | str],
        probability_lookup: dict[str, float],
        candidate_crops: list[str],
        candidate_priors: dict[str, float],
    ) -> list[dict[str, Any]]:
        ranked = []
        profiles = self.assets.get("crop_profiles", [])

        for crop_name in candidate_crops:
            crop_profiles = [profile for profile in profiles if profile.get("crop_type") == crop_name]
            similarity_score = self._score_crop_similarity(payload, crop_profiles)
            model_probability = probability_lookup.get(crop_name, 0.0)
            local_prior = float(candidate_priors.get(crop_name, 0.0))
            final_score = (0.45 * similarity_score) + (0.20 * model_probability) + (0.35 * local_prior)
            ranked.append(
                {
                    "crop_name": crop_name,
                    "probability_percent": round(final_score * 100, 1),
                    "model_probability_percent": round(model_probability * 100, 1),
                    "similarity_percent": round(similarity_score * 100, 1),
                    "district_prior_percent": round(local_prior * 100, 1),
                }
            )

        return sorted(ranked, key=lambda item: (-item["probability_percent"], item["crop_name"]))

    def _score_crop_similarity(
        self,
        payload: dict[str, float | str],
        crop_profiles: list[dict[str, Any]],
    ) -> float:
        if not crop_profiles:
            return 0.0

        numeric_weights = {
            "temperature": 0.22,
            "humidity": 0.18,
            "moisture": 0.22,
            "nitrogen": 0.14,
            "phosphorus": 0.12,
            "potassium": 0.12,
        }

        best_score = 0.0
        for profile in crop_profiles:
            score = 0.0
            for feature, weight in numeric_weights.items():
                minimum, maximum = self.feature_ranges[feature]
                denominator = max(maximum - minimum, 1.0)
                difference = abs(float(payload[feature]) - float(profile[feature])) / denominator
                score += max(0.0, 1.0 - min(difference, 1.0)) * weight

            if str(profile.get("soil_type", "")).title() == str(payload["soil_type"]).title():
                score += 0.12

            best_score = max(best_score, min(score, 1.0))

        return best_score

    def _resolve_fertilizer(self, crop_name: str, soil_type: str) -> str:
        exact_match = next(
            (
                row["fertilizer_name"]
                for row in self.assets["fertilizer_lookup"]
                if row["crop_type"] == crop_name and row["soil_type"] == soil_type
            ),
            None,
        )
        if exact_match:
            return str(exact_match)

        crop_match = next(
            (
                row["fertilizer_name"]
                for row in self.assets["fertilizer_lookup"]
                if row["crop_type"] == crop_name
            ),
            None,
        )
        if crop_match:
            return str(crop_match)

        return "General NPK Blend"
