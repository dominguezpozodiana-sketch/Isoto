from flask import Blueprint, request, jsonify, session
from models import db, Usuario, Transaccion
from utils import requiere_rol
from datetime import datetime

banca_bp = Blueprint('banca_bp', __name__)

@banca_bp.route('/api/admin/usuarios/<string:tel>/recargar', methods=['POST'])
@requiere_rol('admin', 'dueno')
def recargar_saldo(tel):
    """Ejecuta sumas o retiros sobre el monedero del jugador de forma transaccional."""
    data = request.get_json() or {}
    monto_raw = data.get('monto')
    tipo = data.get('tipo')          # 'credito' o 'debito'
    metodo = data.get('metodo')      # 'efectivo', 'zelle', 'pago_movil', 'transferencia'
    descripcion = data.get('descripcion', '')

    if monto_raw is None or not tipo or not metodo:
        return jsonify({'error': 'Todos los campos financieros son requeridos.'}), 400

    try:
        monto = float(monto_raw)
    except ValueError:
        return jsonify({'error': 'El monto debe ser un formato numérico válido.'}), 400

    if monto <= 0:
        return jsonify({'error': 'El monto de la operación debe ser mayor a cero.'}), 400

    if tipo not in ['credito', 'debito']:
        return jsonify({'error': 'Tipo de transacción desconocido.'}), 400

    usuario = Usuario.query.get_or_404(tel)
    
    if tipo == 'credito':
        usuario.saldo += monto
        mensaje_salida = f"Transacción exitosa: Se abonaron ${monto:.2f} a la cuenta de {usuario.nombre}."
    else:
        if usuario.saldo < monto:
            return jsonify({'error': f"Saldo insuficiente. El balance actual del jugador es de ${usuario.saldo:.2f}."}), 400
        usuario.saldo -= monto
        mensaje_salida = f"Transacción exitosa: Se debitaron ${monto:.2f} de la cuenta de {usuario.nombre}."

    # Inserción en el historial de transacciones para auditoría de caja
    nueva_transaccion = Transaccion(
        telefono=usuario.telefono,
        tipo=tipo,
        monto=monto,
        metodo=metodo,
        descripcion=descripcion,
        registrado_por=session.get('telefono'),
        fecha=datetime.utcnow()
    )

    db.session.add(nueva_transaccion)
    db.session.commit()

    return jsonify({
        'msg': mensaje_salida,
        'nuevo_saldo': usuario.saldo
    }), 200

@banca_bp.route('/api/jugador/transacciones', methods=['GET'])
@requiere_rol('usuario', 'admin', 'dueno')
def historial_transacciones_propio():
    """Permite al cliente logueado auditar su historial de recargas y cobros recibidos."""
    tel_usuario = session.get('telefono')
    transacciones = Transaccion.query.filter_by(telefono=tel_usuario).order_by(Transaccion.fecha.desc()).all()
    
    resultado = [{
        'id': t.id,
        'tipo': t.tipo,
        'monto': t.monto,
        'metodo': t.metodo,
        'descripcion': t.descripcion,
        'fecha': t.fecha.isoformat()
    } for t in transacciones]
    
    return jsonify({'transacciones': resultado}), 200