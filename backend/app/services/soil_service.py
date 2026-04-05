from __future__ import annotations

from typing import Any

import requests

from .data_repository import DataRepository


class SoilService:
    def __init__(self, repository: DataRepository) -> None:
        self.repository = repository
        self.soilgrids_url = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    def get_soil_data(self, lat: float, lon: float, state_hint: str | None = None) -> dict[str, Any]:
        try:
            response = requests.get(
                self.soilgrids_url,
                params={
                    "lat": lat,
                    "lon": lon,
                    "property": ["phh2o", "nitrogen", "wv0033"],
                    "depth": ["0-5cm"],
                    "value": ["mean"],
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            layers = {item["name"]: item for item in payload.get("properties", {}).get("layers", [])}

            ph_value = self._extract_layer_value(layers.get("phh2o"))
            nitrogen_value = self._extract_layer_value(layers.get("nitrogen"))
            moisture_value = self._extract_layer_value(layers.get("wv0033"))

            if ph_value is not None and nitrogen_value is not None and moisture_value is not None:
                return {
                    "soil_ph": round(ph_value / 10, 2),
                    "nitrogen_kg_ha": round(nitrogen_value * 12, 2),
                    "moisture_percent": round(moisture_value / 10, 2),
                    "source": "soilgrids",
                }
        except requests.RequestException:
            pass

        if state_hint:
            local_profile = self.repository.get_soil_profile(state_hint)
            if local_profile:
                return local_profile

        raise ValueError("Unable to fetch soil data from SoilGrids or local profile.")

    @staticmethod
    def _extract_layer_value(layer: dict[str, Any] | None) -> float | None:
        if not layer:
            return None
        depths = layer.get("depths", [])
        if not depths:
            return None
        values = depths[0].get("values", {})
        return values.get("mean")

