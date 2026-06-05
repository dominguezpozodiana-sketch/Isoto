import os

class Config:
    """
    Configuración de producción estricta.
    Fuerza la existencia de variables de entorno para evitar brechas de seguridad.
    """
    # Si SECRET_KEY no está en el entorno, lanza un KeyError inmediato protegiendo la app
    SECRET_KEY = os.environ['SECRET_KEY']
    
    # URI de la base de datos relacional
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://usuario:password@localhost:5432/la_bolita')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración estricta de Cookies de Sesión para mitigar robo de identidad
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True  # Requiere HTTPS en producción
    SESSION_COOKIE_SAMESITE = 'Lax'