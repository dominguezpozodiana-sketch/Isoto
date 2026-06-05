from functools import wraps
from flask import session, jsonify

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
# CONFIGURACIÓN DE REGLAS DE JUEGO (BANCA)
# ==========================================

# Multiplicadores de ganancia oficiales
CUOTAS_DEFECTO = {
    'fijo': 80.0,       # Paga 80 veces el monto apostado
    'corrido': 25.0,    # Paga 25 veces el monto apostado
    'parle': 1000.0     # Paga 1000 veces el monto apostado si se aciertan ambos
}

# Límites máximos de dinero permitidos por jugada individual para proteger la caja
LIMITES_APUESTA = {
    'fijo': 50.0,       # Máximo $50 por número en Fijo
    'corrido': 100.0,   # Máximo $100 por número en Corrido
    'parle': 10.0       # Máximo $10 por combinación en Parlé
}

def validar_formato_jugada(modalidad, num1, num2=None):
    """
    Verifica que los números ingresados correspondan estrictamente a las reglas.
    Fijo/Corrido: Deben ser exactamente 2 dígitos (00-99).
    Parlé: Deben ser dos combinaciones válidas de 2 dígitos cada una.
    """
    if modalidad in ['fijo', 'corrido']:
        if not num1 or not num1.isdigit() or len(num1) != 2:
            return False, "Para Fijo o Corrido, debe ingresar un número de exactamente 2 dígitos (00 a 99)."
        return True, None

    elif modalidad == 'parle':
        if not num1 or not num1.isdigit() or len(num1) != 2:
            return False, "El primer número del Parlé debe tener exactamente 2 dígitos."
        if not num2 or not num2.isdigit() or len(num2) != 2:
            return False, "El segundo número del Parlé debe tener exactamente 2 dígitos."
        if num1 == num2:
            return False, "Un Parlé requiere dos números diferentes."
        return True, None

    return False, "Modalidad de juego no soportada por la plataforma."

def verificar_limite_banca(modalidad, monto):
    """Valida si la jugada respeta los topes financieros fijados para mitigar riesgos."""
    limite = LIMITES_APUESTA.get(modalidad, 0.0)
    if monto > limite:
        return False, f"La apuesta excede el límite máximo permitido para {modalidad.upper()}. El tope es de ${limite:.2f}."
    return True, None