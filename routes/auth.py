from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import uuid
from models import db, Usuario, SolicitudRegistro
from utils import hash_password, check_password, generar_codigo_otp, generar_url_whatsapp

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/auth/solicitud-registro', methods=['POST'])
def solicitud_registro():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    whatsapp = data.get('telefono_whatsapp')
    password = data.get('password')
    
    if not nombre or not whatsapp or not password:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400
        
    # Verificar si ya existe el usuario o una solicitud activa
    if Usuario.query.filter_by(telefono_whatsapp=whatsapp).first():
        return jsonify({'error': 'El número de WhatsApp ya se encuentra registrado'}), 400
        
    solicitud_existente = SolicitudRegistro.query.filter_by(telefono_whatsapp=whatsapp, estado='pendiente').first()
    if solicitud_existente:
        return jsonify({'error': 'Ya posees una solicitud de registro bajo revisión'}), 400

    nueva_solicitud = SolicitudRegistro(
        nombre=nombre,
        telefono_whatsapp=whatsapp,
        # Guardamos temporalmente un hash para cuando se valide definitivamente la cuenta
        codigo=hash_password(password), 
        estado='pendiente'
    )
    db.session.add(nueva_solicitud)
    db.session.commit()
    
    return jsonify({'msg': 'Solicitud enviada con éxito. Espere aprobación de su administrador.'}), 201

@auth_bp.route('/api/auth/admin/aprobar-solicitud/<int:solicitud_id>', methods=['POST'])
def aprobar_solicitud(solicitud_id):
    """Acción del administrador: Genera el OTP y la URL precargada para WhatsApp"""
    solicitud = SolicitudRegistro.query.get_or_404(solicitud_id)
    if solicitud.estado != 'pendiente':
        return jsonify({'error': 'La solicitud ya fue procesada'}), 400
        
    otp = generar_codigo_otp()
    solicitud.codigo_expira = datetime.utcnow() + timedelta(minutes=30)
    # Reutilizamos el campo guardando la tupla de validación otp|hash_password para el paso definitivo
    solicitud.codigo = f"{otp}|{solicitud.codigo}" 
    solicitud.estado = 'aprobado'
    db.session.commit()
    
    mensaje = f"¡Hola {solicitud.nombre}! Tu solicitud ha sido aprobada. Tu código de activación es: {otp}. Expira en 30 minutos."
    url_wa = generar_url_whatsapp(solicitid.telefono_whatsapp, mensaje)
    
    return jsonify({'msg': 'Solicitud aprobada', 'whatsapp_url': url_wa}), 200

@auth_bp.route('/api/auth/verificar-codigo', methods=['POST'])
def verificar_codigo():
    data = request.get_json() or {}
    whatsapp = data.get('telefono_whatsapp')
    codigo_ingresado = data.get('codigo')
    
    if not whatsapp or not codigo_ingresado:
        return jsonify({'error': 'Datos incompletos'}), 400
        
    solicitud = SolicitudRegistro.query.filter_by(telefono_whatsapp=whatsapp, estado='aprobado').first()
    if not solicitud or not solicitud.codigo or '|' not in solicitud.codigo:
        return jsonify({'error': 'No se encontró una solicitud aprobada para este número'}), 400
        
    if datetime.utcnow() > solicitud.codigo_expira:
        return jsonify({'error': 'El código OTP ha expirado'}), 400
        
    otp_correcto, password_hash = solicitud.codigo.split('|', 1)
    
    if codigo_ingresado.strip() != otp_correcto.strip():
        return jsonify({'error': 'Código de verificación incorrecto'}), 400
        
    # Crear el usuario definitivo en el sistema
    nuevo_usuario = Usuario(
        telefono=whatsapp, # El teléfono identificador actúa directo con su WhatsApp
        telefono_whatsapp=whatsapp,
        password=password_hash,
        nombre=solicitud.nombre,
        rol='usuario',
        estado='activo'
    )
    db.session.delete(solicitud)
    db.session.add(nuevo_usuario)
    db.session.commit()
    
    return jsonify({'msg': 'Cuenta verificada con éxito. Ya puede iniciar sesión.'}), 200

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    telefono = data.get('telefono')
    password = data.get('password')
    
    usuario = Usuario.query.filter_by(telefono=telefono).first()
    if not usuario or not check_password(password, usuario.password):
        return jsonify({'error': 'Credenciales inválidas'}), 401
        
    if usuario.estado != 'activo':
        return jsonify({'error': f'Su cuenta está en estado: {usuario.estado}'}), 403
        
    usuario.ultimo_login = datetime.utcnow()
    db.session.commit()
    
    # Inyección de estado de sesión en Flask cookie cifrada
    session['telefono'] = usuario.telefono
    session['rol'] = usuario.rol
    session['nombre'] = usuario.nombre
    
    return jsonify({
        'msg': 'Login exitoso',
        'usuario': {'telefono': usuario.telefono, 'nombre': usuario.nombre, 'rol': usuario.rol}
    }), 200

@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'msg': 'Sesión cerrada correctamente'}), 200