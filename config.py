import os

class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "cambiar-esta-clave-en-produccion"
    )

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True

    # Railway funciona detrás de HTTPS
    SESSION_COOKIE_SECURE = True

    SESSION_COOKIE_SAMESITE = "Lax"
