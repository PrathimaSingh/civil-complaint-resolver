# src/my_project/web/app.py
from flask import Flask

def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)

    app.config.from_mapping(
        SECRET_KEY="civil_complaint_secret_key_2026",
        JSON_SORT_KEYS=False,
    )

    if config:
        app.config.update(config)

    from .routes import web_bp
    app.register_blueprint(web_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app