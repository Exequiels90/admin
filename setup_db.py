import sqlite3
import os

# Crear directorio db si no existe
os.makedirs("db", exist_ok=True)

# Conectar a la base de datos
conn = sqlite3.connect("db/productos.db")
cursor = conn.cursor()

# Crear tabla de categorías
cursor.execute("""
CREATE TABLE IF NOT EXISTS categorias (
    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
)
""")

# Crear tabla de proveedores
cursor.execute("""
CREATE TABLE IF NOT EXISTS proveedores (
    id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT
)
""")

# Crear tabla de productos (actualizada con campo marca)
cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    marca TEXT,
    categoria_id INTEGER,
    precio_compra REAL DEFAULT 0,
    precio_venta REAL DEFAULT 0,
    stock INTEGER DEFAULT 0,
    activo INTEGER DEFAULT 1,
    eliminado INTEGER DEFAULT 0,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (categoria_id) REFERENCES categorias (id_categoria)
)
""")

# Crear tabla de lotes (actualizada con número de lote automático)
cursor.execute("""
CREATE TABLE IF NOT EXISTS lotes (
    id_lote INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_lote TEXT UNIQUE NOT NULL,
    nro_factura TEXT,
    id_proveedor INTEGER,
    fecha_factura DATE NOT NULL,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observaciones TEXT,
    FOREIGN KEY (id_proveedor) REFERENCES proveedores (id_proveedor)
)
""")

# Crear tabla de detalles de lotes
cursor.execute("""
CREATE TABLE IF NOT EXISTS lotes_detalles (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
    id_lote INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_compra REAL NOT NULL,
    precio_venta REAL NOT NULL,
    FOREIGN KEY (id_lote) REFERENCES lotes (id_lote),
    FOREIGN KEY (id_producto) REFERENCES productos (id_producto)
)
""")

# Crear tabla de historial de precios
cursor.execute("""
CREATE TABLE IF NOT EXISTS historial_precios (
    id_historial INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL,
    id_lote INTEGER NOT NULL,
    precio_compra REAL NOT NULL,
    precio_venta REAL NOT NULL,
    fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_producto) REFERENCES productos (id_producto),
    FOREIGN KEY (id_lote) REFERENCES lotes (id_lote)
)
""")

# Crear tabla de clientes
cursor.execute("""
CREATE TABLE IF NOT EXISTS clientes (
    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT,
    direccion TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Crear tabla de ventas
cursor.execute("""
CREATE TABLE IF NOT EXISTS ventas (
    id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER,
    fecha_venta DATE NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_venta REAL DEFAULT 0,
    metodo_pago TEXT DEFAULT 'Efectivo',
    observaciones TEXT,
    eliminado INTEGER DEFAULT 0,
    FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
)
""")

# Crear tabla de detalles de ventas
cursor.execute("""
CREATE TABLE IF NOT EXISTS ventas_detalles (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY (id_venta) REFERENCES ventas (id_venta),
    FOREIGN KEY (id_producto) REFERENCES productos (id_producto)
)
""")

# Crear índices para optimizar consultas
cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_codigo ON productos(codigo)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_activo ON productos(activo, eliminado)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_lotes_numero ON lotes(numero_lote)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_lotes_fecha ON lotes(fecha_factura)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_lotes_proveedor ON lotes(id_proveedor)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_lotes_detalles_lote ON lotes_detalles(id_lote)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_lotes_detalles_producto ON lotes_detalles(id_producto)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_producto ON historial_precios(id_producto)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha_venta)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_cliente ON ventas(id_cliente)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_detalles_venta ON ventas_detalles(id_venta)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_detalles_producto ON ventas_detalles(id_producto)")

# Crear triggers para mantener el stock actualizado
cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_insert
AFTER INSERT ON lotes_detalles
BEGIN
    UPDATE productos 
    SET stock = stock + NEW.cantidad 
    WHERE id_producto = NEW.id_producto;
END
""")

cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_update
AFTER UPDATE ON lotes_detalles
BEGIN
    UPDATE productos 
    SET stock = stock - OLD.cantidad + NEW.cantidad 
    WHERE id_producto = NEW.id_producto;
END
""")

cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_delete
AFTER DELETE ON lotes_detalles
BEGIN
    UPDATE productos 
    SET stock = stock - OLD.cantidad 
    WHERE id_producto = OLD.id_producto;
END
""")

# Crear triggers para actualizar stock en ventas
cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_venta_insert
AFTER INSERT ON ventas_detalles
BEGIN
    UPDATE productos 
    SET stock = stock - NEW.cantidad 
    WHERE id_producto = NEW.id_producto;
END
""")

cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_venta_update
AFTER UPDATE ON ventas_detalles
BEGIN
    UPDATE productos 
    SET stock = stock + OLD.cantidad - NEW.cantidad 
    WHERE id_producto = NEW.id_producto;
END
""")

cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_venta_delete
AFTER DELETE ON ventas_detalles
BEGIN
    UPDATE productos 
    SET stock = stock + OLD.cantidad 
    WHERE id_producto = OLD.id_producto;
END
""")

# Crear trigger para calcular total de venta
cursor.execute("""
CREATE TRIGGER IF NOT EXISTS calcular_total_venta
AFTER INSERT ON ventas_detalles
BEGIN
    UPDATE ventas 
    SET total_venta = (
        SELECT SUM(subtotal) 
        FROM ventas_detalles 
        WHERE id_venta = NEW.id_venta
    )
    WHERE id_venta = NEW.id_venta;
END
""")

# Crear trigger para actualizar precio de venta del producto cuando se inserta un detalle de lote
cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_precio_venta_producto
AFTER INSERT ON lotes_detalles
BEGIN
    UPDATE productos 
    SET precio_venta = NEW.precio_venta,
        precio_compra = NEW.precio_compra
    WHERE id_producto = NEW.id_producto;
    
    INSERT INTO historial_precios (id_producto, id_lote, precio_compra, precio_venta)
    VALUES (NEW.id_producto, NEW.id_lote, NEW.precio_compra, NEW.precio_venta);
END
""")

# Insertar datos de ejemplo
cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES ('Electrónicos')")
cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES ('Ropa')")
cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES ('Hogar')")
cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES ('Herramientas')")

cursor.execute("INSERT OR IGNORE INTO proveedores (nombre, telefono, email) VALUES ('Proveedor A', '123-456-7890', 'proveedorA@email.com')")
cursor.execute("INSERT OR IGNORE INTO proveedores (nombre, telefono, email) VALUES ('Proveedor B', '098-765-4321', 'proveedorB@email.com')")

cursor.execute("INSERT OR IGNORE INTO clientes (nombre, telefono, email) VALUES ('Cliente General', '', '')")
cursor.execute("INSERT OR IGNORE INTO clientes (nombre, telefono, email) VALUES ('Juan Pérez', '555-1234', 'juan@email.com')")
cursor.execute("INSERT OR IGNORE INTO clientes (nombre, telefono, email) VALUES ('María García', '555-5678', 'maria@email.com')")

# Guardar cambios y cerrar conexión
conn.commit()
conn.close()

print("Base de datos creada exitosamente con todas las tablas y triggers.")
import sqlite3
import os

# Crear directorio db si no existe
os.makedirs("db", exist_ok=True)

# Conectar a la base de datos
conn = sqlite3.connect("db/productos.db")
cursor = conn.cursor()

# Crear tabla de categorías
cursor.execute("""
CREATE TABLE IF NOT EXISTS categorias (
    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
)
""")

# Crear tabla de proveedores
cursor.execute("""
CREATE TABLE IF NOT EXISTS proveedores (
    id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT
)
""")

# Crear tabla de productos (actualizada con campo marca)
cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    marca TEXT,
    categoria_id INTEGER,
    precio_compra REAL DEFAULT 0,
    precio_venta REAL DEFAULT 0,
    stock INTEGER DEFAULT 0,
    activo INTEGER DEFAULT 1,
    eliminado INTEGER DEFAULT 0,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (categoria_id) REFERENCES categorias (id_categoria)
)
""")

# Crear tabla de lotes (actualizada con número de lote automático)
cursor.execute("""
CREATE TABLE IF NOT EXISTS lotes (
    id_lote INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_lote TEXT UNIQUE NOT NULL,
    nro_factura TEXT,
    id_proveedor INTEGER,
    fecha_factura DATE NOT NULL,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observaciones TEXT,
    FOREIGN KEY (id_proveedor) REFERENCES proveedores (id_proveedor)
)
""")

# Crear tabla de detalles de lotes
cursor.execute("""
CREATE TABLE IF NOT EXISTS lotes_detalles (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
    id_lote INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_compra REAL NOT NULL,
    precio_venta REAL NOT NULL,
    FOREIGN KEY (id_lote) REFERENCES lotes (id_lote),
    FOREIGN KEY (id_producto) REFERENCES productos (id_producto)
)
""")

# Crear tabla de historial de precios
cursor.execute("""
CREATE TABLE IF NOT EXISTS historial_precios (
    id_historial INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL,
    id_lote INTEGER NOT NULL,
    precio_compra REAL NOT NULL,
    precio_venta REAL NOT NULL,
    fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_producto) REFERENCES productos (id_producto),
    FOREIGN KEY (id_lote) REFERENCES lotes (id_lote)
)
""")

# Crear tabla de clientes
cursor.execute("""
CREATE TABLE IF NOT EXISTS clientes (
    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT,
    direccion TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Crear tabla de ventas
cursor.execute("""
CREATE TABLE IF NOT EXISTS ventas (
    id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER,
    fecha_venta DATE NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_venta REAL DEFAULT 0,
    metodo_pago TEXT DEFAULT 'Efectivo',
    observaciones TEXT,
    eliminado INTEGER DEFAULT 0,
    FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
)
""")

# Crear tabla de detalles de ventas
cursor.execute("""
CREATE TABLE IF NOT EXISTS ventas_detalles (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY (id_venta) REFERENCES ventas (id_venta),
    FOREIGN KEY (id_producto) REFERENCES productos (id_producto)
)
""")

# Crear índices para optimizar consultas
cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_codigo ON productos(codigo)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_activo ON productos(activo, eliminado)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_lotes_numero ON lotes(numero_lote)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_lotes_fecha ON lotes(fecha_factura)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_lotes_proveedor ON lotes(id_proveedor)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_lotes_detalles_lote ON lotes_detalles(id_lote)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_lotes_detalles_producto ON lotes_detalles(id_producto)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_producto ON historial_precios(id_producto)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha_venta)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_cliente ON ventas(id_cliente)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_detalles_venta ON ventas_detalles(id_venta)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_detalles_producto ON ventas_detalles(id_producto)")

# Crear triggers para mantener el stock actualizado
cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_insert
AFTER INSERT ON lotes_detalles
BEGIN
    UPDATE productos 
    SET stock = stock + NEW.cantidad 
    WHERE id_producto = NEW.id_producto;
END
""")

cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_update
AFTER UPDATE ON lotes_detalles
BEGIN
    UPDATE productos 
    SET stock = stock - OLD.cantidad + NEW.cantidad 
    WHERE id_producto = NEW.id_producto;
END
""")

cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_delete
AFTER DELETE ON lotes_detalles
BEGIN
    UPDATE productos 
    SET stock = stock - OLD.cantidad 
    WHERE id_producto = OLD.id_producto;
END
""")

# Crear triggers para actualizar stock en ventas
cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_venta_insert
AFTER INSERT ON ventas_detalles
BEGIN
    UPDATE productos 
    SET stock = stock - NEW.cantidad 
    WHERE id_producto = NEW.id_producto;
END
""")

cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_venta_update
AFTER UPDATE ON ventas_detalles
BEGIN
    UPDATE productos 
    SET stock = stock + OLD.cantidad - NEW.cantidad 
    WHERE id_producto = NEW.id_producto;
END
""")

cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_stock_venta_delete
AFTER DELETE ON ventas_detalles
BEGIN
    UPDATE productos 
    SET stock = stock + OLD.cantidad 
    WHERE id_producto = OLD.id_producto;
END
""")

# Crear trigger para calcular total de venta
cursor.execute("""
CREATE TRIGGER IF NOT EXISTS calcular_total_venta
AFTER INSERT ON ventas_detalles
BEGIN
    UPDATE ventas 
    SET total_venta = (
        SELECT SUM(subtotal) 
        FROM ventas_detalles 
        WHERE id_venta = NEW.id_venta
    )
    WHERE id_venta = NEW.id_venta;
END
""")

# Crear trigger para actualizar precio de venta del producto cuando se inserta un detalle de lote
cursor.execute("""
CREATE TRIGGER IF NOT EXISTS actualizar_precio_venta_producto
AFTER INSERT ON lotes_detalles
BEGIN
    UPDATE productos 
    SET precio_venta = NEW.precio_venta,
        precio_compra = NEW.precio_compra
    WHERE id_producto = NEW.id_producto;
    
    INSERT INTO historial_precios (id_producto, id_lote, precio_compra, precio_venta)
    VALUES (NEW.id_producto, NEW.id_lote, NEW.precio_compra, NEW.precio_venta);
END
""")

# Insertar datos de ejemplo
cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES ('Electrónicos')")
cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES ('Ropa')")
cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES ('Hogar')")
cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES ('Herramientas')")

cursor.execute("INSERT OR IGNORE INTO proveedores (nombre, telefono, email) VALUES ('Proveedor A', '123-456-7890', 'proveedorA@email.com')")
cursor.execute("INSERT OR IGNORE INTO proveedores (nombre, telefono, email) VALUES ('Proveedor B', '098-765-4321', 'proveedorB@email.com')")

cursor.execute("INSERT OR IGNORE INTO clientes (nombre, telefono, email) VALUES ('Cliente General', '', '')")
cursor.execute("INSERT OR IGNORE INTO clientes (nombre, telefono, email) VALUES ('Juan Pérez', '555-1234', 'juan@email.com')")
cursor.execute("INSERT OR IGNORE INTO clientes (nombre, telefono, email) VALUES ('María García', '555-5678', 'maria@email.com')")

# Guardar cambios y cerrar conexión
conn.commit()
conn.close()

print("Base de datos creada exitosamente con todas las tablas y triggers.")
