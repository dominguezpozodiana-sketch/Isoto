from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    telefono = db.Column(db.String(20), primary_key=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), default='usuario', nullable=False, index=True)
    saldo = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    jugadas = db.relationship('Jugada', backref='usuario', cascade="all, delete-orphan", lazy=True)
    transacciones = db.relationship('Transaccion', backref='usuario', cascade="all, delete-orphan", lazy=True)


class SolicitudRegistro(db.Model):
    __tablename__ = 'solicitudes_registro'
    
    id = db.Column(db.Integer, primary_key=True)
    telefono_whatsapp = db.Column(db.String(20), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    codigo_otp = db.Column(db.String(6), nullable=False)
    intentos_otp = db.Column(db.Integer, default=0, nullable=False)
    estado = db.Column(db.String(20), default='pendiente', nullable=False, index=True)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_expiracion = db.Column(db.DateTime, nullable=False) # Control temporal de OTP (Punto 4)
    
    aprobado_por = db.Column(db.String(20), db.ForeignKey('usuarios.telefono', ondelete='SET NULL'), nullable=True)


class Loteria(db.Model):
    __tablename__ = 'loterias'
    
    id = db.Column(db.String(50), primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    turno = db.Column(db.String(20), nullable=False)
    hora_apertura = db.Column(db.Time, nullable=False)
    hora_cierre = db.Column(db.Time, nullable=False)
    activa = db.Column(db.Boolean, default=True, nullable=False)

    jugadas = db.relationship('Jugada', backref='loteria', cascade="all, delete-orphan", lazy=True)
    resultados = db.relationship('Resultado', backref='loteria', cascade="all, delete-orphan", lazy=True)


class Jugada(db.Model):
    __tablename__ = 'jugadas'
    
    id = db.Column(db.String(32), primary_key=True)
    telefono = db.Column(db.String(20), db.ForeignKey('usuarios.telefono', ondelete='CASCADE'), nullable=False, index=True)
    loteria_id = db.Column(db.String(50), db.ForeignKey('loterias.id', ondelete='CASCADE'), nullable=False, index=True)
    modalidad = db.Column(db.String(20), nullable=False)
    numero_principal = db.Column(db.String(2), nullable=False)
    numero_parle = db.Column(db.String(2), nullable=True)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    cuota_aplicada = db.Column(db.Numeric(10, 2), nullable=False)
    ganancia_potencial = db.Column(db.Numeric(10, 2), nullable=False)
    monto_ganado = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    estado = db.Column(db.String(20), default='pendiente', nullable=False, index=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class Resultado(db.Model):
    __tablename__ = 'resultados'
    
    id = db.Column(db.Integer, primary_key=True)
    loteria_id = db.Column(db.String(50), db.ForeignKey('loterias.id', ondelete='CASCADE'), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    pick3 = db.Column(db.String(3), nullable=False)
    pick4 = db.Column(db.String(4), nullable=False)
    fuente = db.Column(db.String(20), default='manual')
    procesado = db.Column(db.Boolean, default=False)
    procesado_en = db.Column(db.DateTime, nullable=True)
    ingresado_por = db.Column(db.String(20), db.ForeignKey('usuarios.telefono', ondelete='SET NULL'), nullable=True)

    __table_args__ = (
        UniqueConstraint('loteria_id', 'fecha', name='uq_loteria_fecha'),
    )


class Transaccion(db.Model):
    """Modelo completo de movimientos financieros (Punto 8 garantizado)"""
    __tablename__ = 'transacciones'
    
    id = db.Column(db.Integer, primary_key=True)
    telefono = db.Column(db.String(20), db.ForeignKey('usuarios.telefono', ondelete='CASCADE'), nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False) # 'recarga', 'apuesta', 'premio', 'retiro'
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    balance_posterior = db.Column(db.Numeric(10, 2), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    referencia_id = db.Column(db.String(50), nullable=True)
    ejecutado_por = db.Column(db.String(20), db.ForeignKey('usuarios.telefono', ondelete='SET NULL'), nullable=True)