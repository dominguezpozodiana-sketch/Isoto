from flask import Blueprint, jsonify, request, session
from datetime import datetime, time
import pytz
from models import db, Loteria
from utils import requiere_rol

loterias_bp = Blueprint('loterias_bp', __name__)

# Almacenamiento en memoria para cierres manuales del día actual (se reinicia al pasar la medianoche)
# Estructura: { (loteria_id, fecha_str): True }
cierres_manuales_hoy = {}

def obtener_estado_loteria(loteria, zona_horaria="US/Eastern"):
    """Calcula el estado exacto de la lotería basado en la hora actual de la costa este."""
    tz = pytz.timezone(zona_horaria)
    ahora = datetime.now(tz)
    hora_actual = ahora.time()
    fecha_actual_str = ahora.strftime('%Y-%m-%d')

    # 1. Verificar si fue forzado un cierre manual hoy
    if cierres_manuales_hoy.get((loteria.id, fecha_actual_str)):
        return "cerrada"
    
    # 2. Verificar si no está activa globalmente
    if not loteria.activa:
        return "proximamente"

    # Conversiones de strings/times si aplica
    h_apertura = loteria.hora_apertura
    h_cierre = loteria.hora_cierre
    h_resultado = loteria.hora_resultado

    if hora_actual < h_apertura:
        return "proximamente"
    elif h_apertura <= hora_actual < h_cierre:
        return "abierta"
    elif h_cierre <= hora_actual < h_resultado:
        return "cerrada"
    else:
        # Pasa de la hora del resultado. Si ya hay un número registrado en BD para hoy,
        # su estado final pasará a 'procesada', de lo contrario devuelve 'resultado_pendiente'.
        from models import Resultado
        res = Resultado.query.filter_by(loteria_id=loteria.id, fecha=ahora.date()).first()
        if res and res.procesado:
            return "procesada"
        return "resultado_pendiente"

@loterias_bp.route('/api/loterias', methods=['GET'])
def listar_loterias():
    """Endpoint público para los jugadores. Muestra estados calculados al instante."""
    loterias = Loteria.query.filter_by(activa=True).all()
    resultado = []
    
    for lot in loterias:
        estado_actual = obtener_estado_loteria(lot)
        resultado.append({
          'id': lot.id,
          'nombre': lot.nombre,
          'turno': lot.turno,
          'hora_cierre': lot.hora_cierre.strftime('%I:%M %p'),
          'estado': estado_actual
        })
    return jsonify({'loterias': resultado}), 200

@loterias_bp.route('/api/loterias/<int:id>/cerrar-hoy', methods=['POST'])
@requiere_rol('admin', 'dueno')
def cerrar_manual(id):
    """Permite a un administrador forzar el cierre anticipado de una lotería específica por hoy."""
    loteria = Loteria.query.get_or_404(id)
    tz = pytz.timezone(loteria.zona_horaria or "US/Eastern")
    fecha_hoy_str = datetime.now(tz).strftime('%Y-%m-%d')
    
    cierres_manuales_hoy[(loteria.id, fecha_hoy_str)] = True
    
    return jsonify({
        'msg': f'La lotería {loteria.nombre} ha sido cerrada manualmente por el resto del día.',
        'loteria_id': id,
        'estado': 'cerrada'
    }), 200