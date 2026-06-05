from flask import Blueprint, jsonify, session
from models import db, Jugada, Usuario
from utils import requiere_rol
from sqlalchemy import func

reportes_bp = Blueprint('reportes_bp', __name__)

@reportes_bp.route('/api/admin/dashboard-financiero', methods=['GET'])
@requiere_rol('dueno', 'admin')
def obtener_metricas_banca():
    """Calcula el balance general asegurando tipos nativos de serialización JSON (Punto 7)."""
    try:
        total_apuntado = db.session.query(func.sum(Jugada.monto)).scalar() or 0.00
        total_premios = db.session.query(func.sum(Jugada.monto_ganado)).scalar() or 0.00
        
        # Doble validación y casteo manual redundante (Punto 7 corregido)
        ingresos = float(total_apuntado)
        egresos = float(total_premios)
        utilidad_neta = ingresos - egresos
        
        tickets_pendientes = Jugada.query.filter_by(estado='pendiente').count()
        tickets_ganados = Jugada.query.filter_by(estado='ganada').count()
        tickets_perdidos = Jugada.query.filter_by(estado='perdida').count()
        
        total_saldos_usuarios = db.session.query(func.sum(Usuario.saldo)).scalar() or 0.00

        return jsonify({
            'ingresos_apuestas': ingresos,
            'egresos_premios': egresos,
            'utilidad_neta': utilidad_neta,
            'total_saldos_custodia': float(total_saldos_usuarios),
            'conteo_tickets': {
                'pendientes': tickets_pendientes,
                'ganados': tickets_ganados,
                'perdidos': tickets_perdidos
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f"Error interno al compilar métricas: {str(e)}"}), 500