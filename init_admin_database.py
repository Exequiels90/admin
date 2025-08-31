#!/usr/bin/env python3
"""
Script para inicializar la base de datos del Admin con todas las tablas necesarias
"""

import sqlite3
import os
from datetime import datetime

def init_admin_database():
    """Inicializa la base de datos del Admin con todas las tablas"""
    print("🗄️ Inicializando Base de Datos del Admin...")
    
    # Crear directorio si no existe
    os.makedirs('db', exist_ok=True)
    
    conn = sqlite3.connect('db/admin_database.db')
    cursor = conn.cursor()
    
    # Tabla de pagos parciales
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pagos_parciales (
        id_pago INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        venta_id INTEGER NOT NULL,
        monto_pago REAL NOT NULL,
        usuario_id INTEGER NOT NULL,
        fecha_pago DATETIME DEFAULT CURRENT_TIMESTAMP,
        sincronizado INTEGER DEFAULT 0,
        fecha_sincronizacion DATETIME,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id_cliente),
        FOREIGN KEY (venta_id) REFERENCES ventas (id_venta),
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id_usuario)
    )
    """)
    
    # Tabla de clientes (si no existe)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
        dni VARCHAR(20) UNIQUE NOT NULL,
        nombre VARCHAR(100) NOT NULL,
        apellido VARCHAR(100) NOT NULL,
        email VARCHAR(100),
        telefono VARCHAR(20),
        direccion TEXT,
        fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
        activo INTEGER DEFAULT 1
    )
    """)
    
    # Tabla de ventas (si no existe)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
        total REAL NOT NULL,
        efectivo REAL DEFAULT 0,
        transferencia REAL DEFAULT 0,
        credito REAL DEFAULT 0,
        prestamo_personal REAL DEFAULT 0,
        monto_pendiente REAL,
        usuario_id INTEGER NOT NULL,
        cliente_id INTEGER,
        fecha_venta DATETIME DEFAULT CURRENT_TIMESTAMP,
        sincronizado INTEGER DEFAULT 0,
        fecha_sincronizacion DATETIME,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id_usuario),
        FOREIGN KEY (cliente_id) REFERENCES clientes (id_cliente)
    )
    """)
    
    # Tabla de auditoría (si no existe)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        accion VARCHAR(50) NOT NULL,
        tabla VARCHAR(50) NOT NULL,
        registro_id INTEGER,
        detalles TEXT,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id_usuario)
    )
    """)
    
    # Tabla de clientes POS (si no existe)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes_pos (
        id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre VARCHAR(100) NOT NULL,
        url VARCHAR(200) NOT NULL,
        estado VARCHAR(20) DEFAULT 'desconectado',
        ultima_sincronizacion DATETIME,
        ultimo_error TEXT,
        activo INTEGER DEFAULT 1,
        fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Insertar algunos clientes de prueba
    cursor.execute("""
    INSERT OR IGNORE INTO clientes (dni, nombre, apellido, email, telefono, direccion)
    VALUES 
        ('12345678', 'Juan', 'Pérez', 'juan@email.com', '123456789', 'Calle 123'),
        ('87654321', 'María', 'González', 'maria@email.com', '987654321', 'Avenida 456')
    """)
    
    # Insertar cliente POS de prueba
    cursor.execute("""
    INSERT OR IGNORE INTO clientes_pos (nombre, url, estado)
    VALUES ('POS Principal', 'http://localhost:5000', 'conectado')
    """)
    
    conn.commit()
    conn.close()
    
    print("✅ Base de datos del Admin inicializada correctamente")
    print("📋 Tablas creadas:")
    print("   ├─ pagos_parciales")
    print("   ├─ clientes")
    print("   ├─ ventas")
    print("   ├─ auditoria")
    print("   └─ clientes_pos")

if __name__ == "__main__":
    init_admin_database()
