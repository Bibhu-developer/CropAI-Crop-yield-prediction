from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class DataRepository:
    RECOMMENDATION_CROP_ALIAS = {
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
        "castor seed": "Oil Seeds",
        "castor": "Oil Seeds",
        "oilseeds": "Oil Seeds",
        "oil seeds": "Oil Seeds",
        "rapeseed": "Oil Seeds",
        "rapeseed & mustard": "Oil Seeds",
        "rapeseed and mustard": "Oil Seeds",
        "mustard": "Oil Seeds",
        "sunflower": "Oil Seeds",
        "nigerseed": "Oil Seeds",
        "niger seed": "Oil Seeds",
        "pigeonpea": "Pulses",
        "minor pulses": "Pulses",
        "pulses": "Pulses",
        "gram": "Pulses",
        "moong": "Pulses",
        "urad": "Pulses",
        "peas & beans": "Pulses",
        "peas and beans": "Pulses",
        "jowar": "Millets",
        "bajra": "Millets",
        "ragi": "Millets",
        "millets": "Millets",
    }

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.training_data = pd.read_csv(data_dir / "processed_training_data.csv")
        self.training_data["state_name"] = self.training_data["state_name"].astype(str)
        self.training_data["district_name"] = self.training_data["district_name"].astype(str)
        self.training_data["crop_name"] = self.training_data["crop_name"].astype(str)
        self._district_frame = (
            self.training_data[["state_name", "district_name", "crop_name"]]
            .drop_duplicates()
            .sort_values(["state_name", "district_name", "crop_name"])
            .reset_index(drop=True)
        )
        self._crop_statistics = (
            self.training_data.groupby("crop_name")
            .agg(
                median_yield_kg_per_hectare=("yield_kg_per_hectare", "median"),
                median_area_hectares=("area_hectares", "median"),
            )
            .reset_index()
        )
        self._crops_by_district = (
            self._district_frame.groupby(["state_name", "district_name"])["crop_name"]
            .apply(list)
            .to_dict()
        )

    def get_state_list(self) -> list[str]:
        return sorted(self.training_data["state_name"].dropna().unique().tolist())

    def get_supported_crops(self) -> list[str]:
        return sorted(self.training_data["crop_name"].dropna().unique().tolist())

    def get_districts_by_state(self) -> dict[str, list[str]]:
        mapping = (
            self._district_frame[["state_name", "district_name"]]
            .drop_duplicates()
            .sort_values(["state_name", "district_name"])
            .groupby("state_name")["district_name"]
            .apply(list)
        )
        return mapping.to_dict()

    def get_crops_by_district(self) -> dict[str, list[str]]:
        return {
            f"{state_name}::{district_name}": sorted(set(crops))
            for (state_name, district_name), crops in self._crops_by_district.items()
        }

    def resolve_state(self, state_name: str) -> str | None:
        state_lookup = {state.lower(): state for state in self.get_state_list()}
        return state_lookup.get(state_name.strip().lower())

    def resolve_district(self, state_name: str, district_name: str) -> tuple[str | None, bool]:
        districts = self.get_districts_by_state().get(state_name, [])
        if not districts:
            return None, False

        district_lookup = {district.lower(): district for district in districts}
        direct_match = district_lookup.get(district_name.strip().lower())
        if direct_match:
            return direct_match, False

        lowered_input = district_name.strip().lower()
        partial_match = next((district for district in districts if lowered_input in district.lower()), None)
        if partial_match:
            return partial_match, True

        return districts[0], True

    def get_latest_district_crop_profile(
        self,
        state_name: str,
        district_name: str,
        crop_name: str,
    ) -> dict[str, Any] | None:
        frame = self.training_data[
            (self.training_data["state_name"].str.lower() == state_name.lower())
            & (self.training_data["district_name"].str.lower() == district_name.lower())
            & (self.training_data["crop_name"].str.lower() == crop_name.lower())
        ].sort_values("year")
        if frame.empty:
            return None

        row = frame.iloc[-1]
        return {
            "district_code": int(row["district_code"]),
            "state_code": int(row["state_code"]),
            "state_name": row["state_name"],
            "district_name": row["district_name"],
            "crop_name": row["crop_name"],
            "year": int(row["year"]),
            "period_group": row["period_group"],
            "lagged_yield_1y": float(row["lagged_yield_1y"]),
            "rolling_yield_3y": float(row["rolling_yield_3y"]),
            "yield_volatility_3y": float(row["yield_volatility_3y"]),
            "production_growth_rate": float(row["production_growth_rate"]),
            "area_growth_rate": float(row["area_growth_rate"]),
            "last_recorded_yield_kg_per_ha": float(row["yield_kg_per_hectare"]),
            "last_recorded_area_hectares": float(row["area_hectares"]),
            "last_recorded_production_tons": float(row["production_tons"]),
        }

    def get_district_crop_profile_for_year(
        self,
        state_name: str,
        district_name: str,
        crop_name: str,
        target_year: int,
    ) -> dict[str, Any] | None:
        frame = self.training_data[
            (self.training_data["state_name"].str.lower() == state_name.lower())
            & (self.training_data["district_name"].str.lower() == district_name.lower())
            & (self.training_data["crop_name"].str.lower() == crop_name.lower())
            & (self.training_data["year"] <= target_year)
        ].sort_values("year")
        if frame.empty:
            return None

        row = frame.iloc[-1]
        return {
            "district_code": int(row["district_code"]),
            "state_code": int(row["state_code"]),
            "state_name": row["state_name"],
            "district_name": row["district_name"],
            "crop_name": row["crop_name"],
            "year": int(row["year"]),
            "period_group": row["period_group"],
            "lagged_yield_1y": float(row["lagged_yield_1y"]),
            "rolling_yield_3y": float(row["rolling_yield_3y"]),
            "yield_volatility_3y": float(row["yield_volatility_3y"]),
            "production_growth_rate": float(row["production_growth_rate"]),
            "area_growth_rate": float(row["area_growth_rate"]),
            "last_recorded_yield_kg_per_ha": float(row["yield_kg_per_hectare"]),
            "last_recorded_area_hectares": float(row["area_hectares"]),
            "last_recorded_production_tons": float(row["production_tons"]),
        }

    def get_available_crops_for_district(self, state_name: str, district_name: str) -> list[str]:
        return self.get_crops_by_district().get(f"{state_name}::{district_name}", [])

    def get_crop_statistics(self, crop_name: str) -> dict[str, Any] | None:
        frame = self._crop_statistics[self._crop_statistics["crop_name"].str.lower() == crop_name.lower()]
        if frame.empty:
            return None
        row = frame.iloc[0]
        return {
            "median_yield_kg_per_hectare": float(row["median_yield_kg_per_hectare"]),
            "median_area_hectares": float(row["median_area_hectares"]),
        }

    def get_recommendation_crop_priors(self, state_name: str, district_name: str) -> dict[str, float]:
        frame = self.training_data[
            (self.training_data["state_name"].str.lower() == state_name.lower())
            & (self.training_data["district_name"].str.lower() == district_name.lower())
        ].copy()
        if frame.empty:
            return {}

        recent_year = int(frame["year"].max())
        frame = frame[frame["year"] >= recent_year - 7].copy()
        frame["recommendation_group"] = frame["crop_name"].str.lower().map(self.RECOMMENDATION_CROP_ALIAS)
        frame = frame.dropna(subset=["recommendation_group"])
        if frame.empty:
            return {}

        grouped = (
            frame.groupby("recommendation_group")
            .agg(
                production_tons=("production_tons", "sum"),
                yield_kg_per_hectare=("yield_kg_per_hectare", "median"),
                records=("crop_name", "count"),
            )
            .reset_index()
        )

        max_production = max(float(grouped["production_tons"].max()), 1.0)
        max_yield = max(float(grouped["yield_kg_per_hectare"].max()), 1.0)
        max_records = max(int(grouped["records"].max()), 1)

        priors = {}
        for _, row in grouped.iterrows():
            production_score = float(row["production_tons"]) / max_production
            yield_score = float(row["yield_kg_per_hectare"]) / max_yield
            frequency_score = float(row["records"]) / max_records
            priors[str(row["recommendation_group"])] = round(
                (0.5 * production_score) + (0.3 * yield_score) + (0.2 * frequency_score),
                4,
            )

        return priors
