from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    telefono = db.Column(db.String, primary_key=True)
    telefono_whatsapp = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    nombre = db.Column(db.String, nullable=False)
    rol = db.Column(db.String, nullable=False, default='usuario') # 'dueno', 'admin', 'usuario'
    estado = db.Column(db.String, default='pendiente')          # 'pendiente', 'activo', 'bloqueado'
    saldo = db.Column(db.Float, default=0.0)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)
    
    jugadas = db.relationship('Jugada', backref='jugador', lazy=True)

class SolicitudRegistro(db.Model):
    __tablename__ = 'solicitudes_registro'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    telefono_whatsapp = db.Column(db.String, unique=True, nullable=False)
    codigo = db.Column(db.String, nullable=True)
    codigo_expira = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String, default='pendiente') # 'pendiente', 'aprobado', 'rechazado'
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    aprobado_por = db.Column(db.String, nullable=True)

class Loteria(db.Model):
    __tablename__ = 'loterias'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    estado_usa = db.Column(db.String, nullable=False)
    turno = db.Column(db.String, nullable=False)
    hora_apertura = db.Column(db.Time, nullable=False)
    hora_cierre = db.Column(db.Time, nullable=False)
    hora_resultado = db.Column(db.Time, nullable=False)
    zona_horaria = db.Column(db.String, default='US/Eastern')
    activa = db.Column(db.Boolean, default=True)
    pick_type = db.Column(db.String, default='ambos')

class Resultado(db.Model):
    __tablename__ = 'resultados'
    
    id = db.Column(db.Integer, primary_key=True)
    loteria_id = db.Column(db.Integer, db.ForeignKey('loterias.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    pick3 = db.Column(db.String, nullable=True)
    pick4 = db.Column(db.String, nullable=True)
    fuente = db.Column(db.String, default='manual')
    procesado = db.Column(db.Boolean, default=False)
    procesado_en = db.Column(db.DateTime)
    ingresado_por = db.Column(db.String)

class Jugada(db.Model):
    __tablename__ = 'jugadas'
    
    id = db.Column(db.String, primary_key=True)
    telefono = db.Column(db.String, db.ForeignKey('usuarios.telefono'), nullable=False)
    loteria_id = db.Column(db.Integer, db.ForeignKey('loterias.id'), nullable=False)
    modalidad = db.Column(db.String, nullable=False) 
    numero_principal = db.Column(db.String, nullable=False)
    numero_parle = db.Column(db.String, nullable=True)
    tipo_parle_1 = db.Column(db.String, nullable=True)
    tipo_parle_2 = db.Column(db.String, nullable=True)
    monto = db.Column(db.Float, nullable=False)
    cuota_aplicada = db.Column(db.Float, nullable=False)
    ganancia_potencial = db.Column(db.Float)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String, default='pendiente') # 'pendiente', 'ganada', 'perdida'
    monto_ganado = db.Column(db.Float, default=0.0)

class Transaccion(db.Model):
    __tablename__ = 'transacciones'
    
    id = db.Column(db.Integer, primary_key=True)
    telefono = db.Column(db.String, db.ForeignKey('usuarios.telefono'), nullable=False)
    tipo = db.Column(db.String, nullable=False)          # 'credito' (carga saldo), 'debito' (cobra cliente)
    monto = db.Column(db.Float, nullable=False)
    metodo = db.Column(db.String, nullable=False)         # 'efectivo', 'zelle', 'pago_movil', 'transferencia'
    descripcion = db.Column(db.String, nullable=True)
    registrado_por = db.Column(db.String, nullable=False)    # Teléfono del administrador en sesión
    fecha = db.Column(db.DateTime, default=datetime.utcnow)