import re
from flask import Blueprint, request, jsonify, session
from models import db, Usuario, SolicitudRegistro
from utils import hash_password, check_password, generar_codigo_otp, generar_url_whatsapp

auth_bp = Blueprint('auth_bp', __name__)

def validar_telefono_formato(telefono):
    """Acepta únicamente cadenas puramente numéricas de entre 8 y 15 dígitos."""
    return bool(re.match(r"^\d{8,15}$", telefono))

def validar_password_fuerza(password):
    """Valida una longitud mínima de 6 caracteres para evitar claves triviales."""
    return len(password) >= 6

@auth_bp.route('/api/auth/solicitar-registro', methods=['POST'])
def solicitar_registro():
    data = request.get_json() or {}
    telefono = str(data.get('telefono', '')).strip()
    password = str(data.get('password', ''))

    # Validaciones estructurales de sanidad
    if not telefono or not password:
        return jsonify({'error': 'Todos los campos son obligatorios.'}), 400

    if not validar_telefono_formato(telefono):
        return jsonify({'error': 'Número de teléfono inválido. Use solo números (8 a 15 dígitos).'}), 400

    if not validar_password_fuerza(password):
        return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres.'}), 400

    # Mitigación de enumeración: Respuesta genérica unificada
    usuario_existe = Usuario.query.get(telefono)
    solicitud_existe = SolicitudRegistro.query.filter_by(telefono_whatsapp=telefono, estado='pendiente').first()
    
    if usuario_existe or solicitud_existe:
        return jsonify({'error': 'El número ingresado no está disponible para registro actualmente.'}), 400

    # Crear la solicitud
    otp = generar_codigo_otp()
    hash_p = hash_password(password)

    nueva_solicitud = SolicitudRegistro(
        telefono_whatsapp=telefono,
        password_hash=hash_p,
        codigo_otp=otp,
        intentos_otp=0,
        estado='pendiente'
    )

    try:
        db.session.add(nueva_solicitud)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error de procesamiento interno en el servidor.'}), 500

    # Generación de URL de WhatsApp (Punto 1 corregido)
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
    
    if not_solicitud := (not solicitud):
        return jsonify({'error': 'No se localizan solicitudes pendientes para este número.'}), 404

    # Control estricto de ataques por fuerza bruta al OTP (Máximo 3 intentos)
    if solicitud.intentos_otp >= 3:
        solicitud.estado = 'rechazado'
        db.session.commit()
        return jsonify({'error': 'Código bloqueado por exceso de intentos erróneos. Solicite uno nuevo.'}), 400

    if solicitud.codigo_otp != codigo:
        solicitud.intentos_otp += 1
        db.session.commit()
        return jsonify({'error': f'Código de verificación incorrecto. Intentos restantes: {3 - solicitud.intentos_otp}'}), 400

    # Crear el usuario final tras la validación exitosa
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

    return jsonify({'msg': '¡Cuenta verificada y activada con éxito! Ya puedes iniciar sesión.'}), 200


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    telefono = str(data.get('telefono', '')).strip()
    password = str(data.get('password', ''))

    # Respuesta unificada para evitar el descubrimiento de cuentas activas
    error_generico = "Credenciales incorrectas o cuenta no autorizada."

    usuario = Usuario.query.get(telefono)
    if not usuario or not usuario.activo:
        return jsonify({'error': error_generico}), 401

    if not check_password(usuario.password_hash, password):
        return jsonify({'error': error_generico}), 401

    # Defensa contra Session Fixation: Limpiar y recrear identificadores de sesión
    session.clear()
    session['telefono'] = usuario.telefono
    session['rol'] = usuario.rol

    return jsonify({
        'msg': 'Autenticación exitosa',
        'usuario': {'telefono': usuario.telefono, 'rol': usuario.rol, 'saldo': float(usuario.saldo)}
    }), 200


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'msg': 'Sesión cerrada de manera segura.'}), 200