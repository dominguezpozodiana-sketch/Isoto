from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(15), unique=True, nullable=False)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    contrasena = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), default='usuario')
    fr = db.Column(db.DateTime, default=datetime.utcnow)   # fecha registro
    ui = db.Column(db.DateTime, nullable=True)             # último inicio
    ta = db.Column(db.Integer, default=0)                  # tiempo activo (segundos)
    ti = db.Column(db.Integer, default=0)                  # tiempo inactivo (segundos)
    estado = db.Column(db.String(20), default='activo')

    def get_id(self):
        return str(self.id)

class AdminCreador(UserMixin, db.Model):
    __tablename__ = 'registro_admin_creador'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(15), unique=True, nullable=False)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    contrasena = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False)   # 'admin' o 'creador'
    estado = db.Column(db.String(20), default='activo')

    def get_id(self):
        return str(self.id)

class SolicitudRegistro(db.Model):
    __tablename__ = 'solicitud_registro'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(15), nullable=False)
    nombre = db.Column(db.String(80), nullable=False)
    contrasena = db.Column(db.String(200), nullable=False)
    codigo_otp = db.Column(db.String(6), nullable=False)
    tiempo = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente/aceptado/negado
    
class ResultadoLoteria(db.Model):
    __tablename__ = 'resultados_loteria'
    id = db.Column(db.Integer, primary_key=True)
    estado = db.Column(db.String(30), nullable=False)
    juego = db.Column(db.String(10), nullable=False)
    sorteo = db.Column(db.String(10), nullable=False)
    numeros = db.Column(db.String(30), nullable=False)
    fireball = db.Column(db.String(2), nullable=True)
    fecha_sorteo = db.Column(db.DateTime, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)