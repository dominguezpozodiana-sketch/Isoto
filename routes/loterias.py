from flask import Blueprint, request, jsonify, session
from datetime import datetime
from models import db, Loteria
from utils import requiere_rol

loterias_bp = Blueprint('loterias_bp', __name__)

@loterias_bp.route('/api/loterias', methods=['GET'])
def obtener_loterias():
    """Retorna el catálogo total de terminales de loterías registradas en el ecosistema."""
    try:
        lista = Loteria.query.all()
        resultado = [{
            'id': l.id,
            'nombre': l.nombre,
            'turno': l.turno,
            'hora_apertura': l.hora_apertura.strftime('%H:%M:%S'),
            'hora_cierre': l.hora_cierre.strftime('%H:%M:%S'),
            'activa': l.activa
        } for l in lista]
        
        return jsonify({'loterias': resultado}), 200
    except Exception as e:
        return jsonify({'error': f"Error al mapear sorteos: {str(e)}"}), 500


@loterias_bp.route('/api/admin/crear-loteria', methods=['POST'])
@requiere_rol('dueno')
def crear_nueva_loteria_banca():
    """Permite al Creador de la plataforma dar de alta nuevas terminales horarias."""
    data = request.get_json() or {}
    id_loteria = data.get('id')
    nombre = data.get('nombre')
    turno = data.get('turno') # 'dia', 'noche'
    apertura_str = data.get('hora_apertura') # Formato "HH:MM"
    cierre_str = data.get('hora_cierre')

    if not id_loteria or not nombre or not turno or not apertura_str or not cierre_str:
        return jsonify({'error': 'Todos los campos son mandatorios para el alta.'}), 400

    if Loteria.query.get(id_loteria):
        return jsonify({'error': 'El ID de la lotería provisto ya se encuentra en uso.'}), 400

    try:
        hora_apertura = datetime.strptime(apertura_str, '%H:%M').time()
        hora_cierre = datetime.strptime(cierre_str, '%H:%M').time()
    except ValueError:
        return jsonify({'error': 'Formato de hora inválido. Use la estructura de 24 horas (HH:MM).'}), 400

    nueva_loteria = Loteria(
        id=id_loteria.lower().strip(),
        nombre=nombre,
        turno=turno.lower().strip(),
        hora_apertura=hora_apertura,
        hora_cierre=hora_cierre,
        activa=True
    )

    try:
        db.session.add(nueva_loteria)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Error de persistencia relacional: {str(e)}"}), 500

    return jsonify({'msg': f"Sorteo '{nombre}' configurado e incorporado exitosamente."}), 201


@loterias_bp.route('/api/admin/modificar-estado-loteria', methods=['POST'])
@requiere_rol('admin', 'dueno')
def conmutar_operacion_loteria():
    """Bloquea o desbloquea sorteos de forma persistente en Base de Datos (Punto 21 corregido)."""
    data = request.get_json() or {}
    id_loteria = data.get('id')
    estatus_activo = data.get('activa')

    if not id_loteria or estatus_activo is None:
        return jsonify({'error': 'Faltan parámetros de identificación de sorteo.'}), 400

    loteria = Loteria.query.get(id_loteria)
    if not loteria:
        return jsonify({'error': 'La lotería solicitada no figura en los registros.'}), 404

    # Modificación guardada de forma persistente a nivel de base de datos
    loteria.activa = bool(estatus_activo)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Fallo al asentar la modificación operativa: {str(e)}"}), 500

    estado_txt = "Abierta / Activa" if loteria.activa else "Pausada / Cerrada"
    return jsonify({'msg': f"La lotería '{loteria.nombre}' se encuentra ahora en estado: {estado_txt}."}), 200