from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def clean_soil_dataset(frame: pd.DataFrame) -> pd.DataFrame:
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
    for column in ["temperature", "humidity", "moisture", "nitrogen", "phosphorus", "potassium"]:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    cleaned = cleaned.dropna(subset=["crop_type", "soil_type"])
    cleaned = cleaned.fillna(cleaned.median(numeric_only=True))
    return cleaned


def main() -> None:
    soil_path = DATA_DIR / "soil_recommendation_core.csv"
    yield_path = DATA_DIR / "processed_training_data.csv"
    if not soil_path.exists() or not yield_path.exists():
        raise FileNotFoundError("Required datasets are missing.")

    soil_df = clean_soil_dataset(pd.read_csv(soil_path))
    yield_df = pd.read_csv(yield_path)

    latest_profiles = (
        yield_df.sort_values("year")
        .groupby(["state_name", "district_name", "crop_name"], as_index=False)
        .tail(1)
    )
    dominant_crop = (
        latest_profiles.sort_values("production_tons", ascending=False)
        .groupby(["state_name", "district_name"], as_index=False)
        .head(1)
        .reset_index(drop=True)
    )

    crop_soil_profiles = (
        soil_df.groupby("crop_type", as_index=False)
        .agg(
            soil_type=("soil_type", lambda series: series.mode().iat[0] if not series.mode().empty else series.iloc[0]),
            moisture=("moisture", "median"),
            nitrogen=("nitrogen", "median"),
            phosphorus=("phosphorus", "median"),
            potassium=("potassium", "median"),
        )
    )

    merged = dominant_crop.merge(
        crop_soil_profiles,
        left_on="crop_name",
        right_on="crop_type",
        how="left",
    )

    fallback = {
        "soil_type": "Loamy",
        "moisture": float(soil_df["moisture"].median()),
        "nitrogen": float(soil_df["nitrogen"].median()),
        "phosphorus": float(soil_df["phosphorus"].median()),
        "potassium": float(soil_df["potassium"].median()),
    }

    district_soil_map: dict[str, dict[str, object]] = {}
    for _, row in merged.iterrows():
        key = f"{row['state_name']}::{row['district_name']}"
        district_soil_map[key] = {
            "state_name": row["state_name"],
            "district_name": row["district_name"],
            "dominant_crop_reference": row["crop_name"],
            "soil_type": row["soil_type"] if pd.notna(row["soil_type"]) else fallback["soil_type"],
            "nitrogen": round(float(row["nitrogen"]) if pd.notna(row["nitrogen"]) else fallback["nitrogen"], 2),
            "phosphorus": round(float(row["phosphorus"]) if pd.notna(row["phosphorus"]) else fallback["phosphorus"], 2),
            "potassium": round(float(row["potassium"]) if pd.notna(row["potassium"]) else fallback["potassium"], 2),
            "moisture": round(float(row["moisture"]) if pd.notna(row["moisture"]) else fallback["moisture"], 2),
            "mapping_source": "dominant_crop_profile",
        }

    (DATA_DIR / "district_soil_map.json").write_text(
        json.dumps(district_soil_map, indent=2),
        encoding="utf-8",
    )
    print(f"District soil map saved with {len(district_soil_map)} entries.")


if __name__ == "__main__":
    main()
