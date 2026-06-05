import bcrypt
import random
import urllib.parse
from functools import wraps
from flask import session, jsonify

def hash_password(password: str) -> str:
    """Genera un hash seguro utilizando bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    """Verifica la contraseña contra el hash almacenado."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generar_codigo_otp() -> str:
    """Genera un código numérico de 6 dígitos."""
    return f"{random.randint(100000, 999999)}"

def generar_url_whatsapp(telefono: str, mensaje: str) -> str:
    """Construye una URL limpia de wa.me para envío sin costo de APIs."""
    # Limpiar caracteres no numéricos del teléfono
    tel_limpio = "".join(filter(str.isdigit, telefono))
    mensaje_enc = urllib.parse.quote(mensaje)
    return f"https://wa.me/{tel_limpio}?text={mensaje_enc}"

def requiere_rol(*roles):
    """Decorador personalizado para proteger rutas según el rol de la sesión."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'telefono' not in session:
                return jsonify({'error': 'No autorizado. Inicie sesión.'}), 410
            if session.get('rol') not in roles:
                return jsonify({'error': 'Acceso denegado. Permisos insuficientes.'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
