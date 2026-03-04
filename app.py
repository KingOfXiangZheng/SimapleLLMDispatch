"""SimapleLLMDispatch — Python Edition."""

import os
from flask import Flask
from flask_cors import CORS

from config import PORT
from database import init_db
from routes.admin import admin_bp
from routes.proxy import proxy_bp


def create_app() -> Flask:
    app = Flask(__name__, static_folder="public/dist", static_url_path="")
    CORS(app)

    init_db()

    app.register_blueprint(admin_bp)
    app.register_blueprint(proxy_bp)

    # Serve dashboard at root
    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"SimapleLLMDispatch (Python) running at http://localhost:{PORT}")
    print(f"Dashboard: http://localhost:{PORT}/dashboard.html")
    app.run(host="0.0.0.0", port=PORT, debug=os.environ.get("DEBUG", "0") == "1")
