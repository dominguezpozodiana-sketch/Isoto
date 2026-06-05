import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from models import db, Usuario, Loteria, Jugada, Transaccion
from utils import requiere_rol, verificar_limite_banca, validar_formato_jugada

jugadas_bp = Blueprint('jugadas_bp', __name__)

CUOTAS = {'fijo': 80.00, 'corrido': 25.00, 'parle': 1000.00}

@jugadas_bp.route('/api/jugador/apostar', methods=['POST'])
@requiere_rol('usuario', 'admin', 'dueno')
def registrar_jugada():
    data = request.get_json() or {}
    loteria_id = data.get('loteria_id')
    modalidad = data.get('modalidad')
    numero_principal = data.get('numero_principal')
    numero_parle = data.get('numero_parle')
    monto_raw = data.get('monto')

    if not loteria_id or not modalidad or not numero_principal or monto_raw is None:
        return jsonify({'error': 'Información del ticket incompleta.'}), 400

    try:
        monto = float(monto_raw)
    except ValueError:
        return jsonify({'error': 'El monto debe ser un formato numérico válido.'}), 400

    if monto <= 0:
        return jsonify({'error': 'El monto debe ser superior a $0.00.'}), 400

    loteria = Loteria.query.get(loteria_id)
    if not loteria or not loteria.activa:
        return jsonify({'error': 'La lotería seleccionada está cerrada o inactiva.'}), 400

    hora_actual = datetime.now().time()
    if not (loteria.hora_apertura <= hora_actual <= loteria.hora_cierre):
        return jsonify({'error': 'Sorteo fuera de horario comercial.'}), 400

    es_valido, msg_error = validar_formato_jugada(modalidad, numero_principal, numero_parle)
    if not es_valido:
        return jsonify({'error': msg_error}), 400

    respeta_limite, msg_limite = verificar_limite_banca(modalidad, monto)
    if not respeta_limite:
        return jsonify({'error': msg_limite}), 400

    tel_usuario = session.get('telefono')
    
    # IMPLEMENTACIÓN MODERNA Y SEGURA DE BLOQUEO DE FILA (Punto 3 corregido)
    usuario = Usuario.query.filter_by(telefono=tel_usuario).with_for_update().first()
    if not usuario:
        return jsonify({'error': 'Usuario no registrado.'}), 404

    if usuario.saldo < monto:
        return jsonify({'error': f'Fondos insuficientes. Saldo actual: ${usuario.saldo:.2f}'}), 400

    cuota = CUOTAS.get(modalidad, 1.00)
    ganancia_potencial = monto * cuota

    usuario.saldo -= db.type_coerce(monto, db.Numeric(10, 2))
    ticket_id = uuid.uuid4().hex.upper()

    nueva_jugada = Jugada(
        id=ticket_id,
        telefono=usuario.telefono,
        loteria_id=loteria.id,
        modalidad=modalidad,
        numero_principal=numero_principal,
        numero_parle=numero_parle if modalidad == 'parle' else None,
        monto=monto,
        cuota_aplicada=cuota,
        ganancia_potencial=ganancia_potencial,
        estado='pendiente'
    )
    db.session.add(nueva_jugada)

    auditoria_debito = Transaccion(
        telefono=usuario.telefono,
        tipo='apuesta',
        monto=monto,
        balance_posterior=usuario.saldo,
        referencia_id=ticket_id,
        ejecutado_por=usuario.telefono
    )
    db.session.add(auditoria_debito)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Fallo de base de datos al asentar la jugada: {str(e)}'}), 500

    return jsonify({
        'msg': 'Ticket enviado de forma blindada.',
        'ticket': ticket_id,
        'nuevo_saldo': float(usuario.saldo)
    }), 200