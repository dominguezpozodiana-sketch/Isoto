from datetime import date
from sqlalchemy import func
from flask import jsonify

from models import (
    Usuario,
    Jugada,
    Transaccion
)

@admin_bp.route('/api/admin/dashboard')
@requiere_rol('dueno')
def dashboard_data():

    hoy = date.today()

    jugadores = Usuario.query.filter_by(
        rol='usuario'
    ).count()

    ventas_hoy = db.session.query(
        func.coalesce(func.sum(Jugada.monto), 0)
    ).filter(
        func.date(Jugada.fecha) == hoy
    ).scalar()

    premios_hoy = db.session.query(
        func.coalesce(
            func.sum(Jugada.monto_ganado),
            0
        )
    ).filter(
        func.date(Jugada.fecha) == hoy
    ).scalar()

    ganancia = float(ventas_hoy) - float(premios_hoy)

    return jsonify({
        "jugadores": jugadores,
        "ventas_hoy": float(ventas_hoy),
        "premios_hoy": float(premios_hoy),
        "ganancia_hoy": ganancia
    })