from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DistrictSoilService:
    def __init__(self, data_dir: Path) -> None:
        self.map_path = data_dir / "district_soil_map.json"
        self._soil_map: dict[str, dict[str, Any]] | None = None

    @property
    def soil_map(self) -> dict[str, dict[str, Any]]:
        if self._soil_map is None:
            if not self.map_path.exists():
                raise FileNotFoundError(
                    "district_soil_map.json not found. Run backend/scripts/generate_district_soil_map.py first."
                )
            self._soil_map = json.loads(self.map_path.read_text(encoding="utf-8"))
        return self._soil_map

    def get_soil_profile(self, state_name: str, district_name: str) -> dict[str, Any] | None:
        key = f"{state_name}::{district_name}"
        profile = self.soil_map.get(key)
        if profile:
            return profile

        candidates = [
            value
            for map_key, value in self.soil_map.items()
            if map_key.startswith(f"{state_name}::")
        ]
        if not candidates:
            return None

        return {
            **candidates[0],
            "mapping_source": "state_fallback",
        }

