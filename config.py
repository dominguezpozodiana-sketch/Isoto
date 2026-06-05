import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-key-cambiar-en-produccion')
    # Ajuste automático para compatibilidad con Railway / PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://localhost/la_bolita').replace('postgres://', 'postgresql://')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
