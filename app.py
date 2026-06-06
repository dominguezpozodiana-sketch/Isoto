import os
from decimal import Decimal

from flask import Flask, send_from_directory
from flask.json.provider import DefaultJSONProvider

from config import Config
from models import db


class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static"
)

app.config.from_object(Config)

app.json = CustomJSONProvider(app)

db.init_app(app)

with app.app_context():
    db.create_all()


from routes.auth import auth_bp
from routes.jugadas import jugadas_bp
from routes.loterias import loterias_bp
from routes.resultados import resultados_bp
from routes.admin import admin_bp
from routes.banca import banca_bp
from routes.reportes import reportes_bp

app.register_blueprint(auth_bp)
app.register_blueprint(jugadas_bp)
app.register_blueprint(loterias_bp)
app.register_blueprint(resultados_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(banca_bp)
app.register_blueprint(reportes_bp)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def servir_spa(path):
    if path != "" and os.path.exists(
        os.path.join(app.static_folder, path)
    ):
        return send_from_directory(
            app.static_folder,
            path
        )

    return send_from_directory(
        app.static_folder,
        "index.html"
    )


if __name__ == "__main__":
    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
