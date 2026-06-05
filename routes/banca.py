from flask import Blueprint, request, jsonify, session
from models import db, Usuario, Transaccion
from utils import requiere_rol

banca_bp = Blueprint('banca_bp', __name__)

@banca_bp.route('/api/banca/recargar', methods=['POST'])
@requiere_rol('admin', 'dueno')
def recargar_saldo_jugador():
    """Acredita fondos líquidos de forma segura en la cartera de un cliente."""
    data = request.get_json() or {}
    telefono = data.get('telefono')
    monto_raw = data.get('monto')

    if not telefono or monto_raw is None:
        return jsonify({'error': 'Se requiere especificar el teléfono del destinatario y el monto.'}), 400

    try:
        monto = float(monto_raw)
    except ValueError:
        return jsonify({'error': 'El valor de la recarga debe ser un número válido.'}), 400

    if monto <= 0:
        return jsonify({'error': 'El monto a recargar debe ser una cifra positiva superior a cero.'}), 400

    # Bloqueo de fila para control estricto de concurrencia de saldos
    usuario = Usuario.query.with_for_update().get(telefono)
    if not usuario:
        return jsonify({'error': 'El usuario a recargar no se encuentra registrado.'}), 404

    # Ejecutar la adición del saldo
    usuario.saldo += db.type_coerce(monto, db.Numeric(10, 2))

    # Inyección obligatoria en el registro de auditoría financiera (Punto 24 corregido)
    movimiento_auditoria = Transaccion(
        telefono=usuario.telefono,
        tipo='recarga',
        monto=monto,
        balance_posterior=usuario.saldo,
        referencia_id=None,
        ejecutado_por=session.get('telefono')
    )
    db.session.add(movimiento_auditoria)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Error transaccional al asentar la recarga: {str(e)}"}), 500

    return jsonify({
        'msg': f"Recarga exitosa. Se han acreditado ${monto:.2f} a la cuenta del usuario {telefono}.",
        'nuevo_saldo': float(usuario.saldo)
    }), 200


@banca_bp.route('/api/banca/retirar', methods=['POST'])
@requiere_rol('admin', 'dueno')
def debitar_retiro_jugador():
    """Registra y debita un retiro físico de capital solicitado por el usuario."""
    data = request.get_json() or {}
    telefono = data.get('telefono')
    monto_raw = data.get('monto')

    if not telefono or monto_raw is None:
        return jsonify({'error': 'Se requiere el teléfono y el monto para procesar el retiro.'}), 400

    try:
        monto = float(monto_raw)
    except ValueError:
        return jsonify({'error': 'El monto de retiro debe poseer formato numérico.'}), 400

    if monto <= 0:
        return jsonify({'error': 'El monto de extracción debe ser superior a cero.'}), 400

    # Bloqueo de concurrencia pesimista
    usuario = Usuario.query.with_for_update().get(telefono)
    if not usuario:
        return jsonify({'error': 'El jugador indicado no existe.'}), 404

    if usuario.saldo < monto:
        return jsonify({'error': f"Operación cancelada. El usuario posee saldo insuficiente (${usuario.saldo:.2f}) para este débito."}), 400

    # Deducción del capital
    usuario.saldo -= db.type_coerce(monto, db.Numeric(10, 2))

    # Asentamiento en el libro maestro de auditoría financiera (Punto 24 corregido)
    movimiento_auditoria = Transaccion(
        telefono=usuario.telefono,
        tipo='retiro',
        monto=monto,
        balance_posterior=usuario.saldo,
        referencia_id=None,
        ejecutado_por=session.get('telefono')
    )
    db.session.add(movimiento_auditoria)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Error transaccional al asentar el débito de retiro: {str(e)}"}), 500

    return jsonify({
        'msg': f"Retiro procesado. Se han debitado ${monto:.2f} de la cuenta de {telefono}.",
        'nuevo_saldo': float(usuario.saldo)
    }), 200