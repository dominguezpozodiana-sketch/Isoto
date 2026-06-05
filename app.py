from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import os
import uuid
from datetime import datetime

app = Flask(__name__, static_folder='.')
app.secret_key = 'cambia-esta-clave-por-una-segura'
CORS(app)  # Permitir peticiones desde el mismo origen

# -------------------- DATOS EN MEMORIA (demo) --------------------
# En un caso real usarías una base de datos (SQLite, PostgreSQL, etc.)

usuarios = {
    "52345678": {
        "telefono": "52345678",
        "password": "1234",
        "nombre": "Juan Pérez",
        "rol": "usuario"   # puede ser "usuario" o "admin"
    },
    "51234567": {
        "telefono": "51234567",
        "password": "admin",
        "nombre": "Administrador",
        "rol": "admin"
    }
}

jugadas = []  # lista de diccionarios

# -------------------- RUTAS DE LA API --------------------

@app.route('/')
def index():
    """Sirve el archivo HTML principal"""
    return send_from_directory('.', 'index.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    telefono = str(data.get('telefono', '')).strip()
    password = data.get('password', '')

    user = usuarios.get(telefono)
    if not user or user['password'] != password:
        return jsonify({"error": "Teléfono o contraseña incorrectos"}), 401

    # Guardar sesión (opcional)
    session['user'] = user

    # Determinar qué vistas (pestañas) puede ver
    vistas = ['inicio']
    if user['rol'] == 'usuario':
        vistas.append('jugar')
    elif user['rol'] == 'admin':
        vistas.append('jugar')
        vistas.append('admin_usuarios')
        vistas.append('admin_control')

    return jsonify({
        "usuario": {
            "telefono": user['telefono'],
            "nombre": user['nombre'],
            "rol": user['rol']
        },
        "vistas": vistas
    })

@app.route('/api/jugada', methods=['POST'])
def api_jugada():
    if 'user' not in session:
        return jsonify({"exito": False, "mensaje": "No has iniciado sesión"}), 401
    
    data = request.get_json()
    numero = data.get('numero')
    monto = data.get('monto')
    telefono = session['user']['telefono']

    # Validaciones simples
    if not numero or not monto:
        return jsonify({"exito": False, "mensaje": "Faltan datos"}), 400
    try:
        numero = int(numero)
        monto = float(monto)
        if numero < 0 or numero > 99 or monto <= 0:
            raise ValueError
    except:
        return jsonify({"exito": False, "mensaje": "Número (00-99) y monto positivo requeridos"}), 400

    nueva_jugada = {
        "id": str(uuid.uuid4())[:8],
        "telefono": telefono,
        "numero": numero,
        "monto": monto,
        "fecha": datetime.now().isoformat(),
        "estado": "pendiente"
    }
    jugadas.append(nueva_jugada)

    return jsonify({"exito": True, "id": nueva_jugada['id']})

@app.route('/api/usuarios', methods=['GET'])
def api_usuarios():
    if 'user' not in session or session['user']['rol'] != 'admin':
        return jsonify({"error": "No autorizado"}), 403

    # Devolver lista de usuarios (sin las contraseñas)
    lista = []
    for tel, datos in usuarios.items():
        lista.append({
            "telefono": tel,
            "nombre": datos['nombre'],
            "rol": datos['rol']
        })
    return jsonify(lista)

# -------------------- INICIAR EL SERVIDOR --------------------
if __name__ == '__main__':
    # Escucha en todas las interfaces para que Codespaces pueda redirigir
    app.run(host='0.0.0.0', port=8000, debug=True)