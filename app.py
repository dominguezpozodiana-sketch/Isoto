import os
import uuid
import re
import pytz
import bcrypt
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, time, timedelta
from flask import Flask, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

app = Flask(__name__, static_folder='.')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-super-secreta-cambiar')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///bolita.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app, supports_credentials=True)

# Zona horaria Eastern Time
ET = pytz.timezone('US/Eastern')

# ---------------------------- MODELOS ---------------------------------
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    telefono = db.Column(db.String, primary_key=True)
    password = db.Column(db.String, nullable=False)
    nombre = db.Column(db.String, nullable=False)
    rol = db.Column(db.String, nullable=False)  # jugador, admin, dueño
    activo = db.Column(db.Boolean, default=True)
    saldo = db.Column(db.Float, default=0.0)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime, nullable=True)
    total_sesiones = db.Column(db.Integer, default=0)
    tiempo_total_minutos = db.Column(db.Integer, default=0)
    ip_registro = db.Column(db.String, nullable=True)
    admin_id = db.Column(db.String, db.ForeignKey('usuarios.telefono'), nullable=True)

class Loteria(db.Model):
    __tablename__ = 'loterias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    estado_usa = db.Column(db.String, nullable=False)
    turno = db.Column(db.String, nullable=False)  # dia / noche
    hora_apertura = db.Column(db.Time, nullable=False)
    hora_cierre = db.Column(db.Time, nullable=False)
    hora_resultado = db.Column(db.Time, nullable=False)
    zona_horaria = db.Column(db.String, default='US/Eastern')
    activa = db.Column(db.Boolean, default=True)

class Jugada(db.Model):
    __tablename__ = 'jugadas'
    id = db.Column(db.String, primary_key=True)
    telefono = db.Column(db.String, db.ForeignKey('usuarios.telefono'), nullable=False)
    loteria_id = db.Column(db.Integer, db.ForeignKey('loterias.id'), nullable=False)
    fecha_tiro = db.Column(db.Date, nullable=False)
    modalidad = db.Column(db.String, nullable=False)
    numero_principal = db.Column(db.String, nullable=False)
    numero_parle = db.Column(db.String, nullable=True)
    tipo_parle_1 = db.Column(db.String, nullable=True)
    tipo_parle_2 = db.Column(db.String, nullable=True)
    monto = db.Column(db.Float, nullable=False)
    cuota_aplicada = db.Column(db.Float, nullable=False)
    ganancia_potencial = db.Column(db.Float, nullable=False)
    fecha_apuesta = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String, default='pendiente')
    monto_ganado = db.Column(db.Float, default=0.0)

class Resultado(db.Model):
    __tablename__ = 'resultados'
    id = db.Column(db.Integer, primary_key=True)
    loteria_id = db.Column(db.Integer, db.ForeignKey('loterias.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    numero_ganador_pick3 = db.Column(db.String(3), nullable=True)
    numero_ganador_pick4 = db.Column(db.String(4), nullable=True)
    fuente = db.Column(db.String, default='manual')
    procesado = db.Column(db.Boolean, default=False)
    fecha_procesado = db.Column(db.DateTime, nullable=True)

class Transaccion(db.Model):
    __tablename__ = 'transacciones'
    id = db.Column(db.Integer, primary_key=True)
    telefono = db.Column(db.String, db.ForeignKey('usuarios.telefono'), nullable=False)
    tipo = db.Column(db.String, nullable=False)
    monto = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.String, nullable=True)
    metodo_pago = db.Column(db.String, nullable=True)
    admin_telefono = db.Column(db.String, db.ForeignKey('usuarios.telefono'), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class SolicitudRegistro(db.Model):
    __tablename__ = 'solicitudes_registro'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    telefono_whatsapp = db.Column(db.String, unique=True, nullable=False)
    codigo = db.Column(db.String(6), nullable=True)
    codigo_expira = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String, default='pendiente')
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    aprobado_por = db.Column(db.String, db.ForeignKey('usuarios.telefono'), nullable=True)

class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    id = db.Column(db.Integer, primary_key=True)
    destinatario_rol = db.Column(db.String, nullable=False)
    tipo = db.Column(db.String, nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    leida = db.Column(db.Boolean, default=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    datos_extra = db.Column(db.Text, nullable=True)

class Sesion(db.Model):
    __tablename__ = 'sesiones'
    id = db.Column(db.Integer, primary_key=True)
    telefono = db.Column(db.String, db.ForeignKey('usuarios.telefono'), nullable=False)
    ip_address = db.Column(db.String, nullable=False)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime, nullable=True)
    duracion_minutos = db.Column(db.Integer, default=0)

class IntentoLogin(db.Model):
    __tablename__ = 'intentos_login'
    id = db.Column(db.Integer, primary_key=True)
    telefono = db.Column(db.String, nullable=True)
    ip_address = db.Column(db.String, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    exitoso = db.Column(db.Boolean, default=False)

class AlertaSeguridad(db.Model):
    __tablename__ = 'alertas_seguridad'
    id = db.Column(db.Integer, primary_key=True)
    telefono = db.Column(db.String, db.ForeignKey('usuarios.telefono'), nullable=False)
    tipo = db.Column(db.String, nullable=False)
    descripcion = db.Column(db.String, nullable=False)
    nivel = db.Column(db.String, default='media')
    resuelta = db.Column(db.Boolean, default=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class Cuota(db.Model):
    __tablename__ = 'cuotas'
    id = db.Column(db.Integer, primary_key=True)
    modalidad = db.Column(db.String, unique=True, nullable=False)
    multiplicador = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.String, nullable=True)
    actualizado_por = db.Column(db.String, nullable=True)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------------------- FUNCIONES AUXILIARES --------------------------------
def hash_password(passwd):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(passwd.encode('utf-8'), salt).decode('utf-8')

def check_password(passwd, hashed):
    return bcrypt.checkpw(passwd.encode('utf-8'), hashed.encode('utf-8'))

def generar_codigo():
    import random
    return f"{random.randint(100000, 999999)}"

def obtener_ip():
    return request.remote_addr

def calcular_estado_loteria(loteria):
    ahora = datetime.now(ET).time()
    if not loteria.activa:
        return "inactiva"
    if ahora < loteria.hora_apertura:
        return "proximamente"
    elif ahora < loteria.hora_cierre:
        return "abierta"
    elif ahora < loteria.hora_resultado:
        return "cerrada"
    else:
        res = Resultado.query.filter_by(loteria_id=loteria.id, fecha=date.today()).first()
        if res and res.numero_ganador_pick3 is not None:
            return "resultado_conocido"
        else:
            return "resultado_pendiente"

def obtener_cuota(modalidad, tipo_parle1=None, tipo_parle2=None):
    if modalidad == 'parle':
        clave = f"parle_{tipo_parle1[0]}{tipo_parle2[0]}"
        cu = Cuota.query.filter_by(modalidad=clave).first()
    else:
        cu = Cuota.query.filter_by(modalidad=modalidad).first()
    return cu.multiplicador if cu else 1

def procesar_ganadores(loteria_id, fecha, pick3, pick4):
    jugadas = Jugada.query.filter_by(loteria_id=loteria_id, fecha_tiro=fecha, estado='pendiente').all()
    for jug in jugadas:
        gano = False
        modalidad = jug.modalidad
        if modalidad == 'centena':
            if pick3 == jug.numero_principal:
                gano = True
        elif modalidad == 'fijo':
            fijo_real = pick3[1:] if pick3 else ''
            if jug.numero_principal == fijo_real:
                gano = True
        elif modalidad == 'corrido_p3':
            fijo_real = pick3[1:] if pick3 else ''
            if sorted(jug.numero_principal) == sorted(fijo_real):
                gano = True
        elif modalidad == 'corrido_p4_ab':
            ab = pick4[:2] if pick4 else ''
            if sorted(jug.numero_principal) == sorted(ab):
                gano = True
        elif modalidad == 'corrido_p4_cd':
            cd = pick4[2:] if pick4 else ''
            if sorted(jug.numero_principal) == sorted(cd):
                gano = True
        elif modalidad == 'parle':
            gano1 = False
            n1 = jug.numero_principal
            t1 = jug.tipo_parle_1
            if t1 == 'fijo':
                fijo_real = pick3[1:] if pick3 else ''
                if n1 == fijo_real:
                    gano1 = True
            elif t1 == 'corrido':
                fijo_real = pick3[1:] if pick3 else ''
                if sorted(n1) == sorted(fijo_real):
                    gano1 = True
            gano2 = False
            n2 = jug.numero_parle
            t2 = jug.tipo_parle_2
            if t2 == 'fijo':
                if n2 == pick3[1:]:
                    gano2 = True
            elif t2 == 'corrido':
                if sorted(n2) == sorted(pick3[1:]):
                    gano2 = True
            if gano1 and gano2:
                gano = True
        if gano:
            ganancia = jug.monto * jug.cuota_aplicada
            jug.estado = 'ganada'
            jug.monto_ganado = ganancia
            user = Usuario.query.get(jug.telefono)
            if user:
                user.saldo += ganancia
                trans = Transaccion(telefono=user.telefono, tipo='premio', monto=ganancia, descripcion=f'Premio {modalidad} lotería {loteria_id}')
                db.session.add(trans)
        else:
            jug.estado = 'perdida'
    db.session.commit()
    res = Resultado.query.filter_by(loteria_id=loteria_id, fecha=fecha).first()
    if res:
        res.procesado = True
        res.fecha_procesado = datetime.utcnow()
        db.session.commit()

def job_scraping():
    hoy = date.today()
    loterias = Loteria.query.filter_by(activa=True).all()
    for lot in loterias:
        hora_res = lot.hora_resultado
        ahora = datetime.now(ET)
        if ahora.time() > hora_res and ahora.hour < 23:
            res = Resultado.query.filter_by(loteria_id=lot.id, fecha=hoy).first()
            if not res or res.numero_ganador_pick3 is None:
                try:
                    pick3, pick4 = None, None
                    # Simulación de scraping (reemplazar con llamadas reales)
                    if lot.estado_usa == 'Florida':
                        # Aquí iría el scraping real
                        pick3 = "472"
                        pick4 = "3815"
                    else:
                        pick3 = "123"
                        pick4 = "4567"
                    if pick3:
                        if not res:
                            res = Resultado(loteria_id=lot.id, fecha=hoy, numero_ganador_pick3=pick3, numero_ganador_pick4=pick4, fuente='auto')
                            db.session.add(res)
                        else:
                            res.numero_ganador_pick3 = pick3
                            res.numero_ganador_pick4 = pick4
                            res.fuente = 'auto'
                        db.session.commit()
                        procesar_ganadores(lot.id, hoy, pick3, pick4)
                except Exception as e:
                    print(f"Error scraping {lot.nombre}: {e}")

# Iniciar scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=job_scraping, trigger=IntervalTrigger(minutes=30), id='scraping_job', replace_existing=True)
scheduler.start()

# ---------------------------- RUTAS API ---------------------------------
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/solicitud-registro', methods=['POST'])
def solicitud_registro():
    data = request.get_json()
    nombre = data.get('nombre', '').strip()
    telefono_whatsapp = data.get('telefono_whatsapp', '').strip()
    if not nombre or not telefono_whatsapp:
        return jsonify({"error": "Nombre y número de WhatsApp son obligatorios"}), 400
    if not re.match(r'^\d{10,15}$', telefono_whatsapp):
        return jsonify({"error": "Formato de teléfono inválido. Solo números, código país incluido (ej: 13055551234)"}), 400
    existente = SolicitudRegistro.query.filter_by(telefono_whatsapp=telefono_whatsapp, estado='pendiente').first()
    if existente:
        return jsonify({"error": "Ya tienes una solicitud pendiente. Espera la aprobación."}), 400
    usuario_ya = Usuario.query.get(telefono_whatsapp)
    if usuario_ya:
        return jsonify({"error": "Este número ya está registrado como usuario activo."}), 400
    solicitud = SolicitudRegistro(nombre=nombre, telefono_whatsapp=telefono_whatsapp)
    db.session.add(solicitud)
    db.session.commit()
    admins = Usuario.query.filter(Usuario.rol.in_(['admin', 'dueño'])).all()
    for admin in admins:
        notif = Notificacion(
            destinatario_rol=admin.rol,
            tipo='registro',
            mensaje=f'Nueva solicitud de registro: {nombre} ({telefono_whatsapp})',
            datos_extra=f'{{"solicitud_id": {solicitud.id}}}'
        )
        db.session.add(notif)
    db.session.commit()
    return jsonify({"exito": True, "mensaje": "Solicitud enviada. Espera a que un administrador apruebe tu registro."})

@app.route('/api/verificar-codigo', methods=['POST'])
def verificar_codigo():
    data = request.get_json()
    telefono = data.get('telefono_whatsapp', '').strip()
    codigo = data.get('codigo', '').strip()
    solicitud = SolicitudRegistro.query.filter_by(telefono_whatsapp=telefono, estado='pendiente').first()
    if not solicitud:
        return jsonify({"error": "No hay solicitud pendiente para este número."}), 400
    if not solicitud.codigo or solicitud.codigo != codigo:
        return jsonify({"error": "Código incorrecto."}), 400
    if solicitud.codigo_expira and datetime.utcnow() > solicitud.codigo_expira:
        return jsonify({"error": "El código ha expirado. Solicita un nuevo código al administrador."}), 400
    hashed = hash_password(telefono[-4:])
    nuevo_usuario = Usuario(
        telefono=telefono,
        password=hashed,
        nombre=solicitud.nombre,
        rol='jugador',
        activo=True,
        saldo=0.0,
        ip_registro=obtener_ip(),
        admin_id=solicitud.aprobado_por
    )
    db.session.add(nuevo_usuario)
    solicitud.estado = 'aprobado'
    db.session.commit()
    session['user'] = {'telefono': nuevo_usuario.telefono, 'nombre': nuevo_usuario.nombre, 'rol': nuevo_usuario.rol}
    return jsonify({"exito": True, "mensaje": "Cuenta activada. Ya puedes apostar.", "usuario": {"telefono": nuevo_usuario.telefono, "nombre": nuevo_usuario.nombre, "rol": nuevo_usuario.rol}})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    telefono = data.get('telefono', '').strip()
    password = data.get('password', '')
    ip = obtener_ip()
    usuario = Usuario.query.get(telefono)
    if not usuario or not check_password(password, usuario.password):
        intento = IntentoLogin(telefono=telefono, ip_address=ip, exitoso=False)
        db.session.add(intento)
        db.session.commit()
        return jsonify({"error": "Teléfono o contraseña incorrectos"}), 401
    if not usuario.activo:
        return jsonify({"error": "Usuario bloqueado. Contacta al administrador."}), 403
    intento_exitoso = IntentoLogin(telefono=telefono, ip_address=ip, exitoso=True)
    db.session.add(intento_exitoso)
    nueva_sesion = Sesion(telefono=telefono, ip_address=ip)
    db.session.add(nueva_sesion)
    usuario.ultimo_login = datetime.utcnow()
    usuario.total_sesiones += 1
    db.session.commit()
    session['user'] = {'telefono': usuario.telefono, 'nombre': usuario.nombre, 'rol': usuario.rol}
    vistas = ['loterias']
    if usuario.rol == 'jugador':
        vistas += ['historial']
    elif usuario.rol == 'admin':
        vistas += ['admin_solicitudes', 'admin_usuarios', 'admin_resultados', 'admin_reportes', 'historial']
    elif usuario.rol == 'dueño':
        vistas += ['admin_solicitudes', 'admin_usuarios', 'admin_resultados', 'admin_reportes', 'dueno_loterias', 'dueno_admins', 'historial']
    return jsonify({"usuario": {"telefono": usuario.telefono, "nombre": usuario.nombre, "rol": usuario.rol}, "vistas": vistas})

@app.route('/api/logout', methods=['POST'])
def logout():
    if 'user' in session:
        telefono = session['user']['telefono']
        sesion_activa = Sesion.query.filter_by(telefono=telefono, fecha_fin=None).order_by(Sesion.fecha_inicio.desc()).first()
        if sesion_activa:
            sesion_activa.fecha_fin = datetime.utcnow()
            sesion_activa.duracion_minutos = int((sesion_activa.fecha_fin - sesion_activa.fecha_inicio).total_seconds() / 60)
            usuario = Usuario.query.get(telefono)
            if usuario:
                usuario.tiempo_total_minutos += sesion_activa.duracion_minutos
            db.session.commit()
    session.pop('user', None)
    return jsonify({"exito": True})

@app.route('/api/perfil', methods=['GET'])
def perfil():
    if 'user' not in session:
        return jsonify({"error": "No autorizado"}), 401
    user = Usuario.query.get(session['user']['telefono'])
    return jsonify({"telefono": user.telefono, "nombre": user.nombre, "rol": user.rol, "saldo": user.saldo, "activo": user.activo})

@app.route('/api/cambiar-password', methods=['POST'])
def cambiar_password():
    if 'user' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.get_json()
    old = data.get('password_actual', '')
    new = data.get('password_nueva', '')
    user = Usuario.query.get(session['user']['telefono'])
    if not check_password(old, user.password):
        return jsonify({"error": "Contraseña actual incorrecta"}), 400
    user.password = hash_password(new)
    db.session.commit()
    return jsonify({"exito": True})

@app.route('/api/loterias', methods=['GET'])
def listar_loterias():
    if 'user' not in session:
        return jsonify({"error": "No autorizado"}), 401
    loterias = Loteria.query.all()
    rol = session['user']['rol']
    resultado = []
    for lot in loterias:
        estado = calcular_estado_loteria(lot)
        res_hoy = Resultado.query.filter_by(loteria_id=lot.id, fecha=date.today()).first()
        numero_hoy = res_hoy.numero_ganador_pick3 if res_hoy else None
        item = {
            "id": lot.id,
            "nombre": lot.nombre,
            "estado_usa": lot.estado_usa,
            "turno": lot.turno,
            "hora_cierre": lot.hora_cierre.strftime('%H:%M'),
            "estado": estado,
            "resultado_hoy": numero_hoy,
            "activa": lot.activa
        }
        if rol in ['admin', 'dueño']:
            total_apostado = db.session.query(db.func.sum(Jugada.monto)).filter(Jugada.loteria_id==lot.id, Jugada.fecha_tiro==date.today()).scalar() or 0
            item["total_apostado"] = float(total_apostado)
        resultado.append(item)
    return jsonify(resultado)

@app.route('/api/loterias/admin', methods=['GET'])
def loterias_admin():
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    loterias = Loteria.query.all()
    resultado = []
    for lot in loterias:
        res_hoy = Resultado.query.filter_by(loteria_id=lot.id, fecha=date.today()).first()
        resultado.append({
            "id": lot.id,
            "nombre": lot.nombre,
            "hora_apertura": lot.hora_apertura.strftime('%H:%M'),
            "hora_cierre": lot.hora_cierre.strftime('%H:%M'),
            "hora_resultado": lot.hora_resultado.strftime('%H:%M'),
            "activa": lot.activa,
            "resultado_pick3": res_hoy.numero_ganador_pick3 if res_hoy else None,
            "resultado_pick4": res_hoy.numero_ganador_pick4 if res_hoy else None
        })
    return jsonify(resultado)

@app.route('/api/loterias/<int:id>', methods=['PUT'])
def actualizar_loteria(id):
    if 'user' not in session or session['user']['rol'] != 'dueño':
        return jsonify({"error": "No autorizado"}), 403
    lot = Loteria.query.get_or_404(id)
    data = request.get_json()
    if 'hora_apertura' in data:
        lot.hora_apertura = datetime.strptime(data['hora_apertura'], '%H:%M').time()
    if 'hora_cierre' in data:
        lot.hora_cierre = datetime.strptime(data['hora_cierre'], '%H:%M').time()
    if 'hora_resultado' in data:
        lot.hora_resultado = datetime.strptime(data['hora_resultado'], '%H:%M').time()
    if 'activa' in data:
        lot.activa = data['activa']
    db.session.commit()
    return jsonify({"exito": True})

@app.route('/api/loterias/<int:id>/cerrar-hoy', methods=['POST'])
def cerrar_loteria_hoy(id):
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    # Simulación: podríamos crear un registro de cierre excepcional
    return jsonify({"exito": True, "mensaje": "Cierre manual registrado (simulado)"})

@app.route('/api/apostar', methods=['POST'])
def apostar():
    if 'user' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.get_json()
    loteria_id = data.get('loteria_id')
    modalidad = data.get('modalidad')
    numero_principal = str(data.get('numero_principal', '')).strip()
    monto = float(data.get('monto', 0))
    numero_parle = data.get('numero_parle', '').strip() if modalidad == 'parle' else None
    tipo_parle_1 = data.get('tipo_parle_1') if modalidad == 'parle' else None
    tipo_parle_2 = data.get('tipo_parle_2') if modalidad == 'parle' else None
    if not loteria_id or not modalidad or not numero_principal or monto <= 0:
        return jsonify({"error": "Datos incompletos"}), 400
    loteria = Loteria.query.get(loteria_id)
    if not loteria or not loteria.activa:
        return jsonify({"error": "Lotería no disponible"}), 400
    estado = calcular_estado_loteria(loteria)
    if estado != 'abierta':
        return jsonify({"error": f"No se puede apostar: la lotería está {estado}"}), 400
    user = Usuario.query.get(session['user']['telefono'])
    if user.saldo < monto:
        return jsonify({"error": "Saldo insuficiente"}), 400
    if modalidad == 'parle':
        cuota = obtener_cuota('parle', tipo_parle_1, tipo_parle_2)
    else:
        cuota = obtener_cuota(modalidad)
    if cuota == 1:
        return jsonify({"error": "Modalidad no válida o cuota no configurada"}), 400
    ganancia_potencial = monto * cuota
    jugada_id = str(uuid.uuid4())[:8]
    nueva = Jugada(
        id=jugada_id,
        telefono=user.telefono,
        loteria_id=loteria_id,
        fecha_tiro=date.today(),
        modalidad=modalidad,
        numero_principal=numero_principal,
        numero_parle=numero_parle,
        tipo_parle_1=tipo_parle_1,
        tipo_parle_2=tipo_parle_2,
        monto=monto,
        cuota_aplicada=cuota,
        ganancia_potencial=ganancia_potencial
    )
    user.saldo -= monto
    trans = Transaccion(telefono=user.telefono, tipo='apuesta', monto=-monto, descripcion=f'{modalidad} ${monto} en {loteria.nombre}')
    db.session.add(trans)
    db.session.add(nueva)
    db.session.commit()
    return jsonify({"exito": True, "id": jugada_id, "saldo_restante": user.saldo})

@app.route('/api/historial', methods=['GET'])
def historial():
    if 'user' not in session:
        return jsonify({"error": "No autorizado"}), 401
    telefono = session['user']['telefono']
    jugadas = Jugada.query.filter_by(telefono=telefono).order_by(Jugada.fecha_apuesta.desc()).all()
    lista = []
    for j in jugadas:
        lot = Loteria.query.get(j.loteria_id)
        lista.append({
            "id": j.id,
            "loteria": lot.nombre if lot else "?",
            "modalidad": j.modalidad,
            "numero": j.numero_principal,
            "monto": j.monto,
            "fecha": j.fecha_apuesta.isoformat(),
            "estado": j.estado,
            "ganancia": j.monto_ganado
        })
    return jsonify(lista)

@app.route('/api/saldo', methods=['GET'])
def saldo():
    if 'user' not in session:
        return jsonify({"error": "No autorizado"}), 401
    user = Usuario.query.get(session['user']['telefono'])
    return jsonify({"saldo": user.saldo})

@app.route('/api/resultado/manual', methods=['POST'])
def resultado_manual():
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    loteria_id = data.get('loteria_id')
    fecha_str = data.get('fecha')
    pick3 = data.get('numero_ganador_pick3')
    pick4 = data.get('numero_ganador_pick4')
    if not loteria_id or not fecha_str or not pick3:
        return jsonify({"error": "Faltan datos"}), 400
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    res = Resultado.query.filter_by(loteria_id=loteria_id, fecha=fecha).first()
    if not res:
        res = Resultado(loteria_id=loteria_id, fecha=fecha, numero_ganador_pick3=pick3, numero_ganador_pick4=pick4, fuente='manual')
        db.session.add(res)
    else:
        res.numero_ganador_pick3 = pick3
        res.numero_ganador_pick4 = pick4
        res.fuente = 'manual'
        res.procesado = False
    db.session.commit()
    procesar_ganadores(loteria_id, fecha, pick3, pick4)
    return jsonify({"exito": True})

@app.route('/api/procesar-ganadores', methods=['POST'])
def reprocesar_ganadores():
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    resultado_id = data.get('resultado_id')
    res = Resultado.query.get(resultado_id)
    if not res:
        return jsonify({"error": "Resultado no encontrado"}), 404
    procesar_ganadores(res.loteria_id, res.fecha, res.numero_ganador_pick3, res.numero_ganador_pick4)
    return jsonify({"exito": True})

@app.route('/api/solicitudes-registro', methods=['GET'])
def listar_solicitudes():
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    solicitudes = SolicitudRegistro.query.filter_by(estado='pendiente').all()
    lista = [{"id": s.id, "nombre": s.nombre, "telefono_whatsapp": s.telefono_whatsapp, "fecha_solicitud": s.fecha_solicitud.isoformat()} for s in solicitudes]
    return jsonify(lista)

@app.route('/api/solicitudes-registro/<int:id>/aprobar', methods=['POST'])
def aprobar_solicitud(id):
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    solicitud = SolicitudRegistro.query.get_or_404(id)
    if solicitud.estado != 'pendiente':
        return jsonify({"error": "La solicitud ya fue procesada"}), 400
    codigo = generar_codigo()
    solicitud.codigo = codigo
    solicitud.codigo_expira = datetime.utcnow() + timedelta(minutes=30)
    solicitud.aprobado_por = session['user']['telefono']
    db.session.commit()
    mensaje = f"Hola {solicitud.nombre} 👋%0A%0ATu código de registro para *La Bolita Cubana* es:%0A%0A*{codigo}*%0A%0AEste código expira en 30 minutos.%0ANo lo compartas con nadie."
    url = f"https://wa.me/{solicitud.telefono_whatsapp}?text={mensaje}"
    return jsonify({"exito": True, "url_whatsapp": url, "codigo": codigo, "expira": solicitud.codigo_expira.isoformat()})

@app.route('/api/solicitudes-registro/<int:id>/rechazar', methods=['POST'])
def rechazar_solicitud(id):
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    solicitud = SolicitudRegistro.query.get_or_404(id)
    solicitud.estado = 'rechazado'
    db.session.commit()
    return jsonify({"exito": True})

@app.route('/api/notificaciones', methods=['GET'])
def obtener_notificaciones():
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    rol = session['user']['rol']
    notis = Notificacion.query.filter_by(destinatario_rol=rol, leida=False).order_by(Notificacion.fecha.desc()).all()
    lista = [{"id": n.id, "tipo": n.tipo, "mensaje": n.mensaje, "fecha": n.fecha.isoformat(), "datos_extra": n.datos_extra} for n in notis]
    return jsonify(lista)

@app.route('/api/notificaciones/<int:id>/leer', methods=['PUT'])
def leer_notificacion(id):
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    noti = Notificacion.query.get_or_404(id)
    noti.leida = True
    db.session.commit()
    return jsonify({"exito": True})

@app.route('/api/usuarios', methods=['GET'])
def listar_usuarios():
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    rol = session['user']['rol']
    if rol == 'dueño':
        usuarios = Usuario.query.all()
    else:
        usuarios = Usuario.query.filter_by(rol='jugador').all()
    lista = [{"telefono": u.telefono, "nombre": u.nombre, "rol": u.rol, "activo": u.activo, "saldo": u.saldo} for u in usuarios]
    return jsonify(lista)

@app.route('/api/usuarios/bloquear', methods=['POST'])
def bloquear_usuario():
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    telefono = data.get('telefono')
    usuario = Usuario.query.get(telefono)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404
    usuario.activo = False
    db.session.commit()
    return jsonify({"exito": True})

@app.route('/api/usuarios/desbloquear', methods=['POST'])
def desbloquear_usuario():
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    telefono = data.get('telefono')
    usuario = Usuario.query.get(telefono)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404
    usuario.activo = True
    db.session.commit()
    return jsonify({"exito": True})

@app.route('/api/recargar', methods=['POST'])
def recargar_saldo():
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    telefono = data.get('telefono')
    monto = float(data.get('monto', 0))
    metodo = data.get('metodo_pago', 'efectivo')
    desc = data.get('descripcion', '')
    if monto <= 0:
        return jsonify({"error": "Monto inválido"}), 400
    usuario = Usuario.query.get(telefono)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404
    usuario.saldo += monto
    trans = Transaccion(telefono=telefono, tipo='recarga', monto=monto, metodo_pago=metodo, descripcion=desc, admin_telefono=session['user']['telefono'])
    db.session.add(trans)
    db.session.commit()
    return jsonify({"exito": True, "nuevo_saldo": usuario.saldo})

@app.route('/api/reportes/diario', methods=['GET'])
def reporte_diario():
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    fecha_str = request.args.get('fecha', date.today().isoformat())
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    resultados = db.session.query(
        Jugada.loteria_id,
        db.func.sum(Jugada.monto).label('total_apostado'),
        db.func.sum(Jugada.monto_ganado).label('total_pagado')
    ).filter(Jugada.fecha_tiro == fecha).group_by(Jugada.loteria_id).all()
    reporte = []
    for r in resultados:
        lot = Loteria.query.get(r.loteria_id)
        reporte.append({
            "loteria": lot.nombre if lot else "?",
            "total_apostado": float(r.total_apostado or 0),
            "total_pagado": float(r.total_pagado or 0),
            "ganancia": float(r.total_apostado or 0) - float(r.total_pagado or 0)
        })
    return jsonify(reporte)

@app.route('/api/administradores', methods=['POST'])
def crear_admin():
    if 'user' not in session or session['user']['rol'] != 'dueño':
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    telefono = data.get('telefono')
    nombre = data.get('nombre')
    password = data.get('password')
    if not telefono or not nombre or not password:
        return jsonify({"error": "Faltan datos"}), 400
    if Usuario.query.get(telefono):
        return jsonify({"error": "El teléfono ya existe"}), 400
    nuevo = Usuario(telefono=telefono, password=hash_password(password), nombre=nombre, rol='admin', activo=True)
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({"exito": True})

@app.route('/api/administradores/<telefono>', methods=['DELETE'])
def eliminar_admin(telefono):
    if 'user' not in session or session['user']['rol'] != 'dueño':
        return jsonify({"error": "No autorizado"}), 403
    admin = Usuario.query.get(telefono)
    if not admin or admin.rol != 'admin':
        return jsonify({"error": "No es un administrador"}), 404
    admin.rol = 'jugador'
    db.session.commit()
    return jsonify({"exito": True})

@app.route('/api/cuotas', methods=['GET'])
def listar_cuotas():
    if 'user' not in session or session['user']['rol'] != 'dueño':
        return jsonify({"error": "No autorizado"}), 403
    cuotas = Cuota.query.all()
    return jsonify([{"modalidad": c.modalidad, "multiplicador": c.multiplicador} for c in cuotas])

@app.route('/api/cuotas', methods=['PUT'])
def actualizar_cuota():
    if 'user' not in session or session['user']['rol'] != 'dueño':
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    modalidad = data.get('modalidad')
    multiplicador = float(data.get('multiplicador'))
    cuota = Cuota.query.filter_by(modalidad=modalidad).first()
    if not cuota:
        return jsonify({"error": "Modalidad no encontrada"}), 404
    cuota.multiplicador = multiplicador
    cuota.actualizado_por = session['user']['telefono']
    cuota.fecha_actualizacion = datetime.utcnow()
    db.session.commit()
    return jsonify({"exito": True})

@app.route('/api/admin/usuario/<telefono>/auditoria', methods=['GET'])
def auditoria_usuario(telefono):
    if 'user' not in session or session['user']['rol'] not in ['admin', 'dueño']:
        return jsonify({"error": "No autorizado"}), 403
    usuario = Usuario.query.get(telefono)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404
    sesiones = Sesion.query.filter_by(telefono=telefono).order_by(Sesion.fecha_inicio.desc()).limit(10).all()
    alertas = AlertaSeguridad.query.filter_by(telefono=telefono, resuelta=False).all()
    total_apostado = db.session.query(db.func.sum(Jugada.monto)).filter_by(telefono=telefono, estado='pendiente').scalar() or 0
    total_ganado = db.session.query(db.func.sum(Jugada.monto_ganado)).filter_by(telefono=telefono, estado='ganada').scalar() or 0
    return jsonify({
        "usuario": {"nombre": usuario.nombre, "telefono": usuario.telefono, "saldo": usuario.saldo, "activo": usuario.activo, "fecha_registro": usuario.fecha_registro.isoformat()},
        "estadisticas": {"total_apostado": float(total_apostado), "total_ganado": float(total_ganado), "total_sesiones": usuario.total_sesiones, "tiempo_total_minutos": usuario.tiempo_total_minutos},
        "sesiones": [{"ip": s.ip_address, "inicio": s.fecha_inicio.isoformat(), "fin": s.fecha_fin.isoformat() if s.fecha_fin else None, "duracion": s.duracion_minutos} for s in sesiones],
        "alertas": [{"tipo": a.tipo, "descripcion": a.descripcion, "nivel": a.nivel} for a in alertas]
    })

# ------------------------ INICIALIZACIÓN DE BASE DE DATOS ------------------------
with app.app_context():
    db.create_all()
    # Insertar cuotas base
    cuotas_base = [
        ('centena', 150, 'Pick 3 exacto'),
        ('fijo', 70, 'Pick 3 últimos 2 dígitos exactos'),
        ('corrido_p3', 35, 'Pick 3 2 dígitos cualquier orden'),
        ('corrido_p4_ab', 35, 'Pick 4 primeros 2 corrido'),
        ('corrido_p4_cd', 35, 'Pick 4 últimos 2 corrido'),
        ('parle_ff', 400, 'Parle fijo+fijo'),
        ('parle_fc', 150, 'Parle fijo+corrido'),
        ('parle_cc', 80, 'Parle corrido+corrido')
    ]
    for mod, mult, desc in cuotas_base:
        if not Cuota.query.filter_by(modalidad=mod).first():
            db.session.add(Cuota(modalidad=mod, multiplicador=mult, descripcion=desc))
    # Insertar loterías base
    loterias_base = [
        ('Georgia Día', 'Georgia', 'dia', '08:00', '12:00', '12:29'),
        ('New York Día', 'New York', 'dia', '08:00', '14:00', '14:30'),
        ('Florida Día', 'Florida', 'dia', '08:00', '13:00', '13:30'),
        ('New Jersey Día', 'New Jersey', 'dia', '08:00', '12:29', '12:59'),
        ('Georgia Noche', 'Georgia', 'noche', '15:00', '18:29', '18:59'),
        ('Florida Noche', 'Florida', 'noche', '15:00', '21:15', '21:45'),
        ('New York Noche', 'New York', 'noche', '15:00', '22:00', '22:30'),
        ('New Jersey Noche', 'New Jersey', 'noche', '15:00', '22:27', '22:57')
    ]
    for nombre, estado, turno, apertura, cierre, resultado in loterias_base:
        if not Loteria.query.filter_by(nombre=nombre).first():
            lot = Loteria(
                nombre=nombre,
                estado_usa=estado,
                turno=turno,
                hora_apertura=datetime.strptime(apertura, '%H:%M').time(),
                hora_cierre=datetime.strptime(cierre, '%H:%M').time(),
                hora_resultado=datetime.strptime(resultado, '%H:%M').time()
            )
            db.session.add(lot)
    # Crear dueño por defecto
    if not Usuario.query.filter_by(rol='dueño').first():
        dueño = Usuario(telefono='5550000000', password=hash_password('admin123'), nombre='Dueño', rol='dueño', activo=True)
        db.session.add(dueño)
    db.session.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
