#!/usr/bin/env python3
"""
Script simple para inicializar la base de datos del Admin
"""

import sqlite3
import os
import hashlib

def setup_database():
    """Inicializa la base de datos del Admin"""
    print("🗄️ Inicializando Base de Datos del Admin...")
    
    # Crear directorio si no existe
    os.makedirs('db', exist_ok=True)
    
    # Conectar a la base de datos
    conn = sqlite3.connect('db/admin_database.db')
    cursor = conn.cursor()
    
    # Tabla de usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nombre_completo TEXT NOT NULL,
        rol TEXT DEFAULT 'admin',
        activo INTEGER DEFAULT 1,
        ultimo_login TIMESTAMP,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabla de categorías
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categorias (
        id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE
    )
    """)
    
    # Tabla de subcategorías
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subcategorias (
        id_subcategoria INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        categoria_id INTEGER,
        FOREIGN KEY (categoria_id) REFERENCES categorias (id_categoria)
    )
    """)
    
    # Tabla de marcas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS marcas (
        id_marca INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        subcategoria_id INTEGER,
        FOREIGN KEY (subcategoria_id) REFERENCES subcategorias (id_subcategoria)
    )
    """)
    
    # Tabla de versiones
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS versiones (
        id_version INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        marca_id INTEGER,
        FOREIGN KEY (marca_id) REFERENCES marcas (id_marca)
    )
    """)
    
    # Tabla de productos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        categoria_id INTEGER,
        subcategoria_id INTEGER,
        marca_id INTEGER,
        version_id INTEGER,
        precio_compra REAL DEFAULT 0,
        precio_venta REAL DEFAULT 0,
        stock REAL DEFAULT 0,
        es_pesable INTEGER DEFAULT 0,
        unidad_medida TEXT DEFAULT 'unidad',
        activo INTEGER DEFAULT 1,
        eliminado INTEGER DEFAULT 0,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ultima_sincronizacion TIMESTAMP,
        venta_por_peso INTEGER DEFAULT 0,
        FOREIGN KEY (categoria_id) REFERENCES categorias (id_categoria),
        FOREIGN KEY (subcategoria_id) REFERENCES subcategorias (id_subcategoria),
        FOREIGN KEY (marca_id) REFERENCES marcas (id_marca),
        FOREIGN KEY (version_id) REFERENCES versiones (id_version)
    )
    """)
    
    # Tabla de clientes
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
    
    # Tabla de ventas
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
        eliminado INTEGER DEFAULT 0
    )
    """)
    
    # Tabla de detalles de ventas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detalles_venta (
        id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER,
        producto_id INTEGER,
        cantidad REAL NOT NULL,
        precio_unitario REAL NOT NULL,
        subtotal REAL NOT NULL,
        eliminado INTEGER DEFAULT 0,
        FOREIGN KEY (venta_id) REFERENCES ventas (id_venta),
        FOREIGN KEY (producto_id) REFERENCES productos (id_producto)
    )
    """)
    
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
        fecha_sincronizacion DATETIME
    )
    """)
    
    # Tabla de auditoría
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        accion VARCHAR(50) NOT NULL,
        tabla VARCHAR(50) NOT NULL,
        registro_id INTEGER,
        detalles TEXT,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabla de lotes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lotes (
        id_lote INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_lote VARCHAR(50) NOT NULL,
        nro_factura VARCHAR(50),
        id_proveedor INTEGER,
        fecha_factura DATE,
        fecha_carga DATETIME DEFAULT CURRENT_TIMESTAMP,
        observaciones TEXT,
        fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabla de detalles de lotes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lotes_detalles (
        id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
        id_lote INTEGER NOT NULL,
        id_producto INTEGER NOT NULL,
        cantidad REAL NOT NULL,
        precio_compra REAL NOT NULL,
        precio_venta REAL NOT NULL,
        FOREIGN KEY (id_lote) REFERENCES lotes (id_lote),
        FOREIGN KEY (id_producto) REFERENCES productos (id_producto)
    )
    """)
    
    # Tabla de proveedores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proveedores (
        id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre VARCHAR(100) NOT NULL,
        telefono VARCHAR(20),
        email VARCHAR(100),
        direccion TEXT,
        fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
        activo INTEGER DEFAULT 1
    )
    """)
    
    # Tabla de clientes POS
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
    
    # Insertar usuario administrador por defecto
    password_hash = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute("""
    INSERT OR IGNORE INTO usuarios (username, password_hash, nombre_completo, rol, activo)
    VALUES ('admin', ?, 'Administrador', 'admin', 1)
    """, (password_hash,))
    
    # Insertar categorías básicas
    categorias_basicas = [
        "Alimentos",
        "Bebidas", 
        "Limpieza",
        "Higiene Personal",
        "Otros"
    ]
    
    for categoria in categorias_basicas:
        cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (categoria,))
    
    # Insertar datos de prueba
    cursor.execute("""
    INSERT OR IGNORE INTO clientes (dni, nombre, apellido, email, telefono, direccion)
    VALUES 
        ('12345678', 'Juan', 'Pérez', 'juan@email.com', '123456789', 'Calle 123'),
        ('87654321', 'María', 'González', 'maria@email.com', '987654321', 'Avenida 456')
    """)
    
    cursor.execute("""
    INSERT OR IGNORE INTO clientes_pos (nombre, url, estado)
    VALUES ('POS Principal', 'http://localhost:5000', 'conectado')
    """)
    
    # Guardar cambios
    conn.commit()
    conn.close()
    
    print("✅ Base de datos del Admin inicializada correctamente")
    print("📋 Tablas creadas:")
    print("   ├─ usuarios")
    print("   ├─ categorias")
    print("   ├─ subcategorias")
    print("   ├─ marcas")
    print("   ├─ versiones")
    print("   ├─ productos")
    print("   ├─ clientes")
    print("   ├─ ventas")
    print("   ├─ detalles_venta")
    print("   ├─ pagos_parciales")
    print("   ├─ auditoria")
    print("   ├─ lotes")
    print("   ├─ lotes_detalles")
    print("   ├─ proveedores")
    print("   └─ clientes_pos")
    print("\n🔑 Credenciales de acceso:")
    print("   Usuario: admin")
    print("   Contraseña: admin123")

if __name__ == "__main__":
    setup_database()
