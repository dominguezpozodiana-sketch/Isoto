from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import sqlite3
import uuid
import os
from datetime import datetime

app = Flask(__name__, static_folder='.')
app.secret_key = 'cambia-esta-clave-por-una-segura'
CORS(app)

# -------------------- INICIALIZAR BASE DE DATOS --------------------
DB_NAME = 'bolita.db'

def init_db():
    """Crea las tablas si no existen y carga usuarios por defecto"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tabla de usuarios
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            telefono TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    ''')
    
    # Tabla de jugadas
    c.execute('''
        CREATE TABLE IF NOT EXISTS jugadas (
            id TEXT PRIMARY KEY,
            telefono TEXT NOT NULL,
            numero INTEGER NOT NULL,
            monto REAL NOT NULL,
            fecha TEXT NOT NULL,
            estado TEXT NOT NULL,
            FOREIGN KEY (telefono) REFERENCES usuarios(telefono)
        )
    ''')
    
    # Insertar usuarios de ejemplo si la tabla está vacía
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        usuarios_ejemplo = [
            ('52345678', '1234', 'Juan Pérez', 'usuario'),
            ('51234567', 'admin', 'Administrador', 'admin')
        ]
        c.executemany("INSERT INTO usuarios (telefono, password, nombre, rol) VALUES (?, ?, ?, ?)", usuarios_ejemplo)
    
    conn.commit()
    conn.close()

# Llamar a la función al arrancar el servidor
init_db()

# -------------------- FUNCIONES AUXILIARES --------------------
def get_db():
    """Devuelve una conexión a la base de datos"""
    return sqlite3.connect(DB_NAME)

# -------------------- RUTAS DE LA API --------------------
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    telefono = str(data.get('telefono', '')).strip()
    password = data.get('password', '')

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT telefono, nombre, rol FROM usuarios WHERE telefono = ? AND password = ?", (telefono, password))
    user = c.fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "Teléfono o contraseña incorrectos"}), 401

    # Guardar sesión
    session['user'] = {
        'telefono': user[0],
        'nombre': user[1],
        'rol': user[2]
    }

    # Determinar vistas según rol
    vistas = ['inicio']
    if user[2] == 'usuario':
        vistas.append('jugar')
    elif user[2] == 'admin':
        vistas.append('jugar')
        vistas.append('admin_usuarios')
        vistas.append('admin_control')

    return jsonify({
        "usuario": {
            "telefono": user[0],
            "nombre": user[1],
            "rol": user[2]
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

    # Validaciones
    if not numero or not monto:
        return jsonify({"exito": False, "mensaje": "Faltan datos"}), 400
    try:
        numero = int(numero)
        monto = float(monto)
        if numero < 0 or numero > 99 or monto <= 0:
            raise ValueError
    except:
        return jsonify({"exito": False, "mensaje": "Número (00-99) y monto positivo requeridos"}), 400

    jugada_id = str(uuid.uuid4())[:8]
    fecha = datetime.now().isoformat()
    estado = 'pendiente'

    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO jugadas (id, telefono, numero, monto, fecha, estado) VALUES (?, ?, ?, ?, ?, ?)",
                  (jugada_id, telefono, numero, monto, fecha, estado))
        conn.commit()
        conn.close()
        return jsonify({"exito": True, "id": jugada_id})
    except Exception as e:
        conn.close()
        return jsonify({"exito": False, "mensaje": f"Error en BD: {str(e)}"}), 500

@app.route('/api/usuarios', methods=['GET'])
def api_usuarios():
    if 'user' not in session or session['user']['rol'] != 'admin':
        return jsonify({"error": "No autorizado"}), 403

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT telefono, nombre, rol FROM usuarios")
    rows = c.fetchall()
    conn.close()

    lista = [{"telefono": r[0], "nombre": r[1], "rol": r[2]} for r in rows]
    return jsonify(lista)

# -------------------- INICIAR SERVIDOR --------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)