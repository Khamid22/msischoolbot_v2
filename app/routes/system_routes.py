from flask import Blueprint, make_response


def register_system_routes(app):
    system_blueprint = Blueprint("system", __name__)

    @system_blueprint.get("/manifest.webmanifest")
    def manifest():
        response = make_response(app.send_static_file("manifest.webmanifest"))
        response.headers["Content-Type"] = "application/manifest+json"
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response

    @system_blueprint.get("/sw.js")
    def service_worker():
        response = make_response(app.send_static_file("js/sw.js"))
        response.headers["Content-Type"] = "application/javascript"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    app.register_blueprint(system_blueprint)
