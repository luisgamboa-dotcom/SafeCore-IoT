CREATE DATABASE IF NOT EXISTS safecore_iot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE safecore_iot;

-- 1 Catálogos base
CREATE TABLE IF NOT EXISTS organizaciones (
id_organizacion INT AUTO_INCREMENT PRIMARY KEY,
nombre VARCHAR(100) NOT NULL,
descripcion TEXT,
fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS usuarios_estados (
id_usuario_estado INT AUTO_INCREMENT PRIMARY KEY,
nombre VARCHAR(50) NOT NULL UNIQUE
);
INSERT IGNORE INTO usuarios_estados (id_usuario_estado, nombre) VALUES (1, 'Activo'), (2, 'Inactivo');
CREATE TABLE IF NOT EXISTS catalogo_roles (
id_catalogo_rol INT AUTO_INCREMENT PRIMARY KEY,
nombre_rol VARCHAR(50) NOT NULL UNIQUE,
descripcion TEXT
);
CREATE TABLE IF NOT EXISTS direcciones (
id_direccion INT AUTO_INCREMENT PRIMARY KEY,
calle VARCHAR(200) NOT NULL,
numero VARCHAR(10),
ciudad VARCHAR(100) NOT NULL,
region VARCHAR(100),
codigo_postal VARCHAR(20)
);
CREATE TABLE IF NOT EXISTS modelos_dispositivo (
id_modelo INT AUTO_INCREMENT PRIMARY KEY,
nombre_modelo VARCHAR(100) NOT NULL UNIQUE,
fabricante VARCHAR(100),
descripcion TEXT
);
CREATE TABLE IF NOT EXISTS estados_dispositivo (
id_estado_dispositivo INT AUTO_INCREMENT PRIMARY KEY,
nombre VARCHAR(50) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS magnitudes (
id_magnitud INT AUTO_INCREMENT PRIMARY KEY,
nombre VARCHAR(50) NOT NULL UNIQUE,
unidad VARCHAR(20) NOT NULL,
simbolo VARCHAR(10)
);
CREATE TABLE IF NOT EXISTS tipos_alerta (
id_tipo_alerta INT AUTO_INCREMENT PRIMARY KEY,
nombre VARCHAR(50) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS estados_alerta (
id_estado_alerta INT AUTO_INCREMENT PRIMARY KEY,
nombre VARCHAR(50) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS canales_notificacion (
id_canal INT AUTO_INCREMENT PRIMARY KEY,
nombre VARCHAR(50) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS tipos_mantenimiento (
id_tipo_mantenimiento INT AUTO_INCREMENT PRIMARY KEY,
nombre VARCHAR(50) NOT NULL UNIQUE
);
-- 2 Usuarios
CREATE TABLE IF NOT EXISTS usuarios (
id_usuario INT AUTO_INCREMENT PRIMARY KEY,
email VARCHAR(254) NOT NULL UNIQUE,
password_hash VARCHAR(254) NOT NULL,
nombre VARCHAR(50) NOT NULL,
apellido VARCHAR(50),
telefono VARCHAR(20),
fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
id_usuario_estado INT NOT NULL DEFAULT 1,
id_organizacion INT NULL,
CONSTRAINT fk_usuarios_estado FOREIGN KEY (id_usuario_estado)
REFERENCES usuarios_estados(id_usuario_estado) ON DELETE RESTRICT,
CONSTRAINT fk_usuarios_org FOREIGN KEY (id_organizacion)
REFERENCES organizaciones(id_organizacion) ON DELETE RESTRICT,
INDEX idx_usuarios_org (id_organizacion),
INDEX idx_usuarios_estado (id_usuario_estado)
);
CREATE TABLE IF NOT EXISTS usuarios_roles (
id_usuario INT NOT NULL,
id_catalogo_rol INT NOT NULL,
PRIMARY KEY (id_usuario, id_catalogo_rol),
CONSTRAINT fk_ur_usuario FOREIGN KEY (id_usuario)
REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
CONSTRAINT fk_ur_rol FOREIGN KEY (id_catalogo_rol)
REFERENCES catalogo_roles(id_catalogo_rol) ON DELETE RESTRICT
);
-- 3 Sitios
CREATE TABLE IF NOT EXISTS instalaciones (
id_instalacion INT AUTO_INCREMENT PRIMARY KEY,
nombre VARCHAR(100) NOT NULL,
descripcion TEXT,
fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
id_direccion INT NOT NULL,
id_organizacion INT NULL,
CONSTRAINT fk_inst_dir FOREIGN KEY (id_direccion)
REFERENCES direcciones(id_direccion) ON DELETE RESTRICT,
CONSTRAINT fk_inst_org FOREIGN KEY (id_organizacion)
REFERENCES organizaciones(id_organizacion) ON DELETE RESTRICT,
INDEX idx_inst_org (id_organizacion)
);
CREATE TABLE IF NOT EXISTS zonas (
id_zona INT AUTO_INCREMENT PRIMARY KEY,
nombre VARCHAR(100) NOT NULL,
descripcion TEXT,
id_instalacion INT NOT NULL,
CONSTRAINT fk_zona_inst FOREIGN KEY (id_instalacion)
REFERENCES instalaciones(id_instalacion) ON DELETE CASCADE,
INDEX idx_zona_inst (id_instalacion)
);
-- 4 Dispositivos y sensores
CREATE TABLE IF NOT EXISTS dispositivos (
id_dispositivo INT AUTO_INCREMENT PRIMARY KEY,
codigo_serial VARCHAR(100) NOT NULL UNIQUE,
nombre VARCHAR(100) NOT NULL,
firmware_version VARCHAR(50),
fecha_alta TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
fecha_instalacion TIMESTAMP NULL,
ultima_comunicacion TIMESTAMP NULL,
activo TINYINT(1) NOT NULL DEFAULT 1,
id_modelo INT NOT NULL,
id_estado_dispositivo INT NOT NULL,
id_zona INT NOT NULL,
CONSTRAINT fk_dev_modelo FOREIGN KEY (id_modelo)
REFERENCES modelos_dispositivo(id_modelo) ON DELETE RESTRICT,
CONSTRAINT fk_dev_estado FOREIGN KEY (id_estado_dispositivo)
REFERENCES estados_dispositivo(id_estado_dispositivo) ON DELETE RESTRICT,
CONSTRAINT fk_dev_zona FOREIGN KEY (id_zona)
REFERENCES zonas(id_zona) ON DELETE RESTRICT,
INDEX idx_dev_zona (id_zona),
INDEX idx_dev_modelo (id_modelo),
INDEX idx_dev_lastseen (ultima_comunicacion)
);
CREATE TABLE IF NOT EXISTS sensores (
id_sensor INT AUTO_INCREMENT PRIMARY KEY,
frecuencia_muestreo INT,
offset_calibracion DECIMAL(10,4),
habilitado TINYINT(1) NOT NULL DEFAULT 1,
fecha_instalacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
fecha_retiro TIMESTAMP NULL,
id_dispositivo INT NOT NULL,
CONSTRAINT fk_sens_dev FOREIGN KEY (id_dispositivo)
REFERENCES dispositivos(id_dispositivo) ON DELETE CASCADE,
INDEX idx_sens_dev (id_dispositivo)
);
CREATE TABLE IF NOT EXISTS sensores_magnitudes (
id_sensor INT NOT NULL,
id_magnitud INT NOT NULL,
PRIMARY KEY (id_sensor, id_magnitud),
CONSTRAINT fk_sm_sens FOREIGN KEY (id_sensor)
REFERENCES sensores(id_sensor) ON DELETE CASCADE,
CONSTRAINT fk_sm_mag FOREIGN KEY (id_magnitud)
REFERENCES magnitudes(id_magnitud) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS lecturas (
id_lectura BIGINT AUTO_INCREMENT PRIMARY KEY,
valor DECIMAL(12,4) NOT NULL,
fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
calidad VARCHAR(20) NOT NULL DEFAULT 'valida',
mensaje_id VARCHAR(100) NOT NULL UNIQUE,
id_sensor INT NOT NULL,
id_magnitud INT NOT NULL,
CONSTRAINT fk_lec_sens FOREIGN KEY (id_sensor)
REFERENCES sensores(id_sensor) ON DELETE RESTRICT,
CONSTRAINT fk_lec_mag FOREIGN KEY (id_magnitud)
REFERENCES magnitudes(id_magnitud) ON DELETE RESTRICT,
INDEX idx_lec_sens_mag_tiempo (id_sensor, id_magnitud, fecha_hora),
INDEX idx_lec_tiempo (fecha_hora)
);
-- 5 Reglas y alertas
CREATE TABLE IF NOT EXISTS reglas_alerta (
id_regla INT AUTO_INCREMENT PRIMARY KEY,
operador VARCHAR(10) NOT NULL,
valor_umbral DECIMAL(12,4) NOT NULL,
severidad VARCHAR(20) NOT NULL,
duracion_minima_seg INT NOT NULL DEFAULT 0,
vigencia_desde TIMESTAMP NULL,
vigencia_hasta TIMESTAMP NULL,
activa TINYINT(1) NOT NULL DEFAULT 1,
id_magnitud INT NOT NULL,
id_zona INT,
CONSTRAINT fk_regla_mag FOREIGN KEY (id_magnitud)
REFERENCES magnitudes(id_magnitud) ON DELETE RESTRICT,
CONSTRAINT fk_regla_zona FOREIGN KEY (id_zona)
REFERENCES zonas(id_zona) ON DELETE CASCADE,
INDEX idx_regla_mag_zona (id_magnitud, id_zona)
);
CREATE TABLE IF NOT EXISTS alertas (
id_alerta BIGINT AUTO_INCREMENT PRIMARY KEY,
mensaje_corto VARCHAR(200) NOT NULL,
detalle_tecnico TEXT,
severidad VARCHAR(20) NOT NULL,
fecha_inicio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
fecha_reconocimiento TIMESTAMP NULL,
fecha_resolucion TIMESTAMP NULL,
id_regla INT NOT NULL,
id_lectura_origen BIGINT NOT NULL,
id_dispositivo INT NOT NULL,
id_zona INT NOT NULL,
id_tipo_alerta INT NOT NULL,
id_estado_alerta INT NOT NULL,
reconocido_por INT NULL,
resuelto_por INT NULL,
CONSTRAINT fk_al_regla FOREIGN KEY (id_regla)
REFERENCES reglas_alerta(id_regla) ON DELETE RESTRICT,
CONSTRAINT fk_al_lectura FOREIGN KEY (id_lectura_origen)
REFERENCES lecturas(id_lectura) ON DELETE RESTRICT,
CONSTRAINT fk_al_dev FOREIGN KEY (id_dispositivo)
REFERENCES dispositivos(id_dispositivo) ON DELETE RESTRICT,
CONSTRAINT fk_al_zona FOREIGN KEY (id_zona)
REFERENCES zonas(id_zona) ON DELETE RESTRICT,
CONSTRAINT fk_al_tipo FOREIGN KEY (id_tipo_alerta)
REFERENCES tipos_alerta(id_tipo_alerta) ON DELETE RESTRICT,
CONSTRAINT fk_al_estado FOREIGN KEY (id_estado_alerta)
REFERENCES estados_alerta(id_estado_alerta) ON DELETE RESTRICT,
CONSTRAINT fk_al_rec FOREIGN KEY (reconocido_por)
REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
CONSTRAINT fk_al_res FOREIGN KEY (resuelto_por)
REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
INDEX idx_al_estado_inicio (id_estado_alerta, fecha_inicio),
INDEX idx_al_zona_inicio (id_zona, fecha_inicio)
);
-- 6 Notificaciones
CREATE TABLE IF NOT EXISTS notificaciones (
id_notificacion BIGINT AUTO_INCREMENT PRIMARY KEY,
asunto VARCHAR(200) NOT NULL,
contenido TEXT,
fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
estado_envio VARCHAR(20) NOT NULL DEFAULT 'pendiente',
fecha_leida TIMESTAMP NULL,
id_alerta BIGINT NULL,
id_usuario_destino INT NOT NULL,
id_canal INT NOT NULL,
CONSTRAINT fk_not_al FOREIGN KEY (id_alerta)
REFERENCES alertas(id_alerta) ON DELETE SET NULL,
CONSTRAINT fk_not_user FOREIGN KEY (id_usuario_destino)
REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
CONSTRAINT fk_not_canal FOREIGN KEY (id_canal)
REFERENCES canales_notificacion(id_canal) ON DELETE RESTRICT,
INDEX idx_not_user_estado (id_usuario_destino, estado_envio),
INDEX idx_not_al (id_alerta)
);
CREATE TABLE IF NOT EXISTS usuarios_canales (
id_usuario INT NOT NULL,
id_canal INT NOT NULL,
habilitado TINYINT(1) NOT NULL DEFAULT 1,
destino VARCHAR(254),
prioridad INT NOT NULL DEFAULT 1,
PRIMARY KEY (id_usuario, id_canal),
CONSTRAINT fk_uc_user FOREIGN KEY (id_usuario)
REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
CONSTRAINT fk_uc_canal FOREIGN KEY (id_canal)
REFERENCES canales_notificacion(id_canal) ON DELETE RESTRICT
);
-- 7 Mantenimiento
CREATE TABLE IF NOT EXISTS mantenimientos (
id_mantenimiento INT AUTO_INCREMENT PRIMARY KEY,
fecha_programada TIMESTAMP NULL,
fecha_ejecucion TIMESTAMP NULL,
estado VARCHAR(20) NOT NULL DEFAULT 'programado',
resultado TEXT,
proxima_fecha TIMESTAMP NULL,
id_dispositivo INT NOT NULL,
id_responsable INT NOT NULL,
id_tipo_mantenimiento INT NOT NULL,
CONSTRAINT fk_mant_dev FOREIGN KEY (id_dispositivo)
REFERENCES dispositivos(id_dispositivo) ON DELETE RESTRICT,
CONSTRAINT fk_mant_resp FOREIGN KEY (id_responsable)
REFERENCES usuarios(id_usuario) ON DELETE RESTRICT,
CONSTRAINT fk_mant_tipo FOREIGN KEY (id_tipo_mantenimiento)
REFERENCES tipos_mantenimiento(id_tipo_mantenimiento) ON DELETE RESTRICT,
INDEX idx_mant_dev_fecha (id_dispositivo, fecha_programada),
INDEX idx_mant_prox (proxima_fecha)
);
-- 8 Soporte
CREATE TABLE IF NOT EXISTS dispositivo_zona_historial (
id_historial BIGINT AUTO_INCREMENT PRIMARY KEY,
id_dispositivo INT NOT NULL,
id_zona INT NOT NULL,
desde TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
hasta TIMESTAMP NULL,
CONSTRAINT fk_hdev FOREIGN KEY (id_dispositivo)
REFERENCES dispositivos(id_dispositivo) ON DELETE CASCADE,
CONSTRAINT fk_hzona FOREIGN KEY (id_zona)
REFERENCES zonas(id_zona) ON DELETE RESTRICT,
INDEX idx_hdev_desde (id_dispositivo, desde)
);
CREATE TABLE IF NOT EXISTS auditoria_cambios (
id_auditoria BIGINT AUTO_INCREMENT PRIMARY KEY,
id_usuario INT,
entidad VARCHAR(100) NOT NULL,
registro_id VARCHAR(100) NOT NULL,
accion VARCHAR(20) NOT NULL,
valor_anterior TEXT,
valor_nuevo TEXT,
fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT fk_aud_user FOREIGN KEY (id_usuario)
REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
INDEX idx_aud_ent_reg (entidad, registro_id)
);
