import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from models import db, Usuario, SolicitudRegistro
from utils import hash_password, check_password, generar_codigo_otp, generar_url_whatsapp

auth_bp = Blueprint('auth_bp', __name__)

def validar_telefono_formato(telefono):
    return bool(re.match(r"^\d{8,15}$", telefono))

def validar_password_fuerza(password):
    """Exige un estándar alto: mínimo 8 caracteres, mínimo 1 letra y 1 número (Punto 5)."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True

@auth_bp.route('/api/auth/solicitar-registro', methods=['POST'])
def solicitar_registro():
    data = request.get_json() or {}
    telefono = str(data.get('telefono', '')).strip()
    password = str(data.get('password', ''))

    if not telefono or not password:
        return jsonify({'error': 'Todos los campos son obligatorios.'}), 400

    if not validar_telefono_formato(telefono):
        return jsonify({'error': 'Número de teléfono inválido. Use solo números (8 a 15 dígitos).'}), 400

    if not validar_password_fuerza(password):
        return jsonify({'error': 'La contraseña debe tener mínimo 8 caracteres, incluyendo letras y números.'}), 400

    error_generico = 'El número ingresado no está disponible para registro actualmente.'
    if Usuario.query.get(telefono) or SolicitudRegistro.query.filter_by(telefono_whatsapp=telefono, estado='pendiente').first():
        return jsonify({'error': error_generico}), 400

    otp = generar_codigo_otp()
    hash_p = hash_password(password)
    
    # Define ventana de expiración del código a 10 minutos (Punto 4)
    limite_temporal = datetime.utcnow() + timedelta(minutes=10)

    nueva_solicitud = SolicitudRegistro(
        telefono_whatsapp=telefono,
        password_hash=hash_p,
        codigo_otp=otp,
        intentos_otp=0,
        fecha_expiracion=limite_temporal,
        estado='pendiente'
    )

    try:
        db.session.add(nueva_solicitud)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Error de procesamiento interno.'}), 500

    mensaje = f"Hola, mi código de verificación para la plataforma de Lotería es: {otp}"
    url_wa = generar_url_whatsapp(nueva_solicitud.telefono_whatsapp, mensaje)

    return jsonify({
        'msg': 'Solicitud registrada de forma correcta.',
        'url_whatsapp': url_wa
    }), 200


@auth_bp.route('/api/auth/verificar-otp', methods=['POST'])
def verificar_otp():
    data = request.get_json() or {}
    telefono = str(data.get('telefono', '')).strip()
    codigo = str(data.get('codigo', '')).strip()

    solicitud = SolicitudRegistro.query.filter_by(telefono_whatsapp=telefono, estado='pendiente').first()
    if not solicitud:
        return jsonify({'error': 'No se localizan solicitudes pendientes para este número.'}), 404

    # Validación 1: Expiración por reloj (Punto 4)
    if datetime.utcnow() > solicitud.fecha_expiracion:
        solicitud.estado = 'rechazado'
        db.session.commit()
        return jsonify({'error': 'El código OTP ha expirado debido al límite de tiempo (10 min). Genere uno nuevo.'}), 400

    # Validación 2: Fuerza bruta
    if solicitud.intentos_otp >= 3:
        solicitud.estado = 'rechazado'
        db.session.commit()
        return jsonify({'error': 'Código bloqueado por exceso de intentos erróneos.'}), 400

    if solicitud.codigo_otp != codigo:
        solicitud.intentos_otp += 1
        db.session.commit()
        return jsonify({'error': f'Código incorrecto. Intentos restantes: {3 - solicitud.intentos_otp}'}), 400

    nuevo_usuario = Usuario(
        telefono=solicitud.telefono_whatsapp,
        password_hash=solicitud.password_hash,
        rol='usuario',
        saldo=0.00,
        activo=True
    )
    solicitud.estado = 'aprobado'
    db.session.add(nuevo_usuario)
    
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Error al asentar tu cuenta de usuario.'}), 500

    return jsonify({'msg': '¡Cuenta verificada y activada con éxito!'}), 200


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    telefono = str(data.get('telefono', '')).strip()
    password = str(data.get('password', ''))

    error_generico = "Credenciales incorrectas o cuenta no autorizada."
    usuario = Usuario.query.get(telefono)
    if not usuario or not usuario.activo:
        return jsonify({'error': error_generico}), 401

    if not check_password(usuario.password_hash, password):
        return jsonify({'error': error_generico}), 401

    session.clear()
    session['telefono'] = usuario.telefono
    session['rol'] = usuario.rol

    return jsonify({
        'msg': 'Autenticación exitosa',
        'usuario': {'telefono': usuario.telefono, 'rol': usuario.rol, 'saldo': float(usuario.saldo)}
    }), 200