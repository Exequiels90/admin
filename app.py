from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
import sqlite3
import os
import random
import json
import hashlib
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
from io import BytesIO
import barcode
from barcode.writer import ImageWriter
from functools import wraps
from config import config

# Configuración de la aplicación
app = Flask(__name__)
app.config.from_object(config['production'] if os.environ.get('FLASK_ENV') == 'production' else config['development'])

DB_PATH = app.config['DATABASE_PATH']

# -------------------
# FUNCIONES DE AUTENTICACIÓN
# -------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def hash_password(password):
    """Genera un hash SHA-256 de la contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    """Verifica las credenciales del usuario"""
    conn = get_db_connection()
    user = conn.execute("""
        SELECT id_usuario, username, nombre_completo, rol, activo 
        FROM usuarios 
        WHERE username = ? AND password_hash = ? AND activo = 1
    """, (username, hash_password(password))).fetchone()
    conn.close()
    return user

def update_last_login(user_id):
    """Actualiza la fecha del último login"""
    conn = get_db_connection()
    conn.execute("UPDATE usuarios SET ultimo_login = CURRENT_TIMESTAMP WHERE id_usuario = ?", (user_id,))
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------
# RUTAS DE AUTENTICACIÓN
# -------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            flash("Por favor ingresa usuario y contraseña", "error")
            return render_template("login.html")
        
        user = verify_user(username, password)
        
        if user:
            session['user_id'] = user['id_usuario']
            session['username'] = user['username']
            session['nombre_completo'] = user['nombre_completo']
            session['rol'] = user['rol']
            
            update_last_login(user['id_usuario'])
            
            flash(f"¡Bienvenido, {user['nombre_completo']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Usuario o contraseña incorrectos", "error")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión correctamente", "info")
    return redirect(url_for("login"))

# -------------------
# RUTA PRINCIPAL
# -------------------
@app.route("/")
def index():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))

# -------------------
# LISTAR PRODUCTOS
# -------------------
@app.route("/admin")
@login_required
def admin():
    conn = get_db_connection()
    productos = conn.execute("""
        SELECT 
            p.id_producto,
            p.codigo,
            p.nombre,
            c.nombre AS categoria,
            s.nombre AS subcategoria,
            m.nombre AS marca,
            v.nombre AS version,
            p.precio_compra,
            p.precio_venta,
            p.stock,
            p.eliminado
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id_subcategoria
        LEFT JOIN marcas m ON p.marca_id = m.id_marca
        LEFT JOIN versiones v ON p.version_id = v.id_version
        ORDER BY p.nombre
    """).fetchall()
    conn.close()
    return render_template("admin.html", productos=productos)

# -------------------
# NUEVO PRODUCTO
# -------------------
def generar_codigo():
    return str(random.randint(100000, 999999))

def generar_numero_lote():
    """Genera un número de lote único con formato LOTE-YYYYMMDD-XXXX"""
    fecha = datetime.now().strftime("%Y%m%d")
    # Obtener el último número de secuencia para hoy
    conn = get_db_connection()
    ultimo_lote = conn.execute("""
        SELECT numero_lote FROM lotes 
        WHERE numero_lote LIKE ? 
        ORDER BY numero_lote DESC 
        LIMIT 1
    """, (f"LOTE-{fecha}-%",)).fetchone()
    conn.close()
    
    if ultimo_lote:
        # Extraer el número de secuencia del último lote
        try:
            ultimo_numero = int(ultimo_lote[0].split('-')[-1])
            nuevo_numero = ultimo_numero + 1
        except:
            nuevo_numero = 1
    else:
        nuevo_numero = 1
    
    return f"LOTE-{fecha}-{nuevo_numero:04d}"

@app.route("/nuevo_producto", methods=["GET", "POST"])
@login_required
def nuevo_producto():
    conn = get_db_connection()
    categorias = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()

    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria_id = request.form.get("categoria_id") or None
        subcategoria_id = request.form.get("subcategoria_id") or None
        marca_id = request.form.get("marca_id") or None
        version_id = request.form.get("version_id") or None
        precio_compra = request.form.get("precio_compra", 0)
        precio_venta = request.form.get("precio_venta", 0)

        codigo = generar_codigo()
        while conn.execute("SELECT 1 FROM productos WHERE codigo = ?", (codigo,)).fetchone():
            codigo = generar_codigo()

        conn.execute("""
            INSERT INTO productos (codigo, nombre, categoria_id, subcategoria_id, marca_id, version_id, precio_compra, precio_venta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (codigo, nombre, categoria_id, subcategoria_id, marca_id, version_id, precio_compra, precio_venta))

        conn.commit()
        conn.close()
        flash("Producto creado correctamente", "success")
        return redirect(url_for("admin"))

    conn.close()
    return render_template("nuevo_producto.html", categorias=categorias)

# -------------------
# CATEGORÍAS
# -------------------
@app.route("/categorias")
@login_required
def listar_categorias():
    conn = get_db_connection()
    categorias = conn.execute("""
        SELECT c.*, COUNT(s.id_subcategoria) as total_subcategorias
        FROM categorias c
        LEFT JOIN subcategorias s ON c.id_categoria = s.categoria_id
        GROUP BY c.id_categoria
        ORDER BY c.nombre
    """).fetchall()
    
    # Obtener toda la jerarquía para mostrar en la página
    jerarquia_completa = conn.execute("""
        SELECT 
            c.id_categoria, c.nombre as categoria_nombre,
            s.id_subcategoria, s.nombre as subcategoria_nombre,
            m.id_marca, m.nombre as marca_nombre,
            v.id_version, v.nombre as version_nombre
        FROM categorias c
        LEFT JOIN subcategorias s ON c.id_categoria = s.categoria_id
        LEFT JOIN marcas m ON s.id_subcategoria = m.subcategoria_id
        LEFT JOIN versiones v ON m.id_marca = v.marca_id
        ORDER BY c.nombre, s.nombre, m.nombre, v.nombre
    """).fetchall()
    
    conn.close()
    return render_template("categorias.html", categorias=categorias, jerarquia=jerarquia_completa)

@app.route("/nueva_categoria", methods=["GET", "POST"])
def nueva_categoria():
    if request.method == "POST":
        nombre = request.form["nombre"]
        conn = get_db_connection()
        conn.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
        conn.commit()
        conn.close()
        return redirect(url_for("listar_categorias"))
    return render_template("nueva_categoria.html")

# -------------------
# SUBCATEGORÍAS
# -------------------
@app.route("/subcategorias")
def listar_subcategorias():
    conn = get_db_connection()
    subcategorias = conn.execute("""
        SELECT s.*, c.nombre as categoria_nombre
        FROM subcategorias s
        JOIN categorias c ON s.categoria_id = c.id_categoria
        ORDER BY c.nombre, s.nombre
    """).fetchall()
    conn.close()
    return render_template("subcategorias.html", subcategorias=subcategorias)

@app.route("/nueva_subcategoria", methods=["GET", "POST"])
def nueva_subcategoria():
    conn = get_db_connection()
    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria_id = request.form["categoria_id"]
        conn.execute("INSERT INTO subcategorias (nombre, categoria_id) VALUES (?, ?)", (nombre, categoria_id))
        conn.commit()
        conn.close()
        return redirect(url_for("listar_subcategorias"))
    
    categorias = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    conn.close()
    return render_template("nueva_subcategoria.html", categorias=categorias)

@app.route("/api/subcategorias/<int:categoria_id>")
def api_subcategorias(categoria_id):
    conn = get_db_connection()
    subcategorias = conn.execute("""
        SELECT id_subcategoria, nombre 
        FROM subcategorias 
        WHERE categoria_id = ? 
        ORDER BY nombre
    """, (categoria_id,)).fetchall()
    conn.close()
    
    return jsonify([{
        'id_subcategoria': s.id_subcategoria,
        'nombre': s.nombre
    } for s in subcategorias])

# -------------------
# EDITAR PRODUCTO
# -------------------
@app.route("/editar_producto/<int:id_producto>", methods=["GET", "POST"])
def editar_producto(id_producto):
    conn = get_db_connection()
    producto = conn.execute("SELECT * FROM productos WHERE id_producto = ?", (id_producto,)).fetchone()
    categorias = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    
    # Obtener subcategorías de la categoría del producto
    subcategorias = []
    if producto and producto['categoria_id']:
        subcategorias = conn.execute("""
            SELECT * FROM subcategorias 
            WHERE categoria_id = ? 
            ORDER BY nombre
        """, (producto['categoria_id'],)).fetchall()

    if not producto:
        conn.close()
        flash("Producto no encontrado", "danger")
        return redirect(url_for("admin"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria_id = request.form.get("categoria_id") or None
        subcategoria_id = request.form.get("subcategoria_id") or None
        marca_id = request.form.get("marca_id") or None
        version_id = request.form.get("version_id") or None
        precio_compra = request.form.get("precio_compra", 0)
        precio_venta = request.form.get("precio_venta", 0)
        activo = 1 if request.form.get("activo") else 0

        conn.execute("""
            UPDATE productos
            SET nombre = ?, categoria_id = ?, subcategoria_id = ?, marca_id = ?, version_id = ?,
                precio_compra = ?, precio_venta = ?, activo = ?
            WHERE id_producto = ?
        """, (nombre, categoria_id, subcategoria_id, marca_id, version_id, precio_compra, precio_venta, activo, id_producto))

        conn.commit()
        conn.close()
        flash("Producto actualizado correctamente", "success")
        return redirect(url_for("admin"))

    conn.close()
    return render_template("editar_producto.html", producto=producto, categorias=categorias, subcategorias=subcategorias)

# -------------------
# LOTES
# -------------------
@app.route("/lotes")
def listar_lotes():
    conn = get_db_connection()
    lotes = conn.execute("""
        SELECT l.id_lote, l.numero_lote, l.nro_factura, l.fecha_factura, l.fecha_carga, l.observaciones,
               p.nombre AS proveedor,
               (SELECT COUNT(*) FROM lotes_detalles ld WHERE ld.id_lote = l.id_lote) AS cantidad_items
        FROM lotes l
        LEFT JOIN proveedores p ON l.id_proveedor = p.id_proveedor
        ORDER BY l.fecha_factura DESC
    """).fetchall()
    conn.close()
    return render_template("lotes.html", lotes=lotes)

@app.route("/nuevo_lote", methods=["GET", "POST"])
@login_required
def nuevo_lote():
    conn = get_db_connection()

    if request.method == "POST":
        nro_factura = request.form.get("nro_factura")
        id_proveedor = request.form.get("id_proveedor")
        fecha_factura = request.form.get("fecha_factura") or datetime.now().strftime("%Y-%m-%d")
        observaciones = request.form.get("observaciones")
        
        # Generar número de lote automático
        numero_lote = generar_numero_lote()

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lotes (numero_lote, nro_factura, id_proveedor, fecha_factura, observaciones)
            VALUES (?, ?, ?, ?, ?)
        """, (numero_lote, nro_factura, id_proveedor, fecha_factura, observaciones))
        id_lote = cursor.lastrowid

        # Procesar productos del lote
        nombres = request.form.getlist("nombre[]")
        marcas = request.form.getlist("marca[]")
        categoria_ids = request.form.getlist("categoria_id[]")
        cantidades = request.form.getlist("cantidad[]")
        precios_compra = request.form.getlist("precio_compra[]")
        precios_venta = request.form.getlist("precio_venta[]")
        codigos_existentes = request.form.getlist("codigo_existente[]")

        for i, (nombre, marca, categoria_id, cantidad, pcompra, pventa, codigo_existente) in enumerate(
            zip(nombres, marcas, categoria_ids, cantidades, precios_compra, precios_venta, codigos_existentes)
        ):
            if nombre and cantidad and pcompra and pventa:
                if codigo_existente:
                    # Producto existente - usar su ID
                    id_producto = int(codigo_existente)
                else:
                    # Producto nuevo - crearlo
                    codigo = generar_codigo()
                    while conn.execute("SELECT 1 FROM productos WHERE codigo = ?", (codigo,)).fetchone():
                        codigo = generar_codigo()
                    
                    # Obtener IDs de la nueva estructura
                    subcategorias_list = request.form.getlist("subcategoria_id[]")
                    marcas_list = request.form.getlist("marca_id[]")
                    versiones_list = request.form.getlist("version_id[]")
                    
                    subcategoria_id = subcategorias_list[i] if i < len(subcategorias_list) and subcategorias_list[i] else None
                    marca_id = marcas_list[i] if i < len(marcas_list) and marcas_list[i] else None
                    version_id = versiones_list[i] if i < len(versiones_list) and versiones_list[i] else None
                    
                    cursor.execute("""
                        INSERT INTO productos (codigo, nombre, categoria_id, subcategoria_id, marca_id, version_id, precio_compra, precio_venta)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (codigo, nombre, categoria_id or None, subcategoria_id, marca_id, version_id, float(pcompra), float(pventa)))
                    id_producto = cursor.lastrowid

                # Agregar detalle del lote
                cursor.execute("""
                    INSERT INTO lotes_detalles (id_lote, id_producto, cantidad, precio_compra, precio_venta)
                    VALUES (?, ?, ?, ?, ?)
                """, (id_lote, id_producto, int(cantidad), float(pcompra), float(pventa)))
                
                # Actualizar el stock del producto
                cursor.execute("""
                    UPDATE productos 
                    SET stock = stock + ? 
                    WHERE id_producto = ?
                """, (int(cantidad), id_producto))

        conn.commit()
        conn.close()
        flash(f"Lote {numero_lote} creado correctamente con todos los productos.", "success")
        return redirect(url_for("ver_lote", id_lote=id_lote))

    # Generar número de lote para mostrar
    numero_lote = generar_numero_lote()
    proveedores = conn.execute("SELECT id_proveedor, nombre FROM proveedores").fetchall()
    categorias = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    subcategorias = conn.execute("SELECT * FROM subcategorias ORDER BY nombre").fetchall()
    marcas = conn.execute("SELECT * FROM marcas ORDER BY nombre").fetchall()
    versiones = conn.execute("SELECT * FROM versiones ORDER BY nombre").fetchall()
    productos_existentes = conn.execute("""
        SELECT p.id_producto, p.codigo, p.nombre, p.precio_venta, 
               c.nombre as categoria, s.nombre as subcategoria, m.nombre as marca, v.nombre as version
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id_subcategoria
        LEFT JOIN marcas m ON p.marca_id = m.id_marca
        LEFT JOIN versiones v ON p.version_id = v.id_version
        WHERE p.activo = 1 AND p.eliminado = 0
        ORDER BY p.nombre
    """).fetchall()
    conn.close()
    
    # Convertir objetos Row a diccionarios para JSON serialization
    categorias_dict = [dict(cat) for cat in categorias]
    subcategorias_dict = [dict(sub) for sub in subcategorias]
    marcas_dict = [dict(marca) for marca in marcas]
    versiones_dict = [dict(version) for version in versiones]
    proveedores_dict = [dict(prov) for prov in proveedores]
    productos_dict = [dict(prod) for prod in productos_existentes]
    
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("nuevo_lote.html", 
                         numero_lote=numero_lote,
                         proveedores=proveedores_dict, 
                         categorias=categorias_dict,
                         subcategorias=subcategorias_dict,
                         marcas=marcas_dict,
                         versiones=versiones_dict,
                         productos_existentes=productos_dict,
                         today=today)

@app.route("/ver_lote/<int:id_lote>")
def ver_lote(id_lote):
    conn = get_db_connection()
    
    # Obtener información del lote
    lote = conn.execute("""
        SELECT l.*, p.nombre AS proveedor_nombre
        FROM lotes l
        LEFT JOIN proveedores p ON l.id_proveedor = p.id_proveedor
        WHERE l.id_lote = ?
    """, (id_lote,)).fetchone()
    
    if not lote:
        conn.close()
        flash("Lote no encontrado", "danger")
        return redirect(url_for("listar_lotes"))
    
    # Obtener detalles del lote
    detalles = conn.execute("""
        SELECT ld.*, p.codigo, p.nombre AS producto_nombre,
               c.nombre AS categoria, s.nombre AS subcategoria, m.nombre AS marca, v.nombre AS version
        FROM lotes_detalles ld
        JOIN productos p ON ld.id_producto = p.id_producto
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id_subcategoria
        LEFT JOIN marcas m ON p.marca_id = m.id_marca
        LEFT JOIN versiones v ON p.version_id = v.id_version
        WHERE ld.id_lote = ?
        ORDER BY p.nombre
    """, (id_lote,)).fetchall()
    
    conn.close()
    return render_template("ver_lote.html", lote=lote, detalles=detalles)

# -------------------
# EDITAR LOTE
# -------------------
@app.route("/editar_lote/<int:id_lote>", methods=["GET", "POST"])
def editar_lote(id_lote):
    conn = get_db_connection()
    
    # Obtener información del lote
    lote = conn.execute("""
        SELECT l.*, p.nombre AS proveedor_nombre
        FROM lotes l
        LEFT JOIN proveedores p ON l.id_proveedor = p.id_proveedor
        WHERE l.id_lote = ?
    """, (id_lote,)).fetchone()
    
    if not lote:
        conn.close()
        flash("Lote no encontrado", "danger")
        return redirect(url_for("listar_lotes"))
    
    if request.method == "POST":
        nro_factura = request.form.get("nro_factura")
        id_proveedor = request.form.get("id_proveedor")
        observaciones = request.form.get("observaciones")
        fecha = request.form.get("fecha")
        
        # Actualizar información del lote
        conn.execute("""
            UPDATE lotes 
            SET nro_factura = ?, id_proveedor = ?, fecha = ?, observaciones = ?
            WHERE id_lote = ?
        """, (nro_factura, id_proveedor, fecha, observaciones, id_lote))
        
        # Eliminar detalles existentes
        conn.execute("DELETE FROM lotes_detalles WHERE id_lote = ?", (id_lote,))
        
        # Insertar nuevos detalles
        productos = request.form.getlist("producto_id[]")
        cantidades = request.form.getlist("cantidad[]")
        precios_compra = request.form.getlist("precio_compra[]")
        precios_venta = request.form.getlist("precio_venta[]")
        
        for prod_id, cantidad, pcompra, pventa in zip(productos, cantidades, precios_compra, precios_venta):
            if prod_id and cantidad:
                conn.execute("""
                    INSERT INTO lotes_detalles (id_lote, id_producto, cantidad, precio_compra, precio_venta)
                    VALUES (?, ?, ?, ?, ?)
                """, (id_lote, int(prod_id), int(cantidad), float(pcompra or 0), float(pventa or 0)))
        
        conn.commit()
        conn.close()
        flash("Lote actualizado correctamente.", "success")
        return redirect(url_for("ver_lote", id_lote=id_lote))
    
    # Obtener detalles actuales del lote
    detalles = conn.execute("""
        SELECT ld.*, p.codigo, p.nombre AS producto_nombre, p.precio_compra, p.precio_venta
        FROM lotes_detalles ld
        JOIN productos p ON ld.id_producto = p.id_producto
        WHERE ld.id_lote = ?
        ORDER BY p.nombre
    """, (id_lote,)).fetchall()
    
    # Datos para el formulario
    proveedores = conn.execute("SELECT id_proveedor, nombre FROM proveedores").fetchall()
    productos = conn.execute("SELECT id_producto, nombre, codigo, precio_compra, precio_venta FROM productos WHERE activo=1").fetchall()
    categorias = conn.execute("SELECT * FROM categorias").fetchall()
    conn.close()
    
    # Convertir objetos Row a diccionarios para JSON serialization
    proveedores_dict = [dict(prov) for prov in proveedores]
    productos_dict = [dict(prod) for prod in productos]
    categorias_dict = [dict(cat) for cat in categorias]
    
    return render_template("editar_lote.html", 
                         lote=lote, 
                         detalles=detalles,
                         proveedores=proveedores_dict, 
                         productos=productos_dict, 
                         categorias=categorias_dict)

# -------------------
# ELIMINAR LOTE
# -------------------
@app.route("/eliminar_lote/<int:id_lote>")
def eliminar_lote(id_lote):
    conn = get_db_connection()
    
    # Verificar que el lote existe
    lote = conn.execute("SELECT id_lote FROM lotes WHERE id_lote = ?", (id_lote,)).fetchone()
    if not lote:
        conn.close()
        flash("Lote no encontrado", "danger")
        return redirect(url_for("listar_lotes"))
    
    # Obtener detalles del lote para revertir el stock
    detalles = conn.execute("""
        SELECT id_producto, cantidad 
        FROM lotes_detalles 
        WHERE id_lote = ?
    """, (id_lote,)).fetchall()
    
    # Revertir el stock de cada producto
    for detalle in detalles:
        id_producto, cantidad = detalle
        conn.execute("""
            UPDATE productos 
            SET stock = stock - ? 
            WHERE id_producto = ?
        """, (cantidad, id_producto))
    
    # Eliminar detalles del lote
    conn.execute("DELETE FROM lotes_detalles WHERE id_lote = ?", (id_lote,))
    
    # Eliminar el lote
    conn.execute("DELETE FROM lotes WHERE id_lote = ?", (id_lote,))
    
    conn.commit()
    conn.close()
    flash("Lote eliminado correctamente.", "success")
    return redirect(url_for("listar_lotes"))

# -------------------
# GESTIÓN DE CLIENTES
# -------------------
@app.route("/clientes")
@login_required
def listar_clientes():
    conn = get_db_connection()
    clientes = conn.execute("""
        SELECT c.*, 
               COUNT(v.id_venta) as total_ventas,
               COALESCE(SUM(v.total_venta), 0) as total_comprado
        FROM clientes c
        LEFT JOIN ventas v ON c.id_cliente = v.id_cliente
        GROUP BY c.id_cliente
        ORDER BY c.nombre
    """).fetchall()
    conn.close()
    return render_template("clientes.html", clientes=clientes)

@app.route("/prestamos_personales")
@login_required
def prestamos_personales():
    conn = get_db_connection()
    prestamos = conn.execute("""
        SELECT 
            c.id_cliente,
            c.nombre as cliente_nombre,
            c.telefono,
            c.email,
            COUNT(v.id_venta) as total_facturas,
            COALESCE(SUM(v.total_venta), 0) as total_deuda,
            MAX(v.fecha_venta) as ultima_compra
        FROM clientes c
        INNER JOIN ventas v ON c.id_cliente = v.id_cliente
        WHERE v.metodo_pago = 'Préstamo Personal'
        GROUP BY c.id_cliente
        ORDER BY total_deuda DESC
    """).fetchall()
    
    # Obtener detalles de las facturas para cada cliente
    detalles_prestamos = {}
    for prestamo in prestamos:
        facturas = conn.execute("""
            SELECT 
                v.id_venta,
                v.fecha_venta,
                v.total_venta,
                v.observaciones
            FROM ventas v
            WHERE v.id_cliente = ? AND v.metodo_pago = 'Préstamo Personal'
            ORDER BY v.fecha_venta DESC
        """, (prestamo['id_cliente'],)).fetchall()
        detalles_prestamos[prestamo['id_cliente']] = facturas
    
    conn.close()
    return render_template("prestamos_personales.html", prestamos=prestamos, detalles_prestamos=detalles_prestamos)

@app.route("/nuevo_cliente", methods=["GET", "POST"])
def nuevo_cliente():
    if request.method == "POST":
        nombre = request.form["nombre"]
        telefono = request.form.get("telefono", "")
        email = request.form.get("email", "")
        direccion = request.form.get("direccion", "")
        
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO clientes (nombre, telefono, email, direccion)
            VALUES (?, ?, ?, ?)
        """, (nombre, telefono, email, direccion))
        conn.commit()
        conn.close()
        
        flash("Cliente creado correctamente", "success")
        return redirect(url_for("listar_clientes"))
    
    return render_template("nuevo_cliente.html")

# -------------------
# SISTEMA DE VENTAS
# -------------------
@app.route("/ventas")
@login_required
def listar_ventas():
    conn = get_db_connection()
    ventas = conn.execute("""
        SELECT v.*, c.nombre AS cliente_nombre,
               (SELECT COUNT(*) FROM ventas_detalles vd WHERE vd.id_venta = v.id_venta) AS items
        FROM ventas v
        LEFT JOIN clientes c ON v.id_cliente = c.id_cliente
        ORDER BY v.fecha_venta DESC, v.fecha_registro DESC
    """).fetchall()
    conn.close()
    return render_template("ventas.html", ventas=ventas)

@app.route("/nueva_venta", methods=["GET", "POST"])
@login_required
def nueva_venta():
    conn = get_db_connection()
    
    if request.method == "POST":
        id_cliente = request.form.get("id_cliente") or None
        fecha_venta = request.form.get("fecha_venta") or datetime.now().strftime("%Y-%m-%d")
        metodo_pago = request.form.get("metodo_pago", "Efectivo")
        observaciones = request.form.get("observaciones", "")
        
        # Crear la venta
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ventas (id_cliente, fecha_venta, metodo_pago, observaciones)
            VALUES (?, ?, ?, ?)
        """, (id_cliente, fecha_venta, metodo_pago, observaciones))
        id_venta = cursor.lastrowid
        
        # Procesar productos de la venta
        productos = request.form.getlist("producto_id[]")
        cantidades = request.form.getlist("cantidad[]")
        precios = request.form.getlist("precio[]")
        
        total_venta = 0
        for prod_id, cantidad, precio in zip(productos, cantidades, precios):
            if prod_id and cantidad and precio:
                cantidad = int(cantidad)
                precio = float(precio)
                subtotal = cantidad * precio
                total_venta += subtotal
                
                # Verificar stock disponible
                stock_actual = conn.execute("SELECT stock FROM productos WHERE id_producto = ?", (prod_id,)).fetchone()[0]
                if stock_actual < cantidad:
                    conn.rollback()
                    conn.close()
                    flash(f"Stock insuficiente para el producto seleccionado. Stock disponible: {stock_actual}", "error")
                    return redirect(url_for("nueva_venta"))
                
                cursor.execute("""
                    INSERT INTO ventas_detalles (id_venta, id_producto, cantidad, precio_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, (id_venta, int(prod_id), cantidad, precio, subtotal))
                
                # Actualizar el stock del producto
                cursor.execute("""
                    UPDATE productos 
                    SET stock = stock - ? 
                    WHERE id_producto = ?
                """, (cantidad, int(prod_id)))
        
        # Actualizar el total de la venta
        cursor.execute("""
            UPDATE ventas 
            SET total_venta = ? 
            WHERE id_venta = ?
        """, (total_venta, id_venta))
        
        conn.commit()
        conn.close()
        flash("Venta registrada correctamente", "success")
        return redirect(url_for("ver_venta", id_venta=id_venta))
    
    # Obtener datos para el formulario
    clientes = conn.execute("SELECT id_cliente, nombre FROM clientes ORDER BY nombre").fetchall()
    productos = conn.execute("""
        SELECT p.id_producto, p.codigo, p.nombre, p.precio_venta, p.stock, 
               c.nombre AS categoria, s.nombre AS subcategoria, m.nombre AS marca, v.nombre AS version
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id_subcategoria
        LEFT JOIN marcas m ON p.marca_id = m.id_marca
        LEFT JOIN versiones v ON p.version_id = v.id_version
        WHERE p.activo = 1 AND p.eliminado = 0 AND p.stock > 0
        ORDER BY p.nombre
    """).fetchall()
    conn.close()
    
    # Convertir objetos Row a diccionarios para JSON serialization
    clientes_dict = [dict(cli) for cli in clientes]
    productos_dict = [dict(prod) for prod in productos]
    
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("nueva_venta.html", 
                         clientes=clientes_dict, 
                         productos=productos_dict,
                         today=today)

@app.route("/ver_venta/<int:id_venta>")
def ver_venta(id_venta):
    conn = get_db_connection()
    
    # Obtener información de la venta
    venta = conn.execute("""
        SELECT v.*, c.nombre AS cliente_nombre, c.telefono, c.email
        FROM ventas v
        LEFT JOIN clientes c ON v.id_cliente = c.id_cliente
        WHERE v.id_venta = ?
    """, (id_venta,)).fetchone()
    
    if not venta:
        conn.close()
        flash("Venta no encontrada", "danger")
        return redirect(url_for("listar_ventas"))
    
    # Obtener detalles de la venta
    detalles = conn.execute("""
        SELECT vd.*, p.codigo, p.nombre AS producto_nombre
        FROM ventas_detalles vd
        JOIN productos p ON vd.id_producto = p.id_producto
        WHERE vd.id_venta = ?
        ORDER BY p.nombre
    """, (id_venta,)).fetchall()
    
    conn.close()
    return render_template("ver_venta.html", venta=venta, detalles=detalles)

@app.route("/eliminar_venta/<int:id_venta>")
def eliminar_venta(id_venta):
    conn = get_db_connection()
    
    # Verificar que la venta existe
    venta = conn.execute("SELECT id_venta FROM ventas WHERE id_venta = ?", (id_venta,)).fetchone()
    if not venta:
        conn.close()
        flash("Venta no encontrada", "danger")
        return redirect(url_for("listar_ventas"))
    
    # Obtener detalles de la venta para revertir el stock
    detalles = conn.execute("""
        SELECT id_producto, cantidad 
        FROM ventas_detalles 
        WHERE id_venta = ?
    """, (id_venta,)).fetchall()
    
    # Revertir el stock de cada producto
    for detalle in detalles:
        id_producto, cantidad = detalle
        conn.execute("""
            UPDATE productos 
            SET stock = stock + ? 
            WHERE id_producto = ?
        """, (cantidad, id_producto))
    
    # Eliminar detalles de la venta
    conn.execute("DELETE FROM ventas_detalles WHERE id_venta = ?", (id_venta,))
    
    # Eliminar la venta
    conn.execute("DELETE FROM ventas WHERE id_venta = ?", (id_venta,))
    
    conn.commit()
    conn.close()
    flash("Venta eliminada correctamente", "success")
    return redirect(url_for("listar_ventas"))

# -------------------
# API PARA VENTAS
# -------------------
@app.route("/api/productos_venta")
def api_productos_venta():
    conn = get_db_connection()
    productos = conn.execute("""
        SELECT p.id_producto, p.codigo, p.nombre, p.precio_venta, p.stock, 
               c.nombre AS categoria, s.nombre AS subcategoria, m.nombre AS marca, v.nombre AS version
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id_subcategoria
        LEFT JOIN marcas m ON p.marca_id = m.id_marca
        LEFT JOIN versiones v ON p.version_id = v.id_version
        WHERE p.activo = 1 AND p.eliminado = 0 AND p.stock > 0
        ORDER BY p.nombre
    """).fetchall()
    conn.close()
    
    return jsonify([{
        'id_producto': p.id_producto,
        'codigo': p.codigo,
        'nombre': p.nombre,
        'precio_venta': p.precio_venta,
        'stock': p.stock,
        'categoria': p.categoria,
        'subcategoria': p.subcategoria,
        'marca': p.marca,
        'version': p.version
    } for p in productos])

@app.route("/api/clientes", methods=["POST"])
def api_crear_cliente():
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        telefono = data.get("telefono", "")
        email = data.get("email", "")
        direccion = data.get("direccion", "")
        
        if not nombre:
            return jsonify({"success": False, "message": "El nombre es obligatorio"})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clientes (nombre, telefono, email, direccion)
            VALUES (?, ?, ?, ?)
        """, (nombre, telefono, email, direccion))
        
        id_cliente = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "cliente": {
                "id_cliente": id_cliente,
                "nombre": nombre,
                "telefono": telefono,
                "email": email,
                "direccion": direccion
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# -------------------
# GENERAR CÓDIGOS DE BARRAS
# -------------------
@app.route("/generar_codigos")
def generar_codigos():
    conn = get_db_connection()
    productos = conn.execute("""
        SELECT p.id_producto, p.codigo, p.nombre, p.precio_venta, 
               c.nombre AS categoria, s.nombre AS subcategoria, m.nombre AS marca, v.nombre AS version
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id_subcategoria
        LEFT JOIN marcas m ON p.marca_id = m.id_marca
        LEFT JOIN versiones v ON p.version_id = v.id_version
        WHERE p.activo = 1 AND p.eliminado = 0
        ORDER BY p.nombre
    """).fetchall()
    conn.close()
    
    # Convertir objetos Row a diccionarios para JSON serialization
    productos_dict = [dict(prod) for prod in productos]
    
    return render_template("generar_codigos.html", productos=productos_dict)

@app.route("/generar_pdf_codigos", methods=["POST"])
def generar_pdf_codigos():
    try:
        carrito_data = request.form.get('carrito')
        if not carrito_data:
            flash("No hay productos seleccionados", "error")
            return redirect(url_for("generar_codigos"))
        
        carrito = json.loads(carrito_data)
        if not carrito:
            flash("El carrito está vacío", "error")
            return redirect(url_for("generar_codigos"))
        
        # Crear el PDF en memoria
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Configuración de la página
        margin = 1 * cm
        label_width = 4 * cm
        label_height = 3 * cm
        cols = int((width - 2 * margin) / label_width)
        rows = int((height - 2 * margin) / label_height)
        labels_per_page = cols * rows
        
        current_label = 0
        page = 1
        
        for item in carrito:
            for i in range(item['cantidad']):
                if current_label % labels_per_page == 0 and current_label > 0:
                    p.showPage()
                    page += 1
                
                # Calcular posición del label
                label_index = current_label % labels_per_page
                col = label_index % cols
                row = label_index // cols
                
                x = margin + col * label_width
                y = height - margin - (row + 1) * label_height
                
                # Dibujar borde del label
                p.rect(x, y, label_width, label_height)
                
                # Información del producto - Nuevo layout
                p.setFont("Helvetica", 8)
                
                # Nombre del producto con información completa - PARTE SUPERIOR
                nombre_completo = item['nombre']
                if item.get('subcategoria'):
                    nombre_completo += f" - {item['subcategoria']}"
                if item.get('marca'):
                    nombre_completo += f" - {item['marca']}"
                if item.get('version'):
                    nombre_completo += f" - {item['version']}"
                
                if len(nombre_completo) > 25:
                    nombre_completo = nombre_completo[:22] + "..."
                p.drawString(x + 0.1 * cm, y + label_height - 0.5 * cm, nombre_completo)
                
                # Código de barras - PARTE CENTRAL (se dibuja después)
                
                # Precio de venta - PARTE INFERIOR
                p.drawString(x + 0.1 * cm, y + 0.2 * cm, f"${item['precio']:.2f}")
                
                # Generar código de barras real (Code128)
                try:
                    # Crear código de barras
                    barcode_instance = code128.Code128(item['codigo'], barHeight=0.6*cm, barWidth=0.02*cm)
                    barcode_drawing = Drawing()
                    barcode_drawing.add(barcode_instance)
                    
                    # Posicionar el código de barras
                    bar_x = x + 0.5 * cm
                    bar_y = y + 0.3 * cm
                    barcode_drawing.drawOn(p, bar_x, bar_y)
                    
                except Exception as barcode_error:
                    # Fallback: dibujar líneas simulando código de barras
                    p.setLineWidth(0.5)
                    bar_x = x + 0.5 * cm
                    bar_y = y + 0.5 * cm
                    bar_width = label_width - 1 * cm
                    bar_height = 0.8 * cm
                    
                    for j in range(20):
                        line_x = bar_x + (j * bar_width / 20)
                        line_height = random.uniform(0.2, bar_height)
                        p.line(line_x, bar_y, line_x, bar_y + line_height)
                
                current_label += 1
        
        p.save()
        buffer.seek(0)
        
        # Generar nombre de archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"codigos_barras_{timestamp}.pdf"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f"Error al generar PDF: {str(e)}", "error")
        return redirect(url_for("generar_codigos"))

# -------------------
# ELIMINAR PRODUCTO
# -------------------
@app.route("/eliminar/<int:id_producto>")
def eliminar_producto(id_producto):
    conn = get_db_connection()
    conn.execute("UPDATE productos SET eliminado = 1 WHERE id_producto = ?", (id_producto,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

# -------------------
# DASHBOARD
# -------------------
@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    
    # Estadísticas generales
    total_productos = conn.execute("SELECT COUNT(*) FROM productos WHERE eliminado = 0").fetchone()[0]
    productos_activos = conn.execute("SELECT COUNT(*) FROM productos WHERE activo = 1 AND eliminado = 0").fetchone()[0]
    total_categorias = conn.execute("SELECT COUNT(*) FROM categorias").fetchone()[0]
    total_proveedores = conn.execute("SELECT COUNT(*) FROM proveedores").fetchone()[0]
    total_lotes = conn.execute("SELECT COUNT(*) FROM lotes").fetchone()[0]
    total_clientes = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    total_ventas = conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]
    
    # Productos con stock bajo (menos de 3 unidades)
    stock_bajo = conn.execute("SELECT COUNT(*) FROM productos WHERE stock < 3 AND eliminado = 0").fetchone()[0]
    
    # Valor total del inventario
    valor_inventario = conn.execute("""
        SELECT COALESCE(SUM(stock * precio_venta), 0) 
        FROM productos 
        WHERE eliminado = 0
    """).fetchone()[0]
    
    # Lotes recientes (últimos 5)
    lotes_recientes = conn.execute("""
        SELECT l.id_lote, l.nro_factura, l.fecha_factura, p.nombre AS proveedor,
               (SELECT COUNT(*) FROM lotes_detalles ld WHERE ld.id_lote = l.id_lote) AS items
        FROM lotes l
        LEFT JOIN proveedores p ON l.id_proveedor = p.id_proveedor
        ORDER BY l.fecha_factura DESC
        LIMIT 5
    """).fetchall()
    
    # Ventas recientes (últimas 5)
    ventas_recientes = conn.execute("""
        SELECT v.id_venta, v.fecha_venta, v.total_venta, c.nombre AS cliente,
               (SELECT COUNT(*) FROM ventas_detalles vd WHERE vd.id_venta = v.id_venta) AS items
        FROM ventas v
        LEFT JOIN clientes c ON v.id_cliente = c.id_cliente
        ORDER BY v.fecha_venta DESC, v.fecha_registro DESC
        LIMIT 5
    """).fetchall()
    
    # Estadísticas de préstamos personales
    total_prestamos = conn.execute("""
        SELECT COUNT(DISTINCT v.id_cliente) as total_clientes_prestamo,
               COALESCE(SUM(v.total_venta), 0) as total_deuda_prestamos
        FROM ventas v
        WHERE v.metodo_pago = 'Préstamo Personal'
    """).fetchone()
    
    # Productos más vendidos (por stock más bajo)
    productos_populares = conn.execute("""
        SELECT p.codigo, p.nombre, p.stock, c.nombre AS categoria
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria
        WHERE p.eliminado = 0
        ORDER BY p.stock ASC
        LIMIT 10
    """).fetchall()
    
    conn.close()
    
    return render_template("dashboard.html",
                         total_productos=total_productos,
                         productos_activos=productos_activos,
                         total_categorias=total_categorias,
                         total_proveedores=total_proveedores,
                         total_lotes=total_lotes,
                         total_clientes=total_clientes,
                         total_ventas=total_ventas,
                         stock_bajo=stock_bajo,
                         valor_inventario=valor_inventario,
                         lotes_recientes=lotes_recientes,
                         ventas_recientes=ventas_recientes,
                         productos_populares=productos_populares,
                         total_prestamos=total_prestamos)

# -------------------
# API ROUTES (EXISTENTES)
# -------------------
@app.route("/api/proveedores", methods=["POST"])
def api_crear_proveedor():
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        telefono = data.get("telefono", "")
        email = data.get("email", "")
        
        if not nombre:
            return jsonify({"success": False, "message": "El nombre es obligatorio"})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO proveedores (nombre, telefono, email)
            VALUES (?, ?, ?)
        """, (nombre, telefono, email))
        
        id_proveedor = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "proveedor": {
                "id_proveedor": id_proveedor,
                "nombre": nombre,
                "telefono": telefono,
                "email": email
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/productos", methods=["POST"])
def api_crear_producto():
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        categoria_id = data.get("categoria_id")
        precio_compra = data.get("precio_compra", 0)
        precio_venta = data.get("precio_venta", 0)
        
        if not nombre:
            return jsonify({"success": False, "message": "El nombre es obligatorio"})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generar código único
        codigo = generar_codigo()
        while conn.execute("SELECT 1 FROM productos WHERE codigo = ?", (codigo,)).fetchone():
            codigo = generar_codigo()
        
        cursor.execute("""
            INSERT INTO productos (codigo, nombre, categoria_id, precio_compra, precio_venta)
            VALUES (?, ?, ?, ?, ?)
        """, (codigo, nombre, categoria_id, precio_compra, precio_venta))
        
        id_producto = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "producto": {
                "id_producto": id_producto,
                "codigo": codigo,
                "nombre": nombre,
                "categoria_id": categoria_id,
                "precio_compra": precio_compra,
                "precio_venta": precio_venta
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/reportes")
def reportes():
    """Página principal de reportes"""
    return render_template("reportes.html")

@app.route("/reporte_ventas")
def reporte_ventas():
    """Reporte de ventas por período"""
    # Obtener parámetros de filtro
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Construir query con filtros
    query = """
    SELECT 
        v.id_venta,
        v.fecha_venta as fecha,
        c.nombre as cliente,
        COUNT(vd.id_detalle) as total_items,
        v.total_venta,
        v.metodo_pago,
        v.observaciones
    FROM ventas v
    LEFT JOIN clientes c ON v.id_cliente = c.id_cliente
    LEFT JOIN ventas_detalles vd ON v.id_venta = vd.id_venta
    WHERE 1=1
    """
    
    params = []
    if fecha_inicio:
        query += " AND v.fecha_venta >= ?"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND v.fecha_venta <= ?"
        params.append(fecha_fin)
    
    query += " GROUP BY v.id_venta ORDER BY v.fecha_venta DESC"
    
    cursor.execute(query, params)
    ventas = cursor.fetchall()
    
    # Calcular estadísticas
    total_ventas = len(ventas)
    total_ingresos = sum(venta[4] for venta in ventas) if ventas else 0
    
    # Ventas por método de pago
    cursor.execute("""
        SELECT metodo_pago, COUNT(*), SUM(total_venta)
        FROM ventas 
        GROUP BY metodo_pago
    """)
    ventas_por_pago = cursor.fetchall()
    
    conn.close()
    
    return render_template("reporte_ventas.html", 
                         ventas=ventas, 
                         total_ventas=total_ventas,
                         total_ingresos=total_ingresos,
                         ventas_por_pago=ventas_por_pago,
                         fecha_inicio=fecha_inicio,
                         fecha_fin=fecha_fin)

@app.route("/reporte_ganancias")
def reporte_ganancias():
    """Análisis de ganancias y márgenes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener ventas con detalles y costos
    cursor.execute("""
        SELECT 
            p.nombre as producto,
            p.codigo,
            cat.nombre as categoria,
            SUM(vd.cantidad) as total_vendido,
            SUM(vd.cantidad * vd.precio_unitario) as ingresos_totales,
            SUM(vd.cantidad * vd.precio_unitario - vd.cantidad * COALESCE(
                (SELECT AVG(ld.precio_compra) 
                 FROM lotes_detalles ld 
                 WHERE ld.id_producto = p.id_producto), 0
            )) as ganancia_estimada
        FROM ventas_detalles vd
        JOIN productos p ON vd.id_producto = p.id_producto
        LEFT JOIN categorias cat ON p.categoria_id = cat.id_categoria
        JOIN ventas v ON vd.id_venta = v.id_venta
        WHERE v.eliminado = 0
        GROUP BY p.id_producto
        ORDER BY ganancia_estimada DESC
    """)
    
    productos_ganancia = cursor.fetchall()
    
    # Calcular totales
    total_ingresos = sum(row[4] for row in productos_ganancia)
    total_ganancia = sum(row[5] for row in productos_ganancia)
    margen_promedio = (total_ganancia / total_ingresos * 100) if total_ingresos > 0 else 0
    
    # Productos con mayor margen
    cursor.execute("""
        SELECT 
            p.nombre,
            p.codigo,
            AVG(vd.precio_unitario) as precio_promedio_venta,
            AVG(COALESCE(ld.precio_compra, 0)) as precio_promedio_compra,
            (AVG(vd.precio_unitario) - AVG(COALESCE(ld.precio_compra, 0))) / AVG(vd.precio_unitario) * 100 as margen_porcentual
        FROM ventas_detalles vd
        JOIN productos p ON vd.id_producto = p.id_producto
        LEFT JOIN lotes_detalles ld ON p.id_producto = ld.id_producto
        JOIN ventas v ON vd.id_venta = v.id_venta
        WHERE v.eliminado = 0
        GROUP BY p.id_producto
        HAVING margen_porcentual > 0
        ORDER BY margen_porcentual DESC
        LIMIT 10
    """)
    
    mejores_margenes = cursor.fetchall()
    
    conn.close()
    
    return render_template("reporte_ganancias.html",
                         productos_ganancia=productos_ganancia,
                         total_ingresos=total_ingresos,
                         total_ganancia=total_ganancia,
                         margen_promedio=margen_promedio,
                         mejores_margenes=mejores_margenes)

@app.route("/reporte_productos")
def reporte_productos():
    """Análisis de productos más/menos vendidos y rotación de stock"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Productos más vendidos
    cursor.execute("""
        SELECT 
            p.nombre,
            p.codigo,
            cat.nombre as categoria,
            SUM(vd.cantidad) as total_vendido,
            SUM(vd.cantidad * vd.precio_unitario) as ingresos_totales,
            p.stock as stock_actual,
            ROUND(CAST(SUM(vd.cantidad) AS FLOAT) / p.stock * 100, 2) as rotacion_porcentual
        FROM ventas_detalles vd
        JOIN productos p ON vd.id_producto = p.id_producto
        LEFT JOIN categorias cat ON p.categoria_id = cat.id_categoria
        JOIN ventas v ON vd.id_venta = v.id_venta
        WHERE v.eliminado = 0 AND p.eliminado = 0
        GROUP BY p.id_producto
        ORDER BY total_vendido DESC
        LIMIT 20
    """)
    
    mas_vendidos = cursor.fetchall()
    
    # Productos menos vendidos (con stock)
    cursor.execute("""
        SELECT 
            p.nombre,
            p.codigo,
            cat.nombre as categoria,
            COALESCE(SUM(vd.cantidad), 0) as total_vendido,
            p.stock as stock_actual,
            p.precio_venta,
            ROUND(CAST(COALESCE(SUM(vd.cantidad), 0) AS FLOAT) / p.stock * 100, 2) as rotacion_porcentual
        FROM productos p
        LEFT JOIN categorias cat ON p.categoria_id = cat.id_categoria
        LEFT JOIN ventas_detalles vd ON p.id_producto = vd.id_producto
        LEFT JOIN ventas v ON vd.id_venta = v.id_venta AND v.eliminado = 0
        WHERE p.eliminado = 0 AND p.stock > 0
        GROUP BY p.id_producto
        ORDER BY total_vendido ASC, stock_actual DESC
        LIMIT 20
    """)
    
    menos_vendidos = cursor.fetchall()
    
    # Análisis de rotación por categoría
    cursor.execute("""
        SELECT 
            cat.nombre as categoria,
            COUNT(p.id_producto) as total_productos,
            AVG(p.stock) as stock_promedio,
            SUM(COALESCE(vd.cantidad, 0)) as total_vendido_categoria,
            ROUND(CAST(SUM(COALESCE(vd.cantidad, 0)) AS FLOAT) / AVG(p.stock) * 100, 2) as rotacion_categoria
        FROM categorias cat
        LEFT JOIN productos p ON cat.id_categoria = p.categoria_id AND p.eliminado = 0
        LEFT JOIN ventas_detalles vd ON p.id_producto = vd.id_producto
        LEFT JOIN ventas v ON vd.id_venta = v.id_venta AND v.eliminado = 0
        GROUP BY cat.id_categoria
        ORDER BY rotacion_categoria DESC
    """)
    
    rotacion_categorias = cursor.fetchall()
    
    conn.close()
    
    return render_template("reporte_productos.html",
                         mas_vendidos=mas_vendidos,
                         menos_vendidos=menos_vendidos,
                         rotacion_categorias=rotacion_categorias)

@app.route("/recomendaciones")
def recomendaciones():
    """Sistema inteligente de recomendaciones"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Productos con stock bajo que se venden bien
    cursor.execute("""
        SELECT 
            p.nombre,
            p.codigo,
            cat.nombre as categoria,
            p.stock as stock_actual,
            SUM(vd.cantidad) as vendido_ultimo_mes,
            ROUND(CAST(SUM(vd.cantidad) AS FLOAT) / 30, 1) as promedio_diario,
            CASE 
                WHEN p.stock < SUM(vd.cantidad) / 30 * 7 THEN 'CRÍTICO'
                WHEN p.stock < SUM(vd.cantidad) / 30 * 14 THEN 'BAJO'
                ELSE 'NORMAL'
            END as nivel_stock
        FROM productos p
        LEFT JOIN categorias cat ON p.categoria_id = cat.id_categoria
        LEFT JOIN ventas_detalles vd ON p.id_producto = vd.id_producto
        LEFT JOIN ventas v ON vd.id_venta = v.id_venta 
            AND v.eliminado = 0 
            AND v.fecha_venta >= datetime('now', '-30 days')
        WHERE p.eliminado = 0 AND p.stock > 0
        GROUP BY p.id_producto
        HAVING vendido_ultimo_mes > 0 AND stock_actual < vendido_ultimo_mes / 30 * 14
        ORDER BY (vendido_ultimo_mes / 30) / stock_actual DESC
        LIMIT 10
    """)
    
    stock_bajo = cursor.fetchall()
    
    # 2. Categorías con mayor demanda
    cursor.execute("""
        SELECT 
            cat.nombre as categoria,
            COUNT(DISTINCT p.id_producto) as productos_en_categoria,
            SUM(vd.cantidad) as total_vendido,
            ROUND(CAST(SUM(vd.cantidad) AS FLOAT) / COUNT(DISTINCT p.id_producto), 1) as promedio_por_producto,
            ROUND(CAST(SUM(vd.cantidad) AS FLOAT) / 30, 1) as promedio_diario_categoria
        FROM categorias cat
        LEFT JOIN productos p ON cat.id_categoria = p.categoria_id AND p.eliminado = 0
        LEFT JOIN ventas_detalles vd ON p.id_producto = vd.id_producto
        LEFT JOIN ventas v ON vd.id_venta = v.id_venta 
            AND v.eliminado = 0 
            AND v.fecha_venta >= datetime('now', '-30 days')
        GROUP BY cat.id_categoria
        HAVING total_vendido > 0
        ORDER BY total_vendido DESC
        LIMIT 5
    """)
    
    categorias_demandadas = cursor.fetchall()
    
    # 3. Productos con mayor margen que podrían venderse más
    cursor.execute("""
        SELECT 
            p.nombre,
            p.codigo,
            cat.nombre as categoria,
            p.stock as stock_actual,
            AVG(vd.precio_unitario) as precio_promedio_venta,
            AVG(COALESCE(ld.precio_compra, 0)) as precio_promedio_compra,
            (AVG(vd.precio_unitario) - AVG(COALESCE(ld.precio_compra, 0))) / AVG(vd.precio_unitario) * 100 as margen_porcentual,
            SUM(vd.cantidad) as total_vendido
        FROM productos p
        LEFT JOIN categorias cat ON p.categoria_id = cat.id_categoria
        LEFT JOIN ventas_detalles vd ON p.id_producto = vd.id_producto
        LEFT JOIN lotes_detalles ld ON p.id_producto = ld.id_producto
        LEFT JOIN ventas v ON vd.id_venta = v.id_venta AND v.eliminado = 0
        WHERE p.eliminado = 0 AND p.stock > 0
        GROUP BY p.id_producto
        HAVING margen_porcentual > 30 AND total_vendido < 50
        ORDER BY margen_porcentual DESC
        LIMIT 10
    """)
    
    alto_margen_baja_venta = cursor.fetchall()
    
    # 4. Análisis de estacionalidad (últimos 3 meses)
    cursor.execute("""
        SELECT 
            strftime('%Y-%m', v.fecha_venta) as mes,
            COUNT(DISTINCT v.id_venta) as total_ventas,
            SUM(v.total_venta) as ingresos_mes,
            COUNT(DISTINCT vd.id_producto) as productos_vendidos
        FROM ventas v
        LEFT JOIN ventas_detalles vd ON v.id_venta = vd.id_venta
        WHERE v.eliminado = 0 AND v.fecha_venta >= datetime('now', '-90 days')
        GROUP BY strftime('%Y-%m', v.fecha_venta)
        ORDER BY mes DESC
    """)
    
    tendencia_mensual = cursor.fetchall()
    
    conn.close()
    
    return render_template("recomendaciones.html",
                         stock_bajo=stock_bajo,
                         categorias_demandadas=categorias_demandadas,
                         alto_margen_baja_venta=alto_margen_baja_venta,
                         tendencia_mensual=tendencia_mensual)

@app.route("/api/categorias", methods=["POST"])
def api_crear_categoria():
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        
        if not nombre:
            return jsonify({"success": False, "message": "El nombre es obligatorio"})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO categorias (nombre)
            VALUES (?)
        """, (nombre,))
        
        id_categoria = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "categoria": {
                "id_categoria": id_categoria,
                "nombre": nombre
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/subcategorias", methods=["POST"])
def api_crear_subcategoria():
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        categoria_id = data.get("categoria_id")
        
        if not nombre:
            return jsonify({"success": False, "message": "El nombre es obligatorio"})
        
        if not categoria_id:
            return jsonify({"success": False, "message": "La categoría es obligatoria"})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO subcategorias (nombre, categoria_id)
            VALUES (?, ?)
        """, (nombre, categoria_id))
        
        id_subcategoria = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "subcategoria": {
                "id_subcategoria": id_subcategoria,
                "nombre": nombre,
                "categoria_id": categoria_id
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/subcategorias/<int:categoria_id>")
def api_subcategorias_por_categoria(categoria_id):
    conn = get_db_connection()
    subcategorias = conn.execute("""
        SELECT id_subcategoria, nombre 
        FROM subcategorias 
        WHERE categoria_id = ? 
        ORDER BY nombre
    """, (categoria_id,)).fetchall()
    conn.close()
    
    return jsonify([{
        'id_subcategoria': s.id_subcategoria,
        'nombre': s.nombre
    } for s in subcategorias])

@app.route("/api/marcas", methods=["POST"])
def api_crear_marca():
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        subcategoria_id = data.get("subcategoria_id")
        
        if not nombre or not subcategoria_id:
            return jsonify({"success": False, "message": "El nombre y la subcategoría son obligatorios"})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO marcas (nombre, subcategoria_id)
            VALUES (?, ?)
        """, (nombre, subcategoria_id))
        
        id_marca = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "marca": {
                "id_marca": id_marca,
                "nombre": nombre,
                "subcategoria_id": subcategoria_id
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/marcas/<int:subcategoria_id>")
def api_marcas_por_subcategoria(subcategoria_id):
    conn = get_db_connection()
    marcas = conn.execute("""
        SELECT id_marca, nombre 
        FROM marcas 
        WHERE subcategoria_id = ? 
        ORDER BY nombre
    """, (subcategoria_id,)).fetchall()
    conn.close()
    
    return jsonify([{
        'id_marca': m.id_marca,
        'nombre': m.nombre
    } for m in marcas])

@app.route("/api/versiones", methods=["POST"])
def api_crear_version():
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        marca_id = data.get("marca_id")
        
        if not nombre or not marca_id:
            return jsonify({"success": False, "message": "El nombre y la marca son obligatorios"})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO versiones (nombre, marca_id)
            VALUES (?, ?)
        """, (nombre, marca_id))
        
        id_version = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "version": {
                "id_version": id_version,
                "nombre": nombre,
                "marca_id": marca_id
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/versiones/<int:marca_id>")
def api_versiones_por_marca(marca_id):
    conn = get_db_connection()
    versiones = conn.execute("""
        SELECT id_version, nombre 
        FROM versiones 
        WHERE marca_id = ? 
        ORDER BY nombre
    """, (marca_id,)).fetchall()
    conn.close()
    
    return jsonify([{
        'id_version': v.id_version,
        'nombre': v.nombre
    } for v in versiones])

if __name__ == "__main__":
    app.run(debug=True)
