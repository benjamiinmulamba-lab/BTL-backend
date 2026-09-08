import os
from flask import Flask, send_from_directory
from flask_cors import CORS

from routes.donations import donations_bp
from routes.payfast_webhook import payfast_webhook_bp
from routes.hours import hours_bp
from routes.certificates import certificates_bp

# When this repo is laid out as bltf-fullstack/{frontend,backend}, this lets
# one process serve the static frontend AND the API — handy for phone-only
# testing (Replit etc.) where running two separate servers is awkward.
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


def create_app():
    app = Flask(__name__)
    CORS(app)  # restrict origins in production, e.g. CORS(app, origins=["https://your-frontend.netlify.app"])

    app.register_blueprint(donations_bp)
    app.register_blueprint(payfast_webhook_bp)
    app.register_blueprint(hours_bp)
    app.register_blueprint(certificates_bp)

    if os.path.isdir(FRONTEND_DIR):
        @app.route("/")
        def serve_index():
            return send_from_directory(FRONTEND_DIR, "index.html")

        @app.route("/<path:path>")
        def serve_frontend(path):
            full_path = os.path.join(FRONTEND_DIR, path)
            if os.path.isfile(full_path):
                return send_from_directory(FRONTEND_DIR, path)
            # Not a static file — let Flask's normal 404 handling take over
            # (this route only ever matches paths that aren't already
            # claimed by the API blueprints above).
            return send_from_directory(FRONTEND_DIR, "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
