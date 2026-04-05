from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATASET_PATH = DATA_DIR / "icrisat_district_crop_data.csv"
PROCESSED_PATH = DATA_DIR / "processed_training_data.csv"

IDENTIFIER_COLUMNS = ["Dist Code", "Year", "State Code", "State Name", "Dist Name"]


def clean_label(value: str) -> str:
    return " ".join(value.strip().title().split())


def metric_crop_map(columns: list[str], suffix: str) -> dict[str, str]:
    pattern = re.compile(rf"^(.*) {re.escape(suffix)}$")
    mapping: dict[str, str] = {}
    for column in columns:
        match = pattern.match(column)
        if match:
            mapping[column] = clean_label(match.group(1))
    return mapping


def melt_metric(frame: pd.DataFrame, mapping: dict[str, str], value_name: str) -> pd.DataFrame:
    melted = frame.melt(
        id_vars=IDENTIFIER_COLUMNS,
        value_vars=list(mapping.keys()),
        var_name="metric_column",
        value_name=value_name,
    )
    melted["crop_name"] = melted["metric_column"].map(mapping)
    return melted.drop(columns=["metric_column"])


def engineer_temporal_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_values(["state_name", "district_name", "crop_name", "year"]).reset_index(drop=True)
    group_keys = ["state_name", "district_name", "crop_name"]
    grouped = frame.groupby(group_keys, group_keys=False)

    # Use previous-year information only, so the training row does not see its own target.
    frame["lagged_yield_1y"] = grouped["yield_kg_per_hectare"].shift(1)
    frame["rolling_yield_3y"] = grouped["yield_kg_per_hectare"].transform(
        lambda series: series.shift(1).rolling(3, min_periods=1).mean()
    )
    frame["yield_volatility_3y"] = grouped["yield_kg_per_hectare"].transform(
        lambda series: series.shift(1).rolling(3, min_periods=2).std()
    )
    frame["production_growth_rate"] = grouped["production_tons"].pct_change()
    frame["area_growth_rate"] = grouped["area_hectares"].pct_change()

    crop_defaults = frame.groupby("crop_name")["yield_kg_per_hectare"].median()
    frame["lagged_yield_1y"] = frame["lagged_yield_1y"].fillna(frame["crop_name"].map(crop_defaults))
    frame["rolling_yield_3y"] = frame["rolling_yield_3y"].fillna(frame["crop_name"].map(crop_defaults))
    frame["yield_volatility_3y"] = frame["yield_volatility_3y"].fillna(0.0)
    frame["production_growth_rate"] = frame["production_growth_rate"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    frame["area_growth_rate"] = frame["area_growth_rate"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    frame["period_group"] = pd.cut(
        frame["year"],
        bins=[1977, 1987, 1997, 2007, 2017],
        labels=["1978-1987", "1988-1997", "1998-2007", "2008-2017"],
    ).astype(str)
    return frame


def main() -> None:
    # Step 1: Load dataset.
    raw_df = pd.read_csv(RAW_DATASET_PATH)

    # Step 2: Reshape dataset from wide crop columns to a district-year-crop table.
    area_mapping = metric_crop_map(raw_df.columns.tolist(), "AREA (1000 ha)")
    production_mapping = metric_crop_map(raw_df.columns.tolist(), "PRODUCTION (1000 tons)")
    yield_mapping = metric_crop_map(raw_df.columns.tolist(), "YIELD (Kg per ha)")
    crop_names = sorted(set(area_mapping.values()) & set(production_mapping.values()) & set(yield_mapping.values()))

    area_long = melt_metric(
        raw_df,
        {column: crop for column, crop in area_mapping.items() if crop in crop_names},
        "area_1000ha",
    )
    production_long = melt_metric(
        raw_df,
        {column: crop for column, crop in production_mapping.items() if crop in crop_names},
        "production_1000tons",
    )
    yield_long = melt_metric(
        raw_df,
        {column: crop for column, crop in yield_mapping.items() if crop in crop_names},
        "yield_kg_per_hectare",
    )

    merged = (
        area_long.merge(production_long, on=IDENTIFIER_COLUMNS + ["crop_name"], how="left")
        .merge(yield_long, on=IDENTIFIER_COLUMNS + ["crop_name"], how="left")
        .rename(
            columns={
                "Dist Code": "district_code",
                "State Code": "state_code",
                "State Name": "state_name",
                "Dist Name": "district_name",
                "Year": "year",
            }
        )
    )

    # Step 3: Clean and preprocess the reshaped table.
    merged["state_name"] = merged["state_name"].astype(str).map(clean_label)
    merged["district_name"] = merged["district_name"].astype(str).map(clean_label)
    merged["crop_name"] = merged["crop_name"].astype(str).map(clean_label)
    merged = merged.sort_values(["state_name", "district_name", "crop_name", "year"]).reset_index(drop=True)

    group_keys = ["state_name", "district_name", "crop_name"]
    for column in ["area_1000ha", "production_1000tons"]:
        merged[column] = merged.groupby(group_keys)[column].transform(
            lambda series: series.interpolate(limit_direction="both")
        )

    merged = merged.dropna(subset=["yield_kg_per_hectare"])
    merged = merged[(merged["yield_kg_per_hectare"] > 0) & (merged["area_1000ha"] > 0)]
    merged["area_hectares"] = (merged["area_1000ha"] * 1000).round(2)
    merged["production_tons"] = (merged["production_1000tons"] * 1000).round(2)
    merged["yield_tons_per_hectare"] = (merged["yield_kg_per_hectare"] / 1000).round(4)

    # Step 4: Feature engineering.
    processed = engineer_temporal_features(merged)
    processed = processed[
        [
            "district_code",
            "state_code",
            "state_name",
            "district_name",
            "year",
            "period_group",
            "crop_name",
            "area_hectares",
            "production_tons",
            "yield_kg_per_hectare",
            "yield_tons_per_hectare",
            "lagged_yield_1y",
            "rolling_yield_3y",
            "yield_volatility_3y",
            "production_growth_rate",
            "area_growth_rate",
        ]
    ]

    processed.to_csv(PROCESSED_PATH, index=False)
    print(f"Processed dataset saved to {PROCESSED_PATH}")
    print(
        {
            "rows": int(len(processed)),
            "states": int(processed["state_name"].nunique()),
            "districts": int(processed["district_name"].nunique()),
            "crops": int(processed["crop_name"].nunique()),
        }
    )
    print(processed.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
