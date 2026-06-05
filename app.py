import os
from flask import Flask, send_from_directory
from flask.json.provider import DefaultJSONProvider
from decimal import Decimal
from config import Config
from models import db

class CustomJSONProvider(DefaultJSONProvider):
    """Manejador personalizado para evitar que Flask rompa al procesar dinero en formato Decimal."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config.from_object(Config)

# Asignar el serializador seguro de decimales
app.json = CustomJSONProvider(app)

# Inicializar persistencia relacional
db.init_app(app)

# Registro de Blueprints del Sistema
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

# Asegurar la creación de tablas de forma asíncrona al primer toque de red, no al congelar el inicio
@app.before_request
def inicializar_tablas_produccion():
    # Eliminar el hook después de ejecutarse la primera vez para no saturar
    app.before_request_funcs[None].remove(inicializar_tablas_produccion)
    try:
        db.create_all()
    except Exception as e:
        app.logger.error(f"Error crítico al conectar o crear la Base de Datos: {str(e)}")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def servir_spa(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Este bloque solo corre localmente en tu PC (python app.py)
    puerto = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=puerto, debug=False)
