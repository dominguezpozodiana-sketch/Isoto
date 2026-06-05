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

class Jugada(db.Model):
    __tablename__ = 'jugadas'
    
    id = db.Column(db.String, primary_key=True)
    telefono = db.Column(db.String, db.ForeignKey('usuarios.telefono'), nullable=False)
    loteria_id = db.Column(db.Integer, nullable=False)
    modalidad = db.Column(db.String, nullable=False) # 'centena', 'fijo', etc.
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
