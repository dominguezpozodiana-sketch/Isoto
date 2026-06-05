import os
from flask import Flask, send_from_directory
from config import Config
from models import db

# Importación de la totalidad de los Blueprints del Sistema
from routes.auth import auth_bp
from routes.jugadas import jugadas_bp
from routes.loterias import loterias_bp
from routes.resultados import resultados_bp
from routes.admin import admin_bp
from routes.banca import banca_bp
from routes.reportes import reportes_bp

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config.from_object(Config)

# Inicializar Base de Datos con el contexto relacional
db.init_app(app)

# Registro centralizado de Blueprints autorizados
app.register_blueprint(auth_bp)
app.register_blueprint(jugadas_bp)
app.register_blueprint(loterias_bp)
app.register_blueprint(resultados_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(banca_bp)
app.register_blueprint(reportes_bp)

# Enrutamiento SPA catch-all para servir la página única index.html
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def servir_spa(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    with app.app_context():
        # Generar las tablas relacionales de forma automática si no existen en el motor
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)