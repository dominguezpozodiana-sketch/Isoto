import secrets
import urllib.parse
from functools import wraps
from flask import session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

def requiere_rol(*roles_permitidos):
    """Decorador para restringir el acceso a endpoints según el rol del usuario."""
    def decorador(f):
        @wraps(f)
        def funcion_decorada(*args, **kwargs):
            if 'telefono' not in session:
                return jsonify({'error': 'Sesión no iniciada. Autenticación requerida.'}), 401
            
            rol_usuario = session.get('rol')
            if rol_usuario not in roles_permitidos:
                return jsonify({'error': 'Acceso denegado. Permisos insuficientes.'}), 403
                
            return f(*args, **kwargs)
        return funcion_decorada
    return decorador

# ==========================================
# FUNCIONES DE SEGURIDAD Y CRIPTOGRAFÍA
# ==========================================

def hash_password(password):
    """Genera un hash seguro para contraseñas usando PBKDF2."""
    return generate_password_hash(password)

def check_password(password_hash, password):
    """Verifica si la contraseña coincide con el hash guardado."""
    return check_password_hash(password_hash, password)

def generar_codigo_otp():
    """Genera un código numérico de 6 dígitos altamente aleatorio y seguro."""
    return "".join(str(secrets.randbelow(10)) for _ in range(6))

def generar_url_whatsapp(telefono, mensaje):
    """Construye un enlace codificado válido para la API global de WhatsApp."""
    mensaje_url = urllib.parse.quote(mensaje)
    # Limpiar caracteres no numéricos del teléfono por si acaso
    telefono_limpio = "".join(c for c in str(telefono) if c.isdigit())
    return f"https://api.whatsapp.com/send?phone={telefono_limpio}&text={mensaje_url}"

# ==========================================
# REGLAS MATEMÁTICAS DE LA BANCA
# ==========================================

LIMITES_APUESTA = {
    'fijo': 50.00,
    'corrido': 100.00,
    'parle': 10.00
}

def validar_formato_jugada(modalidad, num1, num2=None):
    """Valida los formatos estrictos de números de la lotería cubana (00-99)."""
    if modalidad in ['fijo', 'corrido']:
        if not num1 or not num1.isdigit() or len(num1) != 2:
            return False, "Debe ingresar un número exacto de 2 dígitos (00 a 99)."
        return True, None

    elif modalidad == 'parle':
        if not num1 or not num1.isdigit() or len(num1) != 2:
            return False, "El primer número del Parlé debe tener 2 dígitos."
        if not num2 or not num2.isdigit() or len(num2) != 2:
            return False, "El segundo número del Parlé debe tener 2 dígitos."
        if num1 == num2:
            return False, "Un Parlé requiere dos números diferentes."
        return True, None

    return False, "Modalidad no soportada."

def verificar_limite_banca(modalidad, monto):
    """Compara el monto contra las reglas financieras máximas fijadas."""
    limite = LIMITES_APUESTA.get(modalidad, 0.00)
    if float(monto) > limite:
        return False, f"La apuesta excede el límite permitido para {modalidad.upper()} (${limite:.2f})."
    return True, None