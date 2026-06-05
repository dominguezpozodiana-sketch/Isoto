from flask import Blueprint, request, jsonify, session
from models import db, Usuario, SolicitudRegistro
from utils import requiere_rol

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/api/admin/jugadores', methods=['GET'])
@requiere_rol('admin', 'dueno')
def listar_jugadores_completo():
    """Devuelve la nómina total de usuarios registrados con balances financieros legibles."""
    try:
        usuarios = Usuario.query.order_by(Usuario.fecha_registro.desc()).all()
        
        resultado = [{
            'telefono': u.telefono,
            'rol': u.rol.upper(),
            'saldo': float(u.saldo), # Conversión segura de db.Numeric a float para JSON
            'activo': u.activo,
            'fecha_registro': u.fecha_registro.isoformat()
        } for u in usuarios]
        
        return jsonify({'jugadores': resultado}), 200
    except Exception as e:
        return jsonify({'error': f"Error interno al extraer el padrón de usuarios: {str(e)}"}), 500


@admin_bp.route('/api/admin/solicitudes', methods=['GET'])
@requiere_rol('admin', 'dueno')
def listar_solicitudes_pendientes():
    """Lista las peticiones de ingreso por WhatsApp pendientes de aprobación administrativa."""
    try:
        solicitudes = SolicitudRegistro.query.filter_by(estado='pendiente').order_by(SolicitudRegistro.fecha_solicitud.desc()).all()
        
        resultado = [{
            'id': s.id,
            'telefono_whatsapp': s.telefono_whatsapp,
            'fecha_solicitud': s.fecha_solicitud.isoformat()
        } for s in solicitudes]
        
        return jsonify({'solicitudes': resultado}), 200
    except Exception as e:
        return jsonify({'error': f"Fallo al recuperar solicitudes: {str(e)}"}), 500


@admin_bp.route('/api/admin/cambiar-estado-usuario', methods=['POST'])
@requiere_rol('admin', 'dueno')
def cambiar_estado_usuario():
    """Permite pausar o reactivar el acceso de un jugador al sistema de forma atómica."""
    data = request.get_json() or {}
    telefono = data.get('telefono')
    activo_status = data.get('activo')

    if not telefono or activo_status is None:
        return jsonify({'error': 'Parámetros insuficientes para ejecutar la acción.'}), 400

    usuario = Usuario.query.get(telefono)
    if not usuario:
        return jsonify({'error': 'El usuario especificado no existe.'}), 404

    # Restricción de seguridad: Un administrador no puede dar de baja al Dueño/Creador
    if usuario.rol == 'dueno' and session.get('rol') != 'dueno':
        return jsonify({'error': 'Acceso denegado. No tienes jerarquía para alterar al Creador.'}), 403

    usuario.activo = bool(activo_status)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Error al actualizar estado en base de datos: {str(e)}"}), 500

    return jsonify({'msg': f"Estado del usuario {telefono} actualizado correctamente."}), 200