from flask import Flask
from flask_cors import CORS

from .config import Config
from .routes import api_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/")
    def index():
        return {
            "status": "ok",
            "service": "crop-yield-prediction-system",
            "message": "Backend is running. Use /api/health or /api/metadata.",
        }

    return app
