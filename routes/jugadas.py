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
        monto = db.type_coerce(float(monto_raw), db.Numeric(10, 2))
    except ValueError:
        return jsonify({'error': 'El monto debe ser un formato numérico válido.'}), 400

    if monto <= 0:
        return jsonify({'error': 'El monto debe ser superior a $0.00.'}), 400

    # 1. Validar existencia y horarios reales de la lotería
    loteria = Loteria.query.get(loteria_id)
    if not loteria or not loteria.activa:
        return jsonify({'error': 'La lotería seleccionada está cerrada o inactiva.'}), 400

    # Validación horaria estricta (Punto 25)
    hora_actual = datetime.now().time()
    if not (loteria.hora_apertura <= hora_actual <= loteria.hora_cierre):
        return jsonify({'error': f'Sorteo fuera de horario comercial. Abierto de {loteria.hora_apertura.strftime("%H:%M")} a {loteria.hora_cierre.strftime("%H:%M")}.'}), 400

    # 2. Formato numérico y límites de riesgo de banca
    es_valido, msg_error = validar_formato_jugada(modalidad, numero_principal, numero_parle)
    if not es_valido:
        return jsonify({'error': msg_error}), 400

    respeta_limite, msg_limite = verificar_limite_banca(modalidad, monto)
    if not respeta_limite:
        return jsonify({'error': msg_limite}), 400

    # ========================================================
    # PROTECCIÓN CRÍTICA DE CONCURRENCIA: BLOQUEO DE FILA (FOR UPDATE)
    # ========================================================
    tel_usuario = session.get('telefono')
    
    # Bloquea la fila del usuario en Postgres hasta terminar el commit (Puntos 5 y 26)
    usuario = Usuario.query.with_for_update().get(tel_usuario)
    if not usuario:
        return jsonify({'error': 'Usuario no registrado.'}), 404

    if usuario.saldo < monto:
        return jsonify({'error': f'Fondos insuficientes. Saldo actual: ${usuario.saldo:.2f}'}), 400

    # Calcular ganancias
    cuota = CUOTAS.get(modalidad, 1.00)
    ganancia_potencial = monto * cuota

    # Descontar saldo de forma segura
    usuario.saldo -= monto
    
    # Identificador de ticket largo y ultra seguro sin colisiones (Punto 6)
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

    # Registro en el libro de auditoría financiera (Punto 24)
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
        'msg': 'Ticket enviado y registrado de forma blindada.',
        'ticket': ticket_id,
        'nuevo_saldo': float(usuario.saldo)
    }), 200


@jugadas_bp.route('/api/jugador/historial-jugadas', methods=['GET'])
@requiere_rol('usuario', 'admin', 'dueno')
def historial_jugadas_propias():
    tel_usuario = session.get('telefono')
    lista = Jugada.query.filter_by(telefono=tel_usuario).order_by(Jugada.fecha.desc()).all()
    
    # Nota: j.loteria.nombre funciona de forma garantizada gracias a la relación añadida en models.py
    resultado = [{
        'id': j.id,
        'loteria': j.loteria.nombre if j.loteria else 'Sorteo Desconocido',
        'modalidad': j.modalidad.upper(),
        'numero': f"{j.numero_principal} - {j.numero_parle}" if j.numero_parle else j.numero_principal,
        'monto': float(j.monto),
        'premio_potencial': float(j.ganancia_potencial),
        'estado': j.estado.upper(),
        'fecha': j.fecha.isoformat()
    } for j in lista]
    
    return jsonify({'jugadas': resultado}), 200