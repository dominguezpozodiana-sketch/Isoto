import os
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.pool import NullPool
from models import db, Usuario, AdminCreador, SolicitudRegistro

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-super-segura-cambiar-en-produccion')

# ================= CONFIGURACIÓN DE BASE DE DATOS =================
TURSO_URL = os.environ.get('TURSO_DATABASE_URL')
TURSO_TOKEN = os.environ.get('TURSO_AUTH_TOKEN')

if TURSO_URL and TURSO_TOKEN:
    try:
        from libsql_experimental import create_client
        def turso_creator():
            return create_client(TURSO_URL, auth_token=TURSO_TOKEN)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'creator': turso_creator,
            'poolclass': NullPool,
        }
        print("✅ Conectado a Turso (experimental)")
    except ImportError:
        print("⚠️ libsql_experimental no instalado, usando SQLite local")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loteria.db'
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
else:
    # Fallback a SQLite local (para desarrollo)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loteria.db'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    user = Usuario.query.get(int(user_id))
    if user:
        return user
    return AdminCreador.query.get(int(user_id))

# ------------------- RUTAS PÚBLICAS -------------------
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/ping')
def ping():
    return 'OK', 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        numero = request.form['numero'].strip()
        if not numero.startswith('+53'):
            numero = '+53' + numero
        contrasena = request.form['contrasena']
        
        user = Usuario.query.filter_by(numero=numero).first()
        if user and check_password_hash(user.contrasena, contrasena):
            if user.estado == 'bloqueado':
                flash('Usuario bloqueado', 'error')
                return redirect(url_for('login'))
            user.ui = datetime.utcnow()
            db.session.commit()
            login_user(user)
            return redirect(url_for('user_dashboard'))
        
        admin = AdminCreador.query.filter_by(numero=numero).first()
        if admin and check_password_hash(admin.contrasena, contrasena):
            if admin.estado == 'bloqueado':
                flash('Cuenta bloqueada', 'error')
                return redirect(url_for('login'))
            login_user(admin)
            if admin.rol == 'creador':
                return redirect(url_for('creator_dashboard'))
            else:
                return redirect(url_for('admin_dashboard'))
        
        flash('Número o contraseña incorrectos', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        numero = request.form['numero'].strip()
        if not numero.startswith('+53'):
            numero = '+53' + numero
        nombre = request.form['nombre'].strip()
        contrasena_plana = request.form['contrasena']
        
        # Verificar duplicados en usuarios existentes
        if Usuario.query.filter_by(numero=numero).first() or AdminCreador.query.filter_by(numero=numero).first():
            flash('El número ya está registrado', 'error')
            return redirect(url_for('register'))
        if Usuario.query.filter_by(nombre=nombre).first() or AdminCreador.query.filter_by(nombre=nombre).first():
            flash('El nombre de usuario ya existe', 'error')
            return redirect(url_for('register'))
        
        # Verificar solicitud pendiente o aceptada
        solicitud_existente = SolicitudRegistro.query.filter(
            (SolicitudRegistro.numero == numero) | (SolicitudRegistro.nombre == nombre),
            SolicitudRegistro.estado.in_(['pendiente', 'aceptado'])
        ).first()
        if solicitud_existente:
            if solicitud_existente.estado == 'pendiente':
                flash('Ya tienes una solicitud de registro pendiente.', 'warning')
            else:
                flash('Tu registro ya fue aceptado. Por favor inicia sesión.', 'info')
            return redirect(url_for('register'))
        
        otp = f"{random.randint(100000, 999999)}"
        nueva_solicitud = SolicitudRegistro(
            numero=numero,
            nombre=nombre,
            contrasena=generate_password_hash(contrasena_plana),
            codigo_otp=otp,
            tiempo=datetime.utcnow(),
            estado='pendiente'
        )
        db.session.add(nueva_solicitud)
        db.session.commit()
        session['solicitud_id'] = nueva_solicitud.id
        flash('Solicitud enviada. Espera el código OTP del administrador', 'info')
        return redirect(url_for('validate_otp'))
    return render_template('register.html')

@app.route('/validate_otp', methods=['GET', 'POST'])
def validate_otp():
    solicitud_id = session.get('solicitud_id')
    if not solicitud_id:
        flash('No hay solicitud activa', 'error')
        return redirect(url_for('register'))
    
    solicitud = SolicitudRegistro.query.get(solicitud_id)
    if not solicitud or solicitud.estado != 'pendiente':
        flash('Solicitud no válida o ya procesada', 'error')
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        otp_ingresado = request.form['otp']
        tiempo_limite = solicitud.tiempo + timedelta(minutes=5)
        if datetime.utcnow() > tiempo_limite:
            nuevo_otp = f"{random.randint(100000, 999999)}"
            solicitud.codigo_otp = nuevo_otp
            solicitud.tiempo = datetime.utcnow()
            db.session.commit()
            flash('El código ha expirado. Se ha generado uno nuevo.', 'warning')
            return redirect(url_for('validate_otp'))
        
        if otp_ingresado == solicitud.codigo_otp:
            nuevo_usuario = Usuario(
                numero=solicitud.numero,
                nombre=solicitud.nombre,
                contrasena=solicitud.contrasena,
                rol='usuario',
                fr=datetime.utcnow(),
                estado='activo'
            )
            db.session.add(nuevo_usuario)
            solicitud.estado = 'aceptado'
            db.session.commit()
            flash('Registro exitoso. Ahora puedes iniciar sesión', 'success')
            session.pop('solicitud_id', None)
            return redirect(url_for('login'))
        else:
            flash('Código incorrecto', 'error')
    return render_template('validate_otp.html')

# ------------------- RUTAS PRIVADAS -------------------
@app.route('/creator')
@login_required
def creator_dashboard():
    # Parche temporal para pruebas (creador por número)
    if current_user.numero == '+5351643108':
        current_user.rol = 'creador'
    if current_user.rol != 'creador':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))
    solicitudes = SolicitudRegistro.query.filter_by(estado='pendiente').all()
    return render_template('creator_dashboard.html', solicitudes=solicitudes)

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.rol != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))
    solicitudes = SolicitudRegistro.query.filter_by(estado='pendiente').all()
    return render_template('admin_dashboard.html', solicitudes=solicitudes)

@app.route('/enviar_otp/<int:solicitud_id>')
@login_required
def enviar_otp(solicitud_id):
    if current_user.numero == '+5351643108':
        current_user.rol = 'creador'
    if current_user.rol not in ['creador', 'admin']:
        flash('No autorizado', 'error')
        return redirect(url_for('login'))
    solicitud = SolicitudRegistro.query.get_or_404(solicitud_id)
    flash(f"Código OTP para {solicitud.nombre}: {solicitud.codigo_otp} (válido por 5 min)", 'info')
    if current_user.rol == 'creador':
        return redirect(url_for('creator_dashboard'))
    else:
        return redirect(url_for('admin_dashboard'))

@app.route('/user')
@login_required
def user_dashboard():
    if current_user.rol != 'usuario':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))
    return render_template('usuario/user_loteria.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ------------------- CREAR TABLAS Y USUARIOS POR DEFECTO -------------------
with app.app_context():
    db.create_all()
    # Crear creador por defecto si no existe
    if not AdminCreador.query.filter_by(rol='creador').first():
        creador = AdminCreador(
            numero='+5300000001',
            nombre='ElCreador',
            contrasena=generate_password_hash('creador123'),
            rol='creador',
            estado='activo'
        )
        db.session.add(creador)
    # Crear admin por defecto si no existe
    if not AdminCreador.query.filter_by(rol='admin').first():
        admin = AdminCreador(
            numero='+5300000002',
            nombre='Admin1',
            contrasena=generate_password_hash('admin123'),
            rol='admin',
            estado='activo'
        )
        db.session.add(admin)
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)