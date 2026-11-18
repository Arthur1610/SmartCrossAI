from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from .api import api
from .database import Events
from .engine import Engine


def create_app(data_dir=None):
    app = Flask(__name__)
    directory = Path(data_dir or Path(app.root_path).parent / "runtime").resolve()
    app.config.update(MAX_CONTENT_LENGTH=200 * 1024 * 1024,
                      TRUSTED_HOSTS=["127.0.0.1", "localhost"])
    app.extensions["smartcross"] = Engine(Events(directory / "events.sqlite3"), directory / "models")
    app.register_blueprint(api)

    @app.get("/")
    def dashboard():
        return render_template("index.html")

    @app.before_request
    def protect_local_api():
        if request.path.startswith("/api/") and request.method not in ("GET", "HEAD"):
            if request.headers.get("Sec-Fetch-Site") == "cross-site":
                return jsonify(error="Requisição de outra origem recusada."), 403
            origin = request.headers.get("Origin")
            if origin and origin != request.host_url.rstrip("/"):
                return jsonify(error="Requisição de outra origem recusada."), 403

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        descriptions = {400: "Requisição inválida.", 413: "O tamanho máximo do envio é 200 MiB.",
                        415: "Envie JSON ou formulário multipart conforme a rota."}
        return jsonify(error=descriptions.get(error.code, error.name)), error.code

    return app
