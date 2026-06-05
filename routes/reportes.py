from flask import Blueprint, jsonify, session
from models import db, Jugada, Transaccion, Usuario
from utils import requiere_rol
from sqlalchemy import func

reportes_bp = Blueprint('reportes_bp', __name__)

@reportes_bp.route('/api/admin/dashboard-financiero', methods=['GET'])
@requiere_rol('dueno', 'admin')
def obtener_metricas_banca():
    """Calcula el balance general de apuestas, premios otorgados y rentabilidad de la banca."""
    try:
        # Totales de Apuestas
        total_apuntado = db.session.query(func.sum(Jugada.monto)).scalar() or 0.0
        total_premios = db.session.query(func.sum(Jugada.monto_ganado)).scalar() or 0.0
        
        # Rendimiento Neto (Utilidad bruta de la banca)
        utilidad_neta = total_apuntado - total_premios
        
        # Conteo de tickets por estado
        tickets_pendientes = Jugada.query.filter_by(estado='pendiente').count()
        tickets_ganados = Jugada.query.filter_by(estado='ganada').count()
        tickets_perdidos = Jugada.query.filter_by(estado='perdida').count()
        
        # Resumen de fondos líquidos en manos de los jugadores
        total_saldos_usuarios = db.session.query(func.sum(Usuario.saldo)).scalar() or 0.0

        return jsonify({
            'ingresos_apuestas': total_apuntado,
            'egresos_premios': total_premios,
            'utilidad_neta': utilidad_neta,
            'total_saldos_custodia': total_saldos_usuarios,
            'conteo_tickets': {
                'pendientes': tickets_pendientes,
                'ganados': tickets_ganados,
                'perdidos': tickets_perdidos
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f"Error interno al compilar métricas: {str(e)}"}), 500

@reportes_bp.route('/api/admin/historial-tickets', methods=['GET'])
@requiere_rol('dueno', 'admin')
def listado_general_tickets():
    """Devuelve el universo completo de apuestas registradas en el sistema para control del Dueño."""
    try:
        tickets = Jugada.query.order_by(Jugada.fecha.desc()).all()
        
        resultado = [{
            'id': t.id,
            'jugador_telefono': t.telefono,
            'loteria': t.loteria.nombre if t.loteria else 'Desconocida',
            'modalidad': t.modalidad.upper(),
            'numero': f"{t.numero_principal} - {t.numero_parle}" if t.numero_parle else t.numero_principal,
            'monto': t.monto,
            'monto_ganado': t.monto_ganado,
            'estado': t.estado.upper(),
            'fecha': t.fecha.isoformat()
        } for t in tickets]
        
        return jsonify({'tickets': resultado}), 200
    except Exception as e:
        return jsonify({'error': f"Error al extraer historial: {str(e)}"}), 500