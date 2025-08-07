import sqlite3
import os

DB_PATH = os.path.join("db", "productos.db")

os.makedirs("db", exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Tabla de categorías
cursor.execute("""
CREATE TABLE IF NOT EXISTS categorias (
    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL
)
""")

# Tabla de productos
cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    id_categoria INTEGER,
    stock INTEGER,
    lote TEXT,
    activo INTEGER DEFAULT 1,
    FOREIGN KEY (id_categoria) REFERENCES categorias(id_categoria)
)
""")

# Tabla de precios de venta históricos
cursor.execute("""
CREATE TABLE IF NOT EXISTS precios_venta (
    id_precio INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER,
    precio_unitario REAL NOT NULL,
    desde_fecha DATE NOT NULL,
    FOREIGN KEY (id_producto) REFERENCES productos(id_producto)
)
""")

# Tabla de compras
cursor.execute("""
CREATE TABLE IF NOT EXISTS compras (
    id_compra INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    proveedor TEXT
)
""")

# Detalles de cada compra
cursor.execute("""
CREATE TABLE IF NOT EXISTS compra_detalle (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
    id_compra INTEGER,
    id_producto INTEGER,
    cantidad INTEGER,
    costo_unitario REAL,
    FOREIGN KEY (id_compra) REFERENCES compras(id_compra),
    FOREIGN KEY (id_producto) REFERENCES productos(id_producto)
)
""")

conn.commit()
conn.close()

print("✅ Base de datos creada correctamente en db/productos.db")
