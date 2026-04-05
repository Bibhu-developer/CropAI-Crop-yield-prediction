from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from .services.crop_recommendation_service import CropRecommendationService
from .services.data_repository import DataRepository
from .services.district_soil_service import DistrictSoilService
from .services.model_service import ModelService
from .services.weather_service import WeatherService, WeatherServiceError
from .utils.file_store import read_json, write_json


api_bp = Blueprint("api", __name__)

repository = None
model_service = None
weather_service = None
district_soil_service = None
crop_recommendation_service = None


def get_services():
    global repository, model_service, weather_service, district_soil_service, crop_recommendation_service
    if repository is None:
        repository = DataRepository(current_app.config["DATA_DIR"])
        model_service = ModelService(
            current_app.config["MODEL_DIR"],
            current_app.config["DATA_DIR"],
            repository,
        )
        weather_service = WeatherService(current_app.config["OPENWEATHERMAP_API_KEY"])
        district_soil_service = DistrictSoilService(current_app.config["DATA_DIR"])
        crop_recommendation_service = CropRecommendationService(current_app.config["MODEL_DIR"])
    return repository, model_service, weather_service, district_soil_service, crop_recommendation_service


@api_bp.get("/health")
def health_check():
    return jsonify({"status": "ok", "service": "crop-yield-prediction-system"})


@api_bp.get("/metadata")
def metadata():
    return jsonify({
        "status": "working",
        "message": "API is running"
    })


@api_bp.get("/analytics")
def analytics():
    _, model_service_instance, _, _, _ = get_services()
    crop_name = request.args.get("crop")
    return jsonify(
        {
            "yearly_yield_trend": model_service_instance.get_yearly_yield_trend(crop_name),
            "feature_importance": model_service_instance.get_feature_importance(),
            "model_metrics": model_service_instance.metrics,
        }
    )


@api_bp.post("/predict")
def predict_yield():
    (
        repository_instance,
        model_service_instance,
        weather_service_instance,
        district_soil_service_instance,
        crop_recommendation_service_instance,
    ) = get_services()
    payload = request.get_json(force=True)

    required_fields = ["state_name", "district_name", "crop_name", "area_hectares"]
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    state_name = repository_instance.resolve_state(str(payload["state_name"]))
    if not state_name:
        return jsonify({"error": f"State '{payload['state_name']}' is not available in the dataset."}), 400

    district_name, used_fallback = repository_instance.resolve_district(
        state_name,
        str(payload["district_name"]),
    )
    if not district_name:
        return jsonify({"error": f"No districts are available for state '{state_name}'."}), 400

    crop_name = str(payload["crop_name"]).strip().title()
    if crop_name not in repository_instance.get_supported_crops():
        return jsonify({"error": f"Crop '{crop_name}' is not available in the trained dataset."}), 400

    district_profile = repository_instance.get_latest_district_crop_profile(
        state_name,
        district_name,
        crop_name,
    )
    if district_profile is None:
        return jsonify(
            {
                "error": f"Crop '{crop_name}' is not available for district '{district_name}'.",
                "available_crops": repository_instance.get_available_crops_for_district(state_name, district_name),
            }
        ), 400

    model_payload = {
        "state_name": state_name,
        "district_name": district_name,
        "crop_name": crop_name,
        "year": district_profile["year"] + 1,
        "period_group": infer_period_group(district_profile["year"] + 1),
        "area_hectares": float(payload["area_hectares"]),
        "lagged_yield_1y": district_profile["lagged_yield_1y"],
        "rolling_yield_3y": district_profile["rolling_yield_3y"],
        "yield_volatility_3y": district_profile["yield_volatility_3y"],
        "production_growth_rate": district_profile["production_growth_rate"],
        "area_growth_rate": district_profile["area_growth_rate"],
    }

    result = model_service_instance.predict(model_payload, context=district_profile)
    recommendations = model_service_instance.recommend_best_crop(model_payload)
    recommendation_module = build_crop_recommendation(
        repository_instance,
        state_name,
        district_name,
        weather_service_instance,
        district_soil_service_instance,
        crop_recommendation_service_instance,
    )

    history_path = current_app.config["DATA_DIR"] / "prediction_history.json"
    history = read_json(history_path)
    history.append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "state_name": state_name,
            "district_name": district_name,
            "crop_name": crop_name,
            "area_hectares": float(payload["area_hectares"]),
            "predicted_yield_kg_per_hectare": result.yield_kg_per_hectare,
            "total_yield_tons": result.total_yield_tons,
        }
    )
    write_json(history_path, history[-20:])

    return jsonify(
        {
            "inputs": {
                "state_name": state_name,
                "district_name": district_name,
                "crop_name": crop_name,
                "area_hectares": float(payload["area_hectares"]),
            },
            "historical_context": {
                "last_observed_year": district_profile["year"],
                "forecast_year": district_profile["year"] + 1,
                "last_recorded_yield_kg_per_ha": round(district_profile["last_recorded_yield_kg_per_ha"], 2),
                "rolling_yield_3y": round(district_profile["rolling_yield_3y"], 2),
                "production_growth_rate": round(district_profile["production_growth_rate"] * 100, 2),
                "area_growth_rate": round(district_profile["area_growth_rate"] * 100, 2),
                "district_fallback_used": used_fallback,
            },
            "prediction": {
                "yield_kg_per_hectare": result.yield_kg_per_hectare,
                "yield_tons_per_hectare": result.yield_tons_per_hectare,
                "total_yield_tons": result.total_yield_tons,
                "confidence_percent": result.confidence_percent,
            },
            "best_crop_suggestion": recommendations,
            "crop_recommendation": recommendation_module,
            "model_metrics": model_service_instance.metrics,
        }
    )


@api_bp.post("/recommend-crop")
def recommend_crop():
    (
        repository_instance,
        _,
        weather_service_instance,
        district_soil_service_instance,
        crop_recommendation_service_instance,
    ) = get_services()
    payload = request.get_json(force=True)

    required_fields = ["state_name", "district_name"]
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    state_name = repository_instance.resolve_state(str(payload["state_name"]))
    if not state_name:
        return jsonify({"error": f"State '{payload['state_name']}' is not available in the dataset."}), 400

    district_name, _ = repository_instance.resolve_district(state_name, str(payload["district_name"]))
    if not district_name:
        return jsonify({"error": f"No districts are available for state '{state_name}'."}), 400

    recommendation_module = build_crop_recommendation(
        repository_instance,
        state_name,
        district_name,
        weather_service_instance,
        district_soil_service_instance,
        crop_recommendation_service_instance,
    )
    return jsonify(recommendation_module)


def infer_period_group(year: int) -> str:
    if year <= 1987:
        return "1978-1987"
    if year <= 1997:
        return "1988-1997"
    if year <= 2007:
        return "1998-2007"
    return "2008-2017"


def build_crop_recommendation(
    repository_instance: DataRepository,
    state_name: str,
    district_name: str,
    weather_service_instance: WeatherService,
    district_soil_service_instance: DistrictSoilService,
    crop_recommendation_service_instance: CropRecommendationService,
) -> dict:
    location_query = f"{district_name}, {state_name}, India"
    try:
        weather = weather_service_instance.get_weather_by_location(location_query)
    except WeatherServiceError as exc:
        return {
            "status": "degraded",
            "error": str(exc),
            "source": "weather",
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "error": f"Weather lookup failed: {exc}",
            "source": "weather",
        }

    soil_profile = district_soil_service_instance.get_soil_profile(state_name, district_name)
    if soil_profile is None:
        return {
            "status": "degraded",
            "error": "District soil profile is not available.",
            "source": "soil",
        }

    candidate_crops = repository_instance.get_available_crops_for_district(state_name, district_name)
    candidate_priors = repository_instance.get_recommendation_crop_priors(state_name, district_name)
    recommendation = crop_recommendation_service_instance.recommend(
        weather,
        soil_profile,
        candidate_crops=candidate_crops,
        candidate_priors=candidate_priors,
    )
    return {
        "status": "ok",
        "recommended_crop": recommendation["recommended_crop"],
        "recommended_fertilizer": recommendation["recommended_fertilizer"],
        "top_crop_candidates": recommendation["top_crop_candidates"],
        "weather": {
            "temperature_c": round(float(weather["temperature_c"]), 1),
            "humidity_percent": round(float(weather["humidity_percent"]), 1),
            "resolved_name": weather["resolved_name"],
        },
        "soil": {
            "soil_type": soil_profile["soil_type"],
            "moisture": round(float(soil_profile["moisture"]), 1),
            "nitrogen": round(float(soil_profile["nitrogen"]), 1),
            "phosphorus": round(float(soil_profile["phosphorus"]), 1),
            "potassium": round(float(soil_profile["potassium"]), 1),
            "mapping_source": soil_profile.get("mapping_source", "district_soil_map"),
        },
        "fertilizer": recommendation["recommended_fertilizer"],
        "input_vector": recommendation["input_vector"],
    }
