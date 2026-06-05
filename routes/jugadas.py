import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from models import db, Usuario, Loteria, Jugada
from utils import requiere_rol, CUOTAS_DEFECTO, validar_formato_jugada, verificar_limite_banca

jugadas_bp = Blueprint('jugadas_bp', __name__)

@jugadas_bp.route('/api/jugador/apostar', methods=['POST'])
@requiere_rol('usuario', 'admin', 'dueno')
def registrar_jugada():
    """Valida, descuenta saldo y almacena una jugada bajo las reglas de la banca."""
    data = request.get_json() or {}
    loteria_id = data.get('loteria_id')
    modalidad = data.get('modalidad')              # 'fijo', 'corrido', 'parle'
    numero_principal = data.get('numero_principal') # Primer número (2 dígitos)
    numero_parle = data.get('numero_parle')         # Segundo número (solo si es parlé)
    monto_raw = data.get('monto')

    # 1. Validaciones iniciales de presencia de datos
    if not loteria_id or not modalidad or not numero_principal or monto_raw is None:
        return jsonify({'error': 'Faltan campos mandatorios para procesar la jugada.'}), 400

    try:
        monto = float(monto_raw)
    except ValueError:
        return jsonify({'error': 'El monto de la jugada debe ser un valor numérico.'}), 400

    if monto <= 0:
        return jsonify({'error': 'El monto apostado debe ser mayor a cero.'}), 400

    # 2. Validar que la lotería exista y esté operativa
    loteria = Loteria.query.get(loteria_id)
    if not loteria or not loteria.activa:
        return jsonify({'error': 'La lotería seleccionada no está disponible o fue pausada.'}), 400

    # 3. Validar reglas de formato numérico (00-99) según modalidad
    es_valido, msg_error = validar_formato_jugada(modalidad, numero_principal, numero_parle)
    if not es_valido:
        return jsonify({'error': msg_error}), 400

    # 4. Validar límites de riesgo de la banca (Topes máximos)
    respeta_limite, msg_limite = verificar_limite_banca(modalidad, monto)
    if not respeta_limite:
        return jsonify({'error': msg_limite}), 400

    # 5. Comprobación y débito de saldo del Usuario
    tel_usuario = session.get('telefono')
    usuario = Usuario.query.get(tel_usuario)
    if not usuario:
        return jsonify({'error': 'Usuario no localizado en el sistema.'}), 404

    if usuario.saldo < monto:
        return jsonify({'error': f"Saldo insuficiente. Tu balance es de ${usuario.saldo:.2f} y la jugada cuesta ${monto:.2f}."}), 400

    # 6. Aplicar cuota y calcular ganancia potencial
    cuota = CUOTAS_DEFECTO.get(modalidad, 1.0)
    ganancia_potencial = monto * cuota

    # 7. Descontar saldo y guardar jugada en la base de datos
    usuario.saldo -= monto

    nueva_jugada = Jugada(
        id=str(uuid.uuid4())[:8].upper(), # ID de ticket corto y legible
        telefono=usuario.telefono,
        loteria_id=loteria.id,
        modalidad=modalidad,
        numero_principal=numero_principal,
        numero_parle=numero_parle if modalidad == 'parle' else None,
        monto=monto,
        cuota_aplicada=cuota,
        ganancia_potencial=ganancia_potencial,
        fecha=datetime.utcnow(),
        estado='pendiente'
    )

    try:
        db.session.add(nueva_jugada)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Error crítico al registrar la jugada: {str(e)}"}), 500

    return jsonify({
        'msg': '¡Jugada procesada y registrada exitosamente!',
        'ticket': nueva_jugada.id,
        'nuevo_saldo': usuario.saldo,
        'ganancia_potencial': ganancia_potencial
    }), 200

@jugadas_bp.route('/api/jugador/historial-jugadas', methods=['GET'])
@requiere_rol('usuario', 'admin', 'dueno')
def historial_jugadas_propias():
    """Devuelve todas las jugadas efectuadas por el cliente en sesión."""
    tel_usuario = session.get('telefono')
    lista = Jugada.query.filter_by(telefono=tel_usuario).order_by(Jugada.fecha.desc()).all()
    
    resultado = [{
        'id': j.id,
        'loteria': j.loteria.nombre if j.loteria else 'Lotería Eliminada',
        'modalidad': j.modalidad.upper(),
        'numero': f"{j.numero_principal} - {j.numero_parle}" if j.numero_parle else j.numero_principal,
        'monto': j.monto,
        'premio_potencial': j.ganancia_potencial,
        'estado': j.estado.upper(),
        'fecha': j.fecha.isoformat()
    } for j in lista]
    
    return jsonify({'jugadas': resultado}), 200