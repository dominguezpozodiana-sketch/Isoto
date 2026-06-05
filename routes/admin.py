from flask import Blueprint, jsonify, request
from models import db, Usuario
from utils import requiere_rol

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/api/admin/usuarios', methods=['GET'])
@requiere_rol('admin', 'dueno')
def obtener_usuarios():
    """Devuelve un listado rápido de jugadores bajo la jurisdicción del administrador."""
    usuarios = Usuario.query.filter_by(rol='usuario').all()
    resultado = [{
        'telefono': u.telefono,
        'nombre': u.nombre,
        'telefono_whatsapp': u.telefono_whatsapp,
        'estado': u.estado,
        'saldo': u.saldo
    } for u in usuarios]
    return jsonify({'usuarios': resultado}), 200

@admin_bp.route('/api/admin/usuarios/<string:tel>/cambiar-estado', methods=['POST'])
@requiere_rol('admin', 'dueno')
def cambiar_estado_usuario(tel):
    """Bloquea o desbloquea el acceso a la plataforma de un jugador de manera inmediata."""
    data = request.get_json() or {}
    nuevo_estado = data.get('estado') # Esperado: 'activo' o 'bloqueado'

    if nuevo_estado not in ['activo', 'bloqueado']:
        return jsonify({'error': 'Estado inválido'}), 400

    usuario = Usuario.query.get_or_404(tel)
    if usuario.rol == 'dueno' or (usuario.rol == 'admin' and session.get('rol') != 'dueno'):
        return jsonify({'error': 'Jerarquía insuficiente para modificar este usuario'}), 403

    usuario.estado = nuevo_estado
    db.session.commit()

    return jsonify({'msg': f'Usuario {usuario.nombre} cambiado a {nuevo_estado} con éxito.'}), 200