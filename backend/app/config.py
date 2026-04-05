import os
from pathlib import Path
from dotenv import load_dotenv

# Absolute base directory (backend folder)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env
load_dotenv(BASE_DIR / ".env")


class Config:
    BASE_DIR = BASE_DIR

    # ✅ FIXED PATHS (IMPORTANT)
    DATA_DIR = BASE_DIR / "data"
    MODEL_DIR = BASE_DIR / "models"

    # Debug print (optional but helpful)
    print("MODEL_DIR:", MODEL_DIR)
    print("DATA_DIR:", DATA_DIR)

    OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")
    PORT = int(os.getenv("PORT", "5000"))

    _raw_cors_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    )
    CORS_ORIGINS = [origin.strip() for origin in _raw_cors_origins.split(",") if origin.strip()]