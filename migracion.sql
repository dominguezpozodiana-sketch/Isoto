-- Crear tablas (si no existen)
CREATE TABLE IF NOT EXISTS usuarios ( telefono TEXT PRIMARY KEY, password TEXT NOT NULL, nombre TEXT NOT NULL, rol TEXT NOT NULL, activo BOOLEAN DEFAULT TRUE, saldo FLOAT DEFAULT 0, fecha_registro TIMESTAMP, ultimo_login TIMESTAMP, total_sesiones INTEGER DEFAULT 0, tiempo_total_minutos INTEGER DEFAULT 0, ip_registro TEXT, admin_id TEXT REFERENCES usuarios(telefono) );
CREATE TABLE IF NOT EXISTS loterias ( id SERIAL PRIMARY KEY, nombre TEXT NOT NULL, estado_usa TEXT NOT NULL, turno TEXT NOT NULL, hora_apertura TIME NOT NULL, hora_cierre TIME NOT NULL, hora_resultado TIME NOT NULL, zona_horaria TEXT DEFAULT 'US/Eastern', activa BOOLEAN DEFAULT TRUE );
CREATE TABLE IF NOT EXISTS jugadas ( id TEXT PRIMARY KEY, telefono TEXT REFERENCES usuarios(telefono) NOT NULL, loteria_id INTEGER REFERENCES loterias(id) NOT NULL, fecha_tiro DATE NOT NULL, modalidad TEXT NOT NULL, numero_principal TEXT NOT NULL, numero_parle TEXT, tipo_parle_1 TEXT, tipo_parle_2 TEXT, monto FLOAT NOT NULL, cuota_aplicada FLOAT NOT NULL, ganancia_potencial FLOAT NOT NULL, fecha_apuesta TIMESTAMP DEFAULT NOW(), estado TEXT DEFAULT 'pendiente', monto_ganado FLOAT DEFAULT 0 );
CREATE TABLE IF NOT EXISTS resultados ( id SERIAL PRIMARY KEY, loteria_id INTEGER REFERENCES loterias(id) NOT NULL, fecha DATE NOT NULL, numero_ganador_pick3 TEXT(3), numero_ganador_pick4 TEXT(4), fuente TEXT DEFAULT 'manual', procesado BOOLEAN DEFAULT FALSE, fecha_procesado TIMESTAMP );
CREATE TABLE IF NOT EXISTS transacciones ( id SERIAL PRIMARY KEY, telefono TEXT REFERENCES usuarios(telefono), tipo TEXT NOT NULL, monto FLOAT NOT NULL, descripcion TEXT, metodo_pago TEXT, admin_telefono TEXT REFERENCES usuarios(telefono), fecha TIMESTAMP DEFAULT NOW() );
CREATE TABLE IF NOT EXISTS solicitudes_registro ( id SERIAL PRIMARY KEY, nombre TEXT NOT NULL, telefono_whatsapp TEXT UNIQUE NOT NULL, codigo TEXT(6), codigo_expira TIMESTAMP, estado TEXT DEFAULT 'pendiente', fecha_solicitud TIMESTAMP DEFAULT NOW(), aprobado_por TEXT REFERENCES usuarios(telefono) );
CREATE TABLE IF NOT EXISTS notificaciones ( id SERIAL PRIMARY KEY, destinatario_rol TEXT NOT NULL, tipo TEXT NOT NULL, mensaje TEXT NOT NULL, leida BOOLEAN DEFAULT FALSE, fecha TIMESTAMP DEFAULT NOW(), datos_extra TEXT );
CREATE TABLE IF NOT EXISTS sesiones ( id SERIAL PRIMARY KEY, telefono TEXT REFERENCES usuarios(telefono) NOT NULL, ip_address TEXT NOT NULL, fecha_inicio TIMESTAMP DEFAULT NOW(), fecha_fin TIMESTAMP, duracion_minutos INTEGER DEFAULT 0 );
CREATE TABLE IF NOT EXISTS intentos_login ( id SERIAL PRIMARY KEY, telefono TEXT, ip_address TEXT NOT NULL, fecha TIMESTAMP DEFAULT NOW(), exitoso BOOLEAN DEFAULT FALSE );
CREATE TABLE IF NOT EXISTS alertas_seguridad ( id SERIAL PRIMARY KEY, telefono TEXT REFERENCES usuarios(telefono) NOT NULL, tipo TEXT NOT NULL, descripcion TEXT NOT NULL, nivel TEXT DEFAULT 'media', resuelta BOOLEAN DEFAULT FALSE, fecha TIMESTAMP DEFAULT NOW() );
CREATE TABLE IF NOT EXISTS cuotas ( id SERIAL PRIMARY KEY, modalidad TEXT UNIQUE NOT NULL, multiplicador FLOAT NOT NULL, descripcion TEXT, actualizado_por TEXT, fecha_actualizacion TIMESTAMP DEFAULT NOW() );

-- Insertar cuotas iniciales
INSERT INTO cuotas (modalidad, multiplicador, descripcion) VALUES
('centena', 150, 'Pick 3 exacto'),
('fijo', 70, 'Pick 3 últimos 2 dígitos exactos'),
('corrido_p3', 35, 'Pick 3 2 dígitos cualquier orden'),
('corrido_p4_ab', 35, 'Pick 4 primeros 2 corrido'),
('corrido_p4_cd', 35, 'Pick 4 últimos 2 corrido'),
('parle_ff', 400, 'Parle fijo+fijo'),
('parle_fc', 150, 'Parle fijo+corrido'),
('parle_cc', 80, 'Parle corrido+corrido')
ON CONFLICT (modalidad) DO NOTHING;

-- Insertar loterías base
INSERT INTO loterias (nombre, estado_usa, turno, hora_apertura, hora_cierre, hora_resultado) VALUES
('Georgia Día', 'Georgia', 'dia', '08:00', '12:00', '12:29'),
('New York Día', 'New York', 'dia', '08:00', '14:00', '14:30'),
('Florida Día', 'Florida', 'dia', '08:00', '13:00', '13:30'),
('New Jersey Día', 'New Jersey', 'dia', '08:00', '12:29', '12:59'),
('Georgia Noche', 'Georgia', 'noche', '15:00', '18:29', '18:59'),
('Florida Noche', 'Florida', 'noche', '15:00', '21:15', '21:45'),
('New York Noche', 'New York', 'noche', '15:00', '22:00', '22:30'),
('New Jersey Noche', 'New Jersey', 'noche', '15:00', '22:27', '22:57')
ON CONFLICT (id) DO NOTHING;
