from flask import Blueprint, request, jsonify, session
from datetime import datetime
from models import db, Resultado, Jugada, Usuario
from utils import requiere_rol

resultados_bp = Blueprint('resultados_bp', __name__)

def verificar_combinacion_parle(numero_apostado, tipo, pick3, pick4):
    """Auxiliar para comprobar si un número individual del Parlé se encuentra en los resultados."""
    if tipo == 'fijo':
        # Debe ser igual a los últimos 2 dígitos del Pick 3
        return numero_apostado == pick3[1:]
    elif tipo == 'corrido':
        # El Pick 3 completo contiene los 2 dígitos apostados (evaluando combinaciones de letras/posiciones)
        # Ejemplo: apostado '74', pick3 '472' -> True
        p3_list = list(pick3)
        try:
            p3_list.remove(numero_apostado[0])
            p3_list.remove(numero_apostado[1])
            return True
        except ValueError:
            return False
    return False

def evaluar_ticket(jugada, pick3, pick4):
    """
    Aplica las reglas exactas de validación de aciertos para la bolita cubana.
    Devuelve True si el ticket es ganador, False si es perdedor.
    """
    modalidad = jugada.modalidad

    if modalidad == 'fijo':
        # Compara contra los últimos 2 dígitos del Pick 3
        return jugada.numero_principal == pick3[1:]

    elif modalidad == 'corrido':
        # Compara si los 2 dígitos del jugador están incluidos dentro del Pick 3 oficial
        p3_list = list(pick3)
        try:
            p3_list.remove(jugada.numero_principal[0])
            p3_list.remove(jugada.numero_principal[1])
            return True
        except ValueError:
            return False

    elif modalidad == 'parle':
        # Un Parlé se compone de dos números combinados. Por simplicidad reglamentaria estándar,
        # evaluamos si el número 1 y el número 2 se consolidan dentro del pool del sorteo actual.
        # En este motor, se verifica la presencia del primer número en el Pick 3 (fijo o corrido)
        # y del segundo número en el Pick 4, o combinaciones cruzadas permitidas en la banca.
        gana1 = (jugada.numero_principal == pick3[1:] or jugada.numero_principal == pick4[2:])
        gana2 = (jugada.numero_parle == pick4[2:] or jugada.numero_parle == pick3[1:])
        return gana1 and gana2

    return False

@resultados_bp.route('/api/resultados', methods=['POST'])
@requiere_rol('admin', 'dueno')
def ingresar_y_escrutar():
    """Registra los números oficiales, audita jugadas pendientes y paga premios automáticamente."""
    data = request.get_json() or {}
    loteria_id = data.get('loteria_id')
    fecha_str = data.get('fecha')  # Formato 'YYYY-MM-DD'
    pick3 = data.get('pick3')      # 3 dígitos, ej: '385'
    pick4 = data.get('pick4')      # 4 dígitos, ej: '2741'

    # 1. Validaciones estructurales de seguridad
    if not loteria_id or not fecha_str or not pick3 or not pick4:
        return jsonify({'error': 'Todos los campos de resultados son obligatorios.'}), 400

    if len(pick3) != 3 or len(pick4) != 4 or not pick3.isdigit() or not pick4.isdigit():
        return jsonify({'error': 'Los formatos numéricos de los Picks son incorrectos.'}), 400

    try:
        fecha_evaluacion = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'El formato de fecha provisto es inválido.'}), 400

    # 2. Impedir duplicados de escrutinio para la misma fecha y lotería
    resultado_existente = Resultado.query.filter_by(loteria_id=loteria_id, fecha=fecha_evaluacion).first()
    if resultado_existente:
        return jsonify({'error': 'Ya se han digitado y procesado los resultados de este sorteo para la fecha indicada.'}), 400

    # 3. Guardar el registro base del resultado oficial
    nuevo_resultado = Resultado(
        loteria_id=loteria_id,
        fecha=fecha_evaluacion,
        pick3=pick3,
        pick4=pick4,
        fuente='manual',
        procesado=False,
        ingresado_por=session.get('telefono')
    )
    db.session.add(nuevo_resultado)

    # 4. Motor de Escrutinio Transaccional en Caliente
    # Extrae todas las jugadas pendientes de esta lotería específica en la fecha seleccionada
    jugadas_pendientes = Jugada.query.filter(
        Jugada.loteria_id == loteria_id,
        Jugada.estado == 'pendiente',
        db.func.date(Jugada.fecha) == fecha_evaluacion
    ).all()

    total_procesadas = 0
    total_ganadoras = 0
    monto_total_pagado = 0.0

    for jugada in jugadas_pendientes:
        es_ganador = evaluar_ticket(jugada, pick3, pick4)
        usuario = Usuario.query.get(jugada.telefono)

        if es_ganador:
            jugada.estado = 'ganada'
            jugada.monto_ganado = jugada.monto * jugada.cuota_aplicada
            if usuario:
                usuario.saldo += jugada.monto_ganado # Acreditación directa a la billetera virtual
            total_ganadoras += 1
            monto_total_pagado += jugada.monto_ganado
        else:
            jugada.estado = 'perdida'
            jugada.monto_ganado = 0.0
        
        total_procesadas += 1

    # 5. Consolidar cambios de forma atómica en Postgres
    nuevo_resultado.procesado = True
    nuevo_resultado.procesado_en = datetime.utcnow()
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Fallo crítico al asentar el escrutinio: {str(e)}"}), 500

    return jsonify({
        'msg': 'Sorteo escrutado con éxito. Carteras actualizadas.',
        'procesadas': total_procesadas,
        'ganadoras': total_ganadoras,
        'monto_pagado': monto_total_pagado
    }), 201