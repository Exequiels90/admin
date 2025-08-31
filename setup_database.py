import sqlite3
import os

def main():
    """Función principal para inicializar la base de datos"""
    print("🔧 Configurando la base de datos con nueva estructura...")

    # Eliminar la base de datos existente si existe
    if os.path.exists("db/productos.db"):
        os.remove("db/productos.db")
        print("✅ Base de datos anterior eliminada")

    # Crear directorio db si no existe
    os.makedirs("db", exist_ok=True)

    # Crear nueva base de datos
    conn = sqlite3.connect("db/productos.db")
    cursor = conn.cursor()

    print("📋 Creando tablas con nueva estructura...")

    # Crear tabla de categorías
    cursor.execute("""
    CREATE TABLE categorias (
        id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE
    )
    """)

    # Crear tabla de subcategorías
    cursor.execute("""
    CREATE TABLE subcategorias (
        id_subcategoria INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        categoria_id INTEGER NOT NULL,
        FOREIGN KEY (categoria_id) REFERENCES categorias (id_categoria)
    )
    """)

    # Crear tabla de marcas
    cursor.execute("""
    CREATE TABLE marcas (
        id_marca INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        subcategoria_id INTEGER NOT NULL,
        FOREIGN KEY (subcategoria_id) REFERENCES subcategorias (id_subcategoria)
    )
    """)

    # Crear tabla de versiones
    cursor.execute("""
    CREATE TABLE versiones (
        id_version INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        marca_id INTEGER NOT NULL,
        FOREIGN KEY (marca_id) REFERENCES marcas (id_marca)
    )
    """)

    # Crear tabla de productos (actualizada)
    cursor.execute("""
    CREATE TABLE productos (
        id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        categoria_id INTEGER,
        subcategoria_id INTEGER,
        marca_id INTEGER,
        version_id INTEGER,
        precio_compra REAL DEFAULT 0,
        precio_venta REAL DEFAULT 0,
        stock INTEGER DEFAULT 0,
        activo INTEGER DEFAULT 1,
        eliminado INTEGER DEFAULT 0,
        FOREIGN KEY (categoria_id) REFERENCES categorias (id_categoria),
        FOREIGN KEY (subcategoria_id) REFERENCES subcategorias (id_subcategoria),
        FOREIGN KEY (marca_id) REFERENCES marcas (id_marca),
        FOREIGN KEY (version_id) REFERENCES versiones (id_version)
    )
    """)

    # Crear tabla de proveedores
    cursor.execute("""
    CREATE TABLE proveedores (
        id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT,
        email TEXT
    )
    """)

    # Crear tabla de lotes
    cursor.execute("""
    CREATE TABLE lotes (
        id_lote INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_lote TEXT UNIQUE NOT NULL,
        nro_factura TEXT,
        id_proveedor INTEGER,
        fecha_factura DATE,
        fecha_carga DATE DEFAULT CURRENT_DATE,
        observaciones TEXT,
        FOREIGN KEY (id_proveedor) REFERENCES proveedores (id_proveedor)
    )
    """)

    # Crear tabla de lotes_detalles
    cursor.execute("""
    CREATE TABLE lotes_detalles (
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

    # Crear tabla de clientes
    cursor.execute("""
    CREATE TABLE clientes (
        id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT,
        email TEXT,
        direccion TEXT
    )
    """)

    # Crear tabla de ventas
    cursor.execute("""
    CREATE TABLE ventas (
        id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cliente INTEGER,
        fecha_venta DATE DEFAULT CURRENT_DATE,
        fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_venta REAL DEFAULT 0,
        metodo_pago TEXT DEFAULT 'Efectivo',
        observaciones TEXT,
        eliminado INTEGER DEFAULT 0,
        FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
    )
    """)

    # Crear tabla de ventas_detalles
    cursor.execute("""
    CREATE TABLE ventas_detalles (
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

    # Crear tabla de historial_precios
    cursor.execute("""
    CREATE TABLE historial_precios (
        id_historial INTEGER PRIMARY KEY AUTOINCREMENT,
        id_producto INTEGER NOT NULL,
        precio_anterior REAL NOT NULL,
        precio_nuevo REAL NOT NULL,
        fecha_cambio DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_producto) REFERENCES productos (id_producto)
    )
    """)

    print("📦 Insertando datos de ejemplo...")

    # Insertar categorías
    categorias = [
        ("Bebidas",),
        ("Indumentaria",),
        ("Electrónicos",),
        ("Alimentos",),
        ("Limpieza",)
    ]

    cursor.executemany("INSERT INTO categorias (nombre) VALUES (?)", categorias)

    # Insertar subcategorías
    subcategorias = [
        # Bebidas
        ("Cerveza", 1),
        ("Gaseosa", 1),
        ("Vino", 1),
        ("Agua", 1),
        # Indumentaria
        ("Remeras", 2),
        ("Pantalones", 2),
        ("Medias", 2),
        ("Boxer", 2),
        ("Zapatillas", 2),
        # Electrónicos
        ("Celulares", 3),
        ("Computadoras", 3),
        ("Accesorios", 3),
        # Alimentos
        ("Snacks", 4),
        ("Golosinas", 4),
        ("Enlatados", 4),
        # Limpieza
        ("Detergentes", 5),
        ("Jabones", 5),
        ("Papel Higiénico", 5)
    ]

    cursor.executemany("INSERT INTO subcategorias (nombre, categoria_id) VALUES (?, ?)", subcategorias)

    # Insertar marcas
    marcas = [
        # Cerveza
        ("Heineken", 1),
        ("Miller", 1),
        ("Corona", 1),
        ("Quilmes", 1),
        # Gaseosa
        ("Coca Cola", 2),
        ("Pepsi", 2),
        ("Sprite", 2),
        ("Fanta", 2),
        # Vino
        ("Trapiche", 3),
        ("Norton", 3),
        ("Luigi Bosca", 3),
        # Agua
        ("Villavicencio", 4),
        ("Eco de los Andes", 4),
        ("Glaciar", 4),
        # Remeras
        ("Narrow", 5),
        ("Taverniti", 5),
        ("Levi's", 5),
        ("Nike", 5),
        # Pantalones
        ("Narrow", 6),
        ("Taverniti", 6),
        ("Levi's", 6),
        ("Nike", 6),
        # Medias
        ("Nike", 7),
        ("Adidas", 7),
        ("Puma", 7),
        # Boxer
        ("Nike", 8),
        ("Adidas", 8),
        ("Puma", 8),
        # Zapatillas
        ("Nike", 9),
        ("Adidas", 9),
        ("Puma", 9),
        ("Converse", 9),
        # Celulares
        ("Samsung", 10),
        ("Apple", 10),
        ("Xiaomi", 10),
        ("Motorola", 10),
        # Computadoras
        ("Dell", 11),
        ("HP", 11),
        ("Lenovo", 11),
        ("Apple", 11),
        # Accesorios
        ("Samsung", 12),
        ("Apple", 12),
        ("Xiaomi", 12),
        # Snacks
        ("Doritos", 13),
        ("Pringles", 13),
        ("Cheetos", 13),
        # Golosinas
        ("Arcor", 14),
        ("Cadbury", 14),
        ("Ferrero", 14),
        # Enlatados
        ("La Campagnola", 15),
        ("Arcor", 15),
        ("Sancor", 15),
        # Detergentes
        ("Ala", 16),
        ("Skip", 16),
        ("Ace", 16),
        # Jabones
        ("Dove", 17),
        ("Rexona", 17),
        ("Lux", 17),
        # Papel Higiénico
        ("Scott", 18),
        ("Elite", 18),
        ("Huggies", 18)
    ]

    cursor.executemany("INSERT INTO marcas (nombre, subcategoria_id) VALUES (?, ?)", marcas)

    # Insertar versiones
    versiones = [
        # Cerveza Heineken
        ("330cc", 1),
        ("473cc", 1),
        ("710cc", 1),
        ("1L", 1),
        # Cerveza Miller
        ("330cc", 2),
        ("473cc", 2),
        ("710cc", 2),
        # Cerveza Corona
        ("330cc", 3),
        ("473cc", 3),
        # Cerveza Quilmes
        ("330cc", 4),
        ("473cc", 4),
        ("1L", 4),
        # Coca Cola
        ("500cc", 5),
        ("1L", 5),
        ("1.5L", 5),
        ("2L", 5),
        # Pepsi
        ("500cc", 6),
        ("1L", 6),
        ("1.5L", 6),
        # Sprite
        ("500cc", 7),
        ("1L", 7),
        # Fanta
        ("500cc", 8),
        ("1L", 8),
        # Vino Trapiche
        ("750cc", 9),
        ("1.5L", 9),
        # Vino Norton
        ("750cc", 10),
        ("1.5L", 10),
        # Vino Luigi Bosca
        ("750cc", 11),
        ("1.5L", 11),
        # Agua Villavicencio
        ("500cc", 12),
        ("1L", 12),
        ("1.5L", 12),
        # Agua Eco de los Andes
        ("500cc", 13),
        ("1L", 13),
        ("1.5L", 13),
        # Agua Glaciar
        ("500cc", 14),
        ("1L", 14),
        ("1.5L", 14),
        # Remeras Narrow
        ("S", 15),
        ("M", 15),
        ("L", 15),
        ("XL", 15),
        ("XXL", 15),
        # Remeras Taverniti
        ("S", 16),
        ("M", 16),
        ("L", 16),
        ("XL", 16),
        ("XXL", 16),
        # Remeras Levi's
        ("S", 17),
        ("M", 17),
        ("L", 17),
        ("XL", 17),
        ("XXL", 17),
        # Remeras Nike
        ("S", 18),
        ("M", 18),
        ("L", 18),
        ("XL", 18),
        ("XXL", 18),
        # Pantalones Narrow
        ("28", 19),
        ("30", 19),
        ("32", 19),
        ("34", 19),
        ("36", 19),
        # Pantalones Taverniti
        ("28", 20),
        ("30", 20),
        ("32", 20),
        ("34", 20),
        ("36", 20),
        # Pantalones Levi's
        ("28", 21),
        ("30", 21),
        ("32", 21),
        ("34", 21),
        ("36", 21),
        # Pantalones Nike
        ("28", 22),
        ("30", 22),
        ("32", 22),
        ("34", 22),
        ("36", 22),
        # Medias Nike
        ("35-38", 23),
        ("39-42", 23),
        ("43-46", 23),
        # Medias Adidas
        ("35-38", 24),
        ("39-42", 24),
        ("43-46", 24),
        # Medias Puma
        ("35-38", 25),
        ("39-42", 25),
        ("43-46", 25),
        # Boxer Nike
        ("S", 26),
        ("M", 26),
        ("L", 26),
        ("XL", 26),
        # Boxer Adidas
        ("S", 27),
        ("M", 27),
        ("L", 27),
        ("XL", 27),
        # Boxer Puma
        ("S", 28),
        ("M", 28),
        ("L", 28),
        ("XL", 28),
        # Zapatillas Nike
        ("40", 29),
        ("41", 29),
        ("42", 29),
        ("43", 29),
        ("44", 29),
        # Zapatillas Adidas
        ("40", 30),
        ("41", 30),
        ("42", 30),
        ("43", 30),
        ("44", 30),
        # Zapatillas Puma
        ("40", 31),
        ("41", 31),
        ("42", 31),
        ("43", 31),
        ("44", 31),
        # Zapatillas Converse
        ("40", 32),
        ("41", 32),
        ("42", 32),
        ("43", 32),
        ("44", 32),
        # Celulares Samsung
        ("Galaxy S23", 33),
        ("Galaxy A54", 33),
        ("Galaxy M54", 33),
        # Celulares Apple
        ("iPhone 15", 34),
        ("iPhone 14", 34),
        ("iPhone 13", 34),
        # Celulares Xiaomi
        ("Redmi Note 12", 35),
        ("POCO X5", 35),
        ("Mi 13", 35),
        # Celulares Motorola
        ("Moto G84", 36),
        ("Moto E40", 36),
        ("Moto G200", 36),
        # Computadoras Dell
        ("Inspiron 15", 37),
        ("Latitude 14", 37),
        ("XPS 13", 37),
        # Computadoras HP
        ("Pavilion 15", 38),
        ("EliteBook 14", 38),
        ("Spectre x360", 38),
        # Computadoras Lenovo
        ("ThinkPad T14", 39),
        ("IdeaPad 15", 39),
        ("Yoga 7", 39),
        # Computadoras Apple
        ("MacBook Air", 40),
        ("MacBook Pro", 40),
        ("iMac", 40),
        # Accesorios Samsung
        ("Cargador 25W", 41),
        ("Cable USB-C", 41),
        ("Funda Silicona", 41),
        # Accesorios Apple
        ("Cargador 20W", 42),
        ("Cable Lightning", 42),
        ("Funda Silicona", 42),
        # Accesorios Xiaomi
        ("Cargador 67W", 43),
        ("Cable USB-C", 43),
        ("Funda TPU", 43),
        # Snacks Doritos
        ("Nacho Cheese", 44),
        ("Cool Ranch", 44),
        ("Spicy Sweet Chili", 44),
        # Snacks Pringles
        ("Original", 45),
        ("Sour Cream", 45),
        ("BBQ", 45),
        # Snacks Cheetos
        ("Crunchy", 46),
        ("Puffs", 46),
        ("Flamin Hot", 46),
        # Golosinas Arcor
        ("Chocolate", 47),
        ("Caramelos", 47),
        ("Chupetines", 47),
        # Golosinas Cadbury
        ("Dairy Milk", 48),
        ("Crunchie", 48),
        ("Flake", 48),
        # Golosinas Ferrero
        ("Ferrero Rocher", 49),
        ("Kinder", 49),
        ("Nutella", 49),
        # Enlatados La Campagnola
        ("Arvejas", 50),
        ("Choclo", 50),
        ("Tomates", 50),
        # Enlatados Arcor
        ("Duraznos", 51),
        ("Peras", 51),
        ("Piña", 51),
        # Enlatados Sancor
        ("Atún", 52),
        ("Sardinas", 52),
        ("Caballa", 52),
        # Detergentes Ala
        ("Líquido", 53),
        ("Polvo", 53),
        ("Cápsulas", 53),
        # Detergentes Skip
        ("Líquido", 54),
        ("Polvo", 54),
        ("Cápsulas", 54),
        # Detergentes Ace
        ("Líquido", 55),
        ("Polvo", 55),
        ("Cápsulas", 55),
        # Jabones Dove
        ("Crema", 56),
        ("Gel", 56),
        ("Barra", 56),
        # Jabones Rexona
        ("Crema", 57),
        ("Gel", 57),
        ("Barra", 57),
        # Jabones Lux
        ("Crema", 58),
        ("Gel", 58),
        ("Barra", 58),
        # Papel Higiénico Scott
        ("4 Rollos", 59),
        ("8 Rollos", 59),
        ("12 Rollos", 59),
        # Papel Higiénico Elite
        ("4 Rollos", 60),
        ("8 Rollos", 60),
        ("12 Rollos", 60),
        # Papel Higiénico Huggies
        ("4 Rollos", 61),
        ("8 Rollos", 61),
        ("12 Rollos", 61)
    ]

    cursor.executemany("INSERT INTO versiones (nombre, marca_id) VALUES (?, ?)", versiones)

    # Insertar algunos productos de ejemplo
    import random

    def generar_codigo():
        return str(random.randint(100000, 999999))

    productos_ejemplo = [
        # Cerveza Heineken 473cc
        (generar_codigo(), "Cerveza Heineken 473cc", 1, 1, 1, 2, 150.00, 250.00, 50),
        # Coca Cola 1L
        (generar_codigo(), "Coca Cola 1L", 1, 2, 5, 16, 80.00, 150.00, 30),
        # Remera Narrow L
        (generar_codigo(), "Remera Narrow L", 2, 5, 15, 18, 800.00, 1200.00, 25),
        # Zapatillas Nike 42
        (generar_codigo(), "Zapatillas Nike 42", 2, 9, 29, 30, 15000.00, 25000.00, 10),
        # iPhone 15
        (generar_codigo(), "iPhone 15", 3, 10, 34, 34, 800000.00, 1200000.00, 5),
        # Doritos Nacho Cheese
        (generar_codigo(), "Doritos Nacho Cheese", 4, 13, 44, 44, 200.00, 350.00, 40),
        # Detergente Ala Líquido
        (generar_codigo(), "Detergente Ala Líquido", 5, 16, 53, 53, 300.00, 500.00, 20)
    ]

    cursor.executemany("""
        INSERT INTO productos (codigo, nombre, categoria_id, subcategoria_id, marca_id, version_id, precio_compra, precio_venta, stock)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, productos_ejemplo)

    # Insertar proveedores de ejemplo
    proveedores = [
        ("Distribuidora Central", "011-1234-5678", "central@dist.com"),
        ("Importadora del Sur", "011-9876-5432", "sur@import.com"),
        ("Mayorista Express", "011-5555-1234", "express@mayor.com")
    ]

    cursor.executemany("INSERT INTO proveedores (nombre, telefono, email) VALUES (?, ?, ?)", proveedores)

    # Insertar clientes de ejemplo
    clientes = [
        ("Juan Pérez", "011-1111-1111", "juan@email.com", "Av. Corrientes 123"),
        ("María García", "011-2222-2222", "maria@email.com", "Belgrano 456"),
        ("Carlos López", "011-3333-3333", "carlos@email.com", "Palermo 789")
    ]

    cursor.executemany("INSERT INTO clientes (nombre, telefono, email, direccion) VALUES (?, ?, ?, ?)", clientes)

    # Crear tabla de usuarios
    print("👤 Creando tabla de usuarios...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            email TEXT,
            rol TEXT DEFAULT 'admin',
            activo INTEGER DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultimo_login TIMESTAMP
        )
    """)

    # Insertar usuario administrador por defecto
    import hashlib
    password_hash = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute("""
        INSERT OR IGNORE INTO usuarios (username, password_hash, nombre_completo, email, rol)
        VALUES (?, ?, ?, ?, ?)
    """, ("admin", password_hash, "Administrador", "admin@sistema.com", "admin"))

    # Crear índices para mejorar rendimiento
    print("🔍 Creando índices...")

    cursor.execute("CREATE INDEX idx_productos_categoria ON productos(categoria_id)")
    cursor.execute("CREATE INDEX idx_productos_subcategoria ON productos(subcategoria_id)")
    cursor.execute("CREATE INDEX idx_productos_marca ON productos(marca_id)")
    cursor.execute("CREATE INDEX idx_productos_version ON productos(version_id)")
    cursor.execute("CREATE INDEX idx_productos_activo ON productos(activo)")
    cursor.execute("CREATE INDEX idx_productos_eliminado ON productos(eliminado)")
    cursor.execute("CREATE INDEX idx_subcategorias_categoria ON subcategorias(categoria_id)")
    cursor.execute("CREATE INDEX idx_versiones_marca ON versiones(marca_id)")
    cursor.execute("CREATE INDEX idx_usuarios_username ON usuarios(username)")

    # Guardar cambios
    conn.commit()
    conn.close()

    print("✅ Base de datos creada exitosamente con nueva estructura!")
    print("📊 Datos pre-cargados:")
    print("   - 5 Categorías")
    print("   - 19 Subcategorías")
    print("   - 61 Marcas")
    print("   - 183 Versiones")
    print("   - 7 Productos de ejemplo")
    print("   - 3 Proveedores")
    print("   - 3 Clientes")
    print("   - 1 Usuario administrador")
    print("\n🎯 Estructura implementada: Categoría → Subcategoría → Marca → Versión")
    print("\n🔐 Usuario por defecto:")
    print("   Usuario: admin")
    print("   Contraseña: admin123")

if __name__ == "__main__":
    main()
