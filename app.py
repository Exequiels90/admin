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
import requests
import threading
import time

# Configuración de la aplicación
app = Flask(__name__)
app.config.from_object(config['production'] if os.environ.get('FLASK_ENV') == 'production' else config['development'])

DB_PATH = app.config['DATABASE_PATH']

# Filtro personalizado para formatear fechas
@app.template_filter('datetime')
def format_datetime(value):
    if value is None:
        return 'N/A'
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except:
            return value
    return value.strftime('%d/%m/%Y %H:%M')

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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('rol') != 'admin':
            flash("Acceso denegado. Se requieren permisos de administrador.", "error")
            return redirect(url_for('dashboard'))
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
# FUNCIONES DE SINCRONIZACIÓN
# -------------------

def generar_numero_lote():
    """Genera un número de lote único"""
    conn = get_db_connection()
    # Obtener el último número de lote
    ultimo_lote = conn.execute("SELECT numero_lote FROM lotes ORDER BY id_lote DESC LIMIT 1").fetchone()
    conn.close()
    
    if ultimo_lote:
        # Extraer el número del último lote (formato: LOTE-YYYYMMDD-XXX)
        try:
            partes = ultimo_lote[0].split('-')
            if len(partes) >= 3:
                ultimo_numero = int(partes[2])
                nuevo_numero = ultimo_numero + 1
            else:
                nuevo_numero = 1
        except:
            nuevo_numero = 1
    else:
        nuevo_numero = 1
    
    # Formato: LOTE-YYYYMMDD-XXX
    fecha_actual = datetime.now().strftime("%Y%m%d")
    return f"LOTE-{fecha_actual}-{nuevo_numero:03d}"

def generar_codigo():
    """Genera un código único para productos"""
    conn = get_db_connection()
    while True:
        # Generar código aleatorio de 8 dígitos
        codigo = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        
        # Verificar que no exista
        existe = conn.execute("SELECT 1 FROM productos WHERE codigo = ?", (codigo,)).fetchone()
        if not existe:
            conn.close()
            return codigo
    conn.close()

def sync_with_pos_clients():
    """Sincroniza datos con clientes POS"""
    try:
        conn = get_db_connection()
        
        # Obtener productos activos para sincronizar
        productos = conn.execute("""
            SELECT 
                id_producto, codigo, nombre, precio_venta, stock, 
                categoria_id, subcategoria_id, marca_id, version_id,
                es_pesable, unidad_medida, activo
            FROM productos 
            WHERE activo = 1 AND eliminado = 0
        """).fetchall()
        
        # Obtener clientes POS registrados
        clientes_pos = conn.execute("SELECT * FROM clientes_pos WHERE activo = 1").fetchall()
        
        sync_data = {
            'productos': [dict(p) for p in productos],
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }
        
        # Enviar datos a cada cliente POS
        for cliente in clientes_pos:
            try:
                response = requests.post(
                    f"{cliente['url']}/api/sync",
                    json=sync_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                if response.status_code == 200:
                    # Actualizar estado de sincronización
                    conn.execute("""
                        UPDATE clientes_pos 
                        SET ultima_sincronizacion = CURRENT_TIMESTAMP, 
                            estado = 'conectado'
                        WHERE id_cliente = ?
                    """, (cliente['id_cliente'],))
                else:
                    conn.execute("""
                        UPDATE clientes_pos 
                        SET estado = 'error',
                            ultimo_error = ?
                        WHERE id_cliente = ?
                    """, (f"HTTP {response.status_code}", cliente['id_cliente']))
                    
            except Exception as e:
                conn.execute("""
                    UPDATE clientes_pos 
                    SET estado = 'desconectado',
                        ultimo_error = ?
                    WHERE id_cliente = ?
                """, (str(e), cliente['id_cliente']))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error en sincronización: {e}")
        return False

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
# DASHBOARD
# -------------------
@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    
    # Estadísticas generales
    total_productos = conn.execute("SELECT COUNT(*) FROM productos WHERE activo = 1 AND eliminado = 0").fetchone()[0]
    productos_bajo_stock = conn.execute("SELECT COUNT(*) FROM productos WHERE stock <= 10 AND activo = 1 AND eliminado = 0").fetchone()[0]
    total_ventas_hoy = conn.execute("""
        SELECT COUNT(*) FROM ventas 
        WHERE DATE(fecha_venta) = DATE('now')
    """).fetchone()[0]
    
    # Ventas de hoy
    ventas_hoy = conn.execute("""
        SELECT SUM(total) FROM ventas 
        WHERE DATE(fecha_venta) = DATE('now')
    """).fetchone()[0] or 0
    
    # Productos más vendidos
    productos_mas_vendidos = conn.execute("""
        SELECT p.nombre, SUM(dv.cantidad) as total_vendido
        FROM productos p
        JOIN detalles_venta dv ON p.id_producto = dv.producto_id
        JOIN ventas v ON dv.venta_id = v.id_venta
        WHERE DATE(v.fecha_venta) >= DATE('now', '-7 days')
        GROUP BY p.id_producto
        ORDER BY total_vendido DESC
        LIMIT 5
    """).fetchall()
    
    # Estado de clientes POS
    clientes_pos = conn.execute("""
        SELECT nombre, url, estado, ultima_sincronizacion
        FROM clientes_pos 
        WHERE activo = 1
        ORDER BY ultima_sincronizacion DESC
    """).fetchall()
    
    conn.close()
    
    return render_template("dashboard.html",
                         total_productos=total_productos,
                         productos_bajo_stock=productos_bajo_stock,
                         total_ventas_hoy=total_ventas_hoy,
                         ventas_hoy=ventas_hoy,
                         productos_mas_vendidos=productos_mas_vendidos,
                         clientes_pos=clientes_pos)

# -------------------
# LISTAR PRODUCTOS
# -------------------
@app.route("/admin")
@login_required
def admin():
    conn = get_db_connection()
    
    # Obtener filtros de la URL
    filtro_categoria = request.args.get('filtro_categoria', '')
    filtro_subcategoria = request.args.get('filtro_subcategoria', '')
    filtro_marca = request.args.get('filtro_marca', '')
    filtro_version = request.args.get('filtro_version', '')
    filtro_pesable = request.args.get('filtro_pesable', '')
    
    # Construir la consulta base
    query = """
        SELECT 
            p.id_producto,
            p.codigo,
            p.nombre,
            c.nombre AS categoria,
            s.nombre AS subcategoria,
            m.nombre AS marca_nombre,
            v.nombre AS version_nombre,
            p.precio_compra,
            p.precio_venta,
            p.stock,
            p.es_pesable,
            p.unidad_medida,
            p.ultima_sincronizacion
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id_subcategoria
        LEFT JOIN marcas m ON p.marca_id = m.id_marca
        LEFT JOIN versiones v ON p.version_id = v.id_version
        WHERE p.activo = 1 AND p.eliminado = 0
    """
    
    params = []
    
    # Agregar filtros si están presentes
    if filtro_categoria:
        query += " AND p.categoria_id = ?"
        params.append(filtro_categoria)
    
    if filtro_subcategoria:
        query += " AND p.subcategoria_id = ?"
        params.append(filtro_subcategoria)
    
    if filtro_marca:
        query += " AND p.marca_id = ?"
        params.append(filtro_marca)
    
    if filtro_version:
        query += " AND p.version_id = ?"
        params.append(filtro_version)
    
    if filtro_pesable:
        if filtro_pesable == 'si':
            query += " AND p.es_pesable = 1"
        elif filtro_pesable == 'no':
            query += " AND p.es_pesable = 0"
    
    query += " ORDER BY c.nombre, s.nombre, m.nombre, v.nombre, p.nombre"
    
    productos = conn.execute(query, params).fetchall()
    
    # Obtener datos para los filtros
    categorias = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    subcategorias = conn.execute("SELECT * FROM subcategorias ORDER BY nombre").fetchall()
    marcas = conn.execute("SELECT * FROM marcas ORDER BY nombre").fetchall()
    versiones = conn.execute("SELECT * FROM versiones ORDER BY nombre").fetchall()
    
    # Convertir a diccionarios para JSON
    subcategorias_data = [dict(row) for row in subcategorias]
    marcas_data = [dict(row) for row in marcas]
    versiones_data = [dict(row) for row in versiones]
    
    # Datos de filtros actuales
    filtros = {
        'categoria_id': filtro_categoria,
        'subcategoria_id': filtro_subcategoria,
        'marca_id': filtro_marca,
        'version_id': filtro_version,
        'pesable': filtro_pesable
    }
    
    conn.close()
    return render_template("admin.html", 
                         productos=productos,
                         categorias=categorias,
                         subcategorias=subcategorias,
                         marcas=marcas,
                         versiones=versiones,
                         subcategorias_data=subcategorias_data,
                         marcas_data=marcas_data,
                         versiones_data=versiones_data,
                         filtros=filtros)

# -------------------
# NUEVO PRODUCTO
# -------------------
@app.route("/nuevo_producto", methods=["GET", "POST"])
@login_required
def nuevo_producto():
    if request.method == "POST":
        try:
            conn = get_db_connection()
            
            # Obtener datos del formulario
            codigo = request.form.get("codigo")
            nombre = request.form.get("nombre")
            categoria_id = request.form.get("categoria_id")
            subcategoria_id = request.form.get("subcategoria_id") or None
            marca_id = request.form.get("marca_id") or None
            version_id = request.form.get("version_id") or None
            precio_compra = float(request.form.get("precio_compra", 0))
            precio_venta = float(request.form.get("precio_venta", 0))
            stock = int(request.form.get("stock", 0))
            es_pesable = request.form.get("es_pesable") == "on"
            unidad_medida = request.form.get("unidad_medida", "unidad")
            
            # Validar que el código sea único
            existing = conn.execute("SELECT id_producto FROM productos WHERE codigo = ?", (codigo,)).fetchone()
            if existing:
                flash("El código ya existe", "error")
                return redirect(url_for("nuevo_producto"))
            
            # Insertar producto
            conn.execute("""
                INSERT INTO productos (
                    codigo, nombre, categoria_id, subcategoria_id, marca_id, version_id,
                    precio_compra, precio_venta, stock, es_pesable, unidad_medida,
                    activo, fecha_creacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (codigo, nombre, categoria_id, subcategoria_id, marca_id, version_id,
                  precio_compra, precio_venta, stock, es_pesable, unidad_medida))
            
            conn.commit()
            conn.close()
            
            flash("Producto creado exitosamente", "success")
            return redirect(url_for("admin"))
            
        except Exception as e:
            flash(f"Error al crear producto: {e}", "error")
            return redirect(url_for("nuevo_producto"))
    
    conn = get_db_connection()
    categorias = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    subcategorias = conn.execute("SELECT * FROM subcategorias ORDER BY nombre").fetchall()
    marcas = conn.execute("SELECT * FROM marcas ORDER BY nombre").fetchall()
    versiones = conn.execute("SELECT * FROM versiones ORDER BY nombre").fetchall()
    conn.close()
    
    return render_template("nuevo_producto.html",
                         categorias=categorias,
                         subcategorias=subcategorias,
                         marcas=marcas,
                         versiones=versiones)

# -------------------
# API ROUTES PARA SINCRONIZACIÓN
# -------------------

@app.route("/api/sync", methods=["POST"])
def api_sync():
    """Endpoint para sincronización con clientes POS"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Datos inválidos"}), 400
        
        # Procesar datos de sincronización
        productos_recibidos = data.get('productos', [])
        ventas_recibidas = data.get('ventas', [])
        
        conn = get_db_connection()
        
        # Actualizar productos
        for producto_data in productos_recibidos:
            conn.execute("""
                UPDATE productos 
                SET stock = ?, ultima_sincronizacion = CURRENT_TIMESTAMP
                WHERE codigo = ?
            """, (producto_data.get('stock', 0), producto_data.get('codigo')))
        
        # Registrar ventas del cliente POS
        for venta_data in ventas_recibidas:
            conn.execute("""
                INSERT INTO ventas_pos (
                    cliente_id, total, fecha_venta, productos_json
                ) VALUES (?, ?, ?, ?)
            """, (
                venta_data.get('cliente_id'),
                venta_data.get('total', 0),
                venta_data.get('fecha_venta'),
                json.dumps(venta_data.get('productos', []))
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Sincronización completada"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/productos", methods=["GET"])
def api_productos():
    """Endpoint para obtener productos activos"""
    try:
        conn = get_db_connection()
        productos = conn.execute("""
            SELECT 
                p.id_producto, p.codigo, p.nombre, p.categoria_id, p.subcategoria_id,
                p.marca_id, p.version_id, p.precio_compra, p.precio_venta, p.stock,
                p.es_pesable, p.venta_por_peso, p.unidad_medida, p.activo, p.eliminado, p.fecha_creacion
            FROM productos p
            WHERE p.activo = 1 AND p.eliminado = 0
            ORDER BY p.nombre
        """).fetchall()
        
        conn.close()
        
        # Convertir a diccionario y mapear precio_venta a precio para compatibilidad con POS
        productos_dict = []
        for p in productos:
            producto_dict = dict(p)
            # Mapear precio_venta a precio para compatibilidad con POS
            producto_dict['precio'] = producto_dict.get('precio_venta', 0)
            productos_dict.append(producto_dict)
        
        return jsonify(productos_dict)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/categorias", methods=["GET", "POST"])
def api_categorias():
    """Endpoint para obtener y crear categorías"""
    try:
        conn = get_db_connection()
        
        if request.method == "GET":
            categorias = conn.execute("""
                SELECT id_categoria, nombre
                FROM categorias
                ORDER BY nombre
            """).fetchall()
            
            conn.close()
            return jsonify([dict(c) for c in categorias])
        
        elif request.method == "POST":
            data = request.get_json()
            nombre = data.get("nombre")
            
            if not nombre:
                return jsonify({"success": False, "message": "El nombre es requerido"}), 400
            
            # Insertar nueva categoría
            cursor = conn.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
            conn.commit()
            
            # Obtener la categoría creada
            nueva_categoria = conn.execute("""
                SELECT id_categoria, nombre
                FROM categorias
                WHERE id_categoria = ?
            """, (cursor.lastrowid,)).fetchone()
            
            conn.close()
            
            return jsonify({
                "success": True,
                "message": "Categoría creada correctamente",
                "categoria": dict(nueva_categoria)
            })
        
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": f"Error al crear la categoría: {str(e)}"}), 500

@app.route("/api/subcategorias", methods=["GET", "POST"])
def api_subcategorias():
    """Endpoint para obtener y crear subcategorías"""
    try:
        conn = get_db_connection()
        
        if request.method == "GET":
            subcategorias = conn.execute("""
                SELECT id_subcategoria, nombre, categoria_id
                FROM subcategorias
                ORDER BY nombre
            """).fetchall()
            
            conn.close()
            return jsonify([dict(s) for s in subcategorias])
        
        elif request.method == "POST":
            data = request.get_json()
            nombre = data.get("nombre")
            categoria_id = data.get("categoria_id")
            
            if not nombre:
                return jsonify({"success": False, "message": "El nombre es requerido"}), 400
            
            # Insertar nueva subcategoría
            cursor = conn.execute("INSERT INTO subcategorias (nombre, categoria_id) VALUES (?, ?)", 
                                (nombre, categoria_id))
            conn.commit()
            
            # Obtener la subcategoría creada
            nueva_subcategoria = conn.execute("""
                SELECT id_subcategoria, nombre, categoria_id
                FROM subcategorias
                WHERE id_subcategoria = ?
            """, (cursor.lastrowid,)).fetchone()
            
            conn.close()
            
            return jsonify({
                "success": True,
                "message": "Subcategoría creada correctamente",
                "subcategoria": dict(nueva_subcategoria)
            })
        
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": f"Error al crear la subcategoría: {str(e)}"}), 500

@app.route("/api/subcategorias/<int:id_subcategoria>", methods=["PUT"])
def api_editar_subcategoria(id_subcategoria):
    """Endpoint para editar subcategorías"""
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        categoria_id = data.get("categoria_id")
        
        if not nombre:
            return jsonify({"success": False, "message": "El nombre es requerido"}), 400
        
        conn = get_db_connection()
        
        # Actualizar la subcategoría
        conn.execute("""
            UPDATE subcategorias 
            SET nombre = ?, categoria_id = ?
            WHERE id_subcategoria = ?
        """, (nombre, categoria_id, id_subcategoria))
        conn.commit()
        
        # Obtener la subcategoría actualizada
        subcategoria_actualizada = conn.execute("""
            SELECT id_subcategoria, nombre, categoria_id
            FROM subcategorias
            WHERE id_subcategoria = ?
        """, (id_subcategoria,)).fetchone()
        
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Subcategoría actualizada correctamente",
            "subcategoria": dict(subcategoria_actualizada)
        })
        
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": f"Error al actualizar la subcategoría: {str(e)}"}), 500

@app.route("/api/marcas", methods=["GET", "POST"])
def api_marcas():
    """Endpoint para obtener y crear marcas"""
    try:
        conn = get_db_connection()
        
        if request.method == "GET":
            marcas = conn.execute("""
                SELECT id_marca, nombre, subcategoria_id
                FROM marcas
                ORDER BY nombre
            """).fetchall()
            
            conn.close()
            return jsonify([dict(m) for m in marcas])
        
        elif request.method == "POST":
            data = request.get_json()
            nombre = data.get("nombre")
            subcategoria_id = data.get("subcategoria_id")
            
            if not nombre:
                return jsonify({"success": False, "message": "El nombre es requerido"}), 400
            
            # Insertar nueva marca
            cursor = conn.execute("INSERT INTO marcas (nombre, subcategoria_id) VALUES (?, ?)", 
                                (nombre, subcategoria_id))
            conn.commit()
            
            # Obtener la marca creada
            nueva_marca = conn.execute("""
                SELECT id_marca, nombre, subcategoria_id
                FROM marcas
                WHERE id_marca = ?
            """, (cursor.lastrowid,)).fetchone()
            
            conn.close()
            
            return jsonify({
                "success": True,
                "message": "Marca creada correctamente",
                "marca": dict(nueva_marca)
            })
        
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": f"Error al crear la marca: {str(e)}"}), 500

@app.route("/api/marcas/<int:id_marca>", methods=["PUT"])
def api_editar_marca(id_marca):
    """Endpoint para editar marcas"""
    try:
        data = request.get_json()
        nombre = data.get("nombre")
        subcategoria_id = data.get("subcategoria_id")
        
        if not nombre:
            return jsonify({"success": False, "message": "El nombre es requerido"}), 400
        
        conn = get_db_connection()
        
        # Actualizar la marca
        conn.execute("""
            UPDATE marcas 
            SET nombre = ?, subcategoria_id = ?
            WHERE id_marca = ?
        """, (nombre, subcategoria_id, id_marca))
        conn.commit()
        
        # Obtener la marca actualizada
        marca_actualizada = conn.execute("""
            SELECT id_marca, nombre, subcategoria_id
            FROM marcas
            WHERE id_marca = ?
        """, (id_marca,)).fetchone()
        
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Marca actualizada correctamente",
            "marca": dict(marca_actualizada)
        })
        
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": f"Error al actualizar la marca: {str(e)}"}), 500

@app.route("/api/versiones", methods=["GET", "POST"])
def api_versiones():
    """Endpoint para obtener y crear versiones"""
    try:
        conn = get_db_connection()
        
        if request.method == "GET":
            versiones = conn.execute("""
                SELECT id_version, nombre, marca_id
                FROM versiones
                ORDER BY nombre
            """).fetchall()
            
            conn.close()
            return jsonify([dict(v) for v in versiones])
        
        elif request.method == "POST":
            data = request.get_json()
            nombre = data.get("nombre")
            marca_id = data.get("marca_id")
            
            if not nombre:
                return jsonify({"success": False, "message": "El nombre es requerido"}), 400
            
            # Insertar nueva versión
            cursor = conn.execute("INSERT INTO versiones (nombre, marca_id) VALUES (?, ?)", 
                                (nombre, marca_id))
            conn.commit()
            
            # Obtener la versión creada
            nueva_version = conn.execute("""
                SELECT id_version, nombre, marca_id
                FROM versiones
                WHERE id_version = ?
            """, (cursor.lastrowid,)).fetchone()
            
            conn.close()
            
            return jsonify({
                "success": True,
                "message": "Versión creada correctamente",
                "version": dict(nueva_version)
            })
        
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": f"Error al crear la versión: {str(e)}"}), 500

@app.route("/api/clientes", methods=["GET"])
def api_clientes():
    """Endpoint para obtener clientes"""
    try:
        conn = get_db_connection()
        clientes = conn.execute("""
            SELECT id_cliente, nombre, telefono, email, direccion, activo
            FROM clientes
            WHERE activo = 1
            ORDER BY nombre
        """).fetchall()
        
        conn.close()
        
        return jsonify([dict(c) for c in clientes])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/health", methods=["GET"])
def api_health():
    """Endpoint de salud para verificar conexión"""
    try:
        conn = get_db_connection()
        # Verificar que la base de datos responde
        conn.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        })
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/api/ventas/batch", methods=["POST"])
def api_ventas_batch():
    """Endpoint para recibir ventas en lote desde el POS"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Datos de ventas requeridos"}), 400
        
        # Aceptar tanto formato {"ventas": [...]} como formato directo [...]
        if isinstance(data, list):
            ventas_data = data
        elif isinstance(data, dict) and 'ventas' in data:
            ventas_data = data['ventas']
        else:
            return jsonify({"success": False, "error": "Formato de datos inválido"}), 400
        
        conn = get_db_connection()
        ventas_recibidas = 0
        
        for venta_data in ventas_data:
            try:
                # Insertar venta principal
                cursor = conn.execute("""
                    INSERT INTO ventas (
                        fecha_venta, total, usuario_id, efectivo, transferencia, credito, prestamo_personal,
                        cliente_id, sincronizado, fecha_sincronizacion
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                """, (
                    venta_data['fecha_venta'],
                    venta_data['total'],
                    venta_data['id_usuario'],
                    venta_data.get('efectivo', 0),
                    venta_data.get('transferencia', 0),
                    venta_data.get('credito', 0),
                    venta_data.get('prestamo_personal', 0),
                    venta_data.get('cliente_id')
                ))
                
                # Obtener el ID de la venta insertada
                venta_id = cursor.lastrowid
                
                # Insertar detalles de la venta
                for item in venta_data.get('items', []):
                    conn.execute("""
                        INSERT INTO detalles_venta (
                            venta_id, producto_id, cantidad, precio_unitario, subtotal
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        venta_id,
                        item['id_producto'],
                        item['cantidad'],
                        item['precio_unitario'],
                        item['cantidad'] * item['precio_unitario']
                    ))
                
                ventas_recibidas += 1
                
            except Exception as e:
                print(f"Error procesando venta {venta_data.get('id_venta')}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Procesadas {ventas_recibidas} ventas",
            "ventas_recibidas": ventas_recibidas
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -------------------
# ENDPOINT TEMPORAL PARA INICIALIZACIÓN
# -------------------
@app.route("/api/init_db", methods=["POST"])
def init_db():
    """Endpoint temporal para inicializar la base de datos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Crear la tabla detalles_venta
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalles_venta (
            id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            cantidad REAL NOT NULL,
            precio_unitario REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (venta_id) REFERENCES ventas (id_venta),
            FOREIGN KEY (producto_id) REFERENCES productos (id_producto)
        )
        """)
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Base de datos inicializada correctamente"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -------------------
# SINCRONIZACIÓN MANUAL
# -------------------
@app.route("/sync_manual")
@admin_required
def sync_manual():
    """Sincronización manual con clientes POS"""
    success = sync_with_pos_clients()
    
    if success:
        flash("Sincronización completada exitosamente", "success")
    else:
        flash("Error en la sincronización", "error")
    
    return redirect(url_for("dashboard"))

# -------------------
# GESTIÓN DE CLIENTES POS
# -------------------
@app.route("/clientes_pos")
@admin_required
def clientes_pos():
    conn = get_db_connection()
    clientes = conn.execute("""
        SELECT * FROM clientes_pos 
        ORDER BY nombre
    """).fetchall()
    conn.close()
    
    return render_template("clientes_pos.html", clientes=clientes)

@app.route("/nuevo_cliente_pos", methods=["GET", "POST"])
@admin_required
def nuevo_cliente_pos():
    if request.method == "POST":
        try:
            conn = get_db_connection()
            
            nombre = request.form.get("nombre")
            url = request.form.get("url")
            descripcion = request.form.get("descripcion", "")
            
            conn.execute("""
                INSERT INTO clientes_pos (nombre, url, descripcion, activo, fecha_registro)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (nombre, url, descripcion))
            
            conn.commit()
            conn.close()
            
            flash("Cliente POS registrado exitosamente", "success")
            return redirect(url_for("clientes_pos"))
            
        except Exception as e:
            flash(f"Error al registrar cliente: {e}", "error")
    
    return render_template("nuevo_cliente_pos.html")

# -------------------
# CATEGORÍAS
# -------------------
@app.route("/categorias")
@login_required
def listar_categorias():
    conn = get_db_connection()
    categorias = conn.execute("""
        SELECT c.*
        FROM categorias c
        ORDER BY c.nombre
    """).fetchall()
    
    conn.close()
    return render_template("categorias.html", categorias=categorias)

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
@login_required
def listar_subcategorias():
    conn = get_db_connection()
    subcategorias = conn.execute("""
        SELECT s.*, c.nombre as categoria_nombre
        FROM subcategorias s
        LEFT JOIN categorias c ON s.categoria_id = c.id_categoria
        ORDER BY c.nombre, s.nombre
    """).fetchall()
    
    categorias = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    conn.close()
    return render_template("subcategorias.html", subcategorias=subcategorias, categorias=categorias)

@app.route("/nueva_subcategoria", methods=["GET", "POST"])
@login_required
def nueva_subcategoria():
    conn = get_db_connection()
    categorias = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    
    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria_id = request.form.get("categoria_id") or None
        
        conn.execute("INSERT INTO subcategorias (nombre, categoria_id) VALUES (?, ?)", (nombre, categoria_id))
        conn.commit()
        conn.close()
        flash("Subcategoría creada correctamente", "success")
        return redirect(url_for("listar_subcategorias"))
    
    conn.close()
    return render_template("nueva_subcategoria.html", categorias=categorias)

# -------------------
# MARCAS
# -------------------
@app.route("/marcas")
@login_required
def listar_marcas():
    conn = get_db_connection()
    marcas = conn.execute("""
        SELECT m.*, s.nombre as subcategoria_nombre, c.nombre as categoria_nombre
        FROM marcas m
        LEFT JOIN subcategorias s ON m.subcategoria_id = s.id_subcategoria
        LEFT JOIN categorias c ON s.categoria_id = c.id_categoria
        ORDER BY c.nombre, s.nombre, m.nombre
    """).fetchall()
    
    subcategorias = conn.execute("SELECT * FROM subcategorias ORDER BY nombre").fetchall()
    conn.close()
    return render_template("marcas.html", marcas=marcas, subcategorias=subcategorias)

@app.route("/nueva_marca", methods=["GET", "POST"])
@login_required
def nueva_marca():
    conn = get_db_connection()
    categorias = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    subcategorias = conn.execute("SELECT * FROM subcategorias ORDER BY nombre").fetchall()
    
    if request.method == "POST":
        nombre = request.form["nombre"]
        subcategoria_id = request.form.get("subcategoria_id") or None
        
        conn.execute("INSERT INTO marcas (nombre, subcategoria_id) VALUES (?, ?)", (nombre, subcategoria_id))
        conn.commit()
        conn.close()
        flash("Marca creada correctamente", "success")
        return redirect(url_for("listar_marcas"))
    
    conn.close()
    return render_template("nueva_marca.html", categorias=categorias, subcategorias=subcategorias)

# -------------------
# VERSIONES
# -------------------
@app.route("/versiones")
@login_required
def listar_versiones():
    conn = get_db_connection()
    versiones = conn.execute("""
        SELECT v.*, m.nombre as marca_nombre, s.nombre as subcategoria_nombre, c.nombre as categoria_nombre
        FROM versiones v
        LEFT JOIN marcas m ON v.marca_id = m.id_marca
        LEFT JOIN subcategorias s ON m.subcategoria_id = s.id_subcategoria
        LEFT JOIN categorias c ON s.categoria_id = c.id_categoria
        ORDER BY c.nombre, s.nombre, m.nombre, v.nombre
    """).fetchall()
    
    conn.close()
    return render_template("versiones.html", versiones=versiones)

@app.route("/nueva_version", methods=["GET", "POST"])
@login_required
def nueva_version():
    conn = get_db_connection()
    categorias = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    subcategorias = conn.execute("SELECT * FROM subcategorias ORDER BY nombre").fetchall()
    marcas = conn.execute("SELECT * FROM marcas ORDER BY nombre").fetchall()
    
    if request.method == "POST":
        nombre = request.form["nombre"]
        marca_id = request.form.get("marca_id") or None
        
        conn.execute("INSERT INTO versiones (nombre, marca_id) VALUES (?, ?)", (nombre, marca_id))
        conn.commit()
        conn.close()
        flash("Versión creada correctamente", "success")
        return redirect(url_for("listar_versiones"))
    
    conn.close()
    return render_template("nueva_version.html", categorias=categorias, subcategorias=subcategorias, marcas=marcas)



# -------------------
# EDITAR PRODUCTO
# -------------------
@app.route("/editar_producto/<int:id_producto>", methods=["GET", "POST"])
def editar_producto(id_producto):
    conn = get_db_connection()
    producto = conn.execute("SELECT * FROM productos WHERE id_producto = ?", (id_producto,)).fetchone()
    categorias = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    subcategorias = conn.execute("SELECT * FROM subcategorias ORDER BY nombre").fetchall()
    marcas = conn.execute("SELECT * FROM marcas ORDER BY nombre").fetchall()
    versiones = conn.execute("SELECT * FROM versiones ORDER BY nombre").fetchall()

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
        es_pesable = 1 if request.form.get("es_pesable") else 0
        unidad_medida = request.form.get("unidad_medida", "unidad")
        activo = 1 if request.form.get("activo") else 0

        conn.execute("""
            UPDATE productos
            SET nombre = ?, categoria_id = ?, subcategoria_id = ?, marca_id = ?, version_id = ?,
                precio_compra = ?, precio_venta = ?, es_pesable = ?, unidad_medida = ?, activo = ?
            WHERE id_producto = ?
        """, (nombre, categoria_id, subcategoria_id, marca_id, version_id, 
              precio_compra, precio_venta, es_pesable, unidad_medida, activo, id_producto))

        conn.commit()
        conn.close()
        flash("Producto actualizado correctamente", "success")
        return redirect(url_for("admin"))

    conn.close()
    return render_template("editar_producto.html", 
                         producto=producto, 
                         categorias=categorias,
                         subcategorias=subcategorias,
                         marcas=marcas,
                         versiones=versiones)

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
        categoria_ids = request.form.getlist("categoria_id[]")
        subcategoria_ids = request.form.getlist("subcategoria_id[]")
        marca_ids = request.form.getlist("marca_id[]")
        version_ids = request.form.getlist("version_id[]")
        cantidades = request.form.getlist("cantidad[]")
        precios_compra = request.form.getlist("precio_compra[]")
        precios_venta = request.form.getlist("precio_venta[]")
        codigos_existentes = request.form.getlist("codigo_existente[]")

        for i, (categoria_id, subcategoria_id, marca_id, version_id, cantidad, pcompra, pventa, codigo_existente) in enumerate(
            zip(categoria_ids, subcategoria_ids, marca_ids, version_ids, cantidades, precios_compra, precios_venta, codigos_existentes)
        ):
            if cantidad and pcompra and pventa:
                if codigo_existente:
                    # Producto existente - usar su ID
                    id_producto = int(codigo_existente)
                else:
                    # Producto nuevo - crearlo
                    codigo = generar_codigo()
                    while conn.execute("SELECT 1 FROM productos WHERE codigo = ?", (codigo,)).fetchone():
                        codigo = generar_codigo()
                    
                    # Obtener valores de la estructura completa
                    es_pesable = request.form.getlist("es_pesable[]")
                    
                    es_pesable_val = 1 if i < len(es_pesable) and es_pesable[i] else 0
                    unidad_medida_val = "kg" if es_pesable_val else "unidad"
                    
                    # Generar nombre automático a partir de categoría/subcategoría/marca/versión
                    nombre_parts = []
                    if marca_id:
                        marca_nombre = conn.execute("SELECT nombre FROM marcas WHERE id_marca = ?", (marca_id,)).fetchone()
                        if marca_nombre: nombre_parts.append(marca_nombre[0])
                    if subcategoria_id:
                        sub_nombre = conn.execute("SELECT nombre FROM subcategorias WHERE id_subcategoria = ?", (subcategoria_id,)).fetchone()
                        if sub_nombre: nombre_parts.append(sub_nombre[0])
                    if version_id:
                        ver_nombre = conn.execute("SELECT nombre FROM versiones WHERE id_version = ?", (version_id,)).fetchone()
                        if ver_nombre: nombre_parts.append(ver_nombre[0])
                    nombre_auto = " ".join(nombre_parts) or "Producto"

                    cursor.execute("""
                        INSERT INTO productos (codigo, nombre, categoria_id, subcategoria_id, marca_id, version_id, 
                                             precio_compra, precio_venta, es_pesable, unidad_medida)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (codigo, nombre_auto, categoria_id or None, subcategoria_id or None, marca_id or None, version_id or None, 
                          float(pcompra), float(pventa), es_pesable_val, unidad_medida_val))
                    id_producto = cursor.lastrowid

                # Agregar detalle del lote
                cursor.execute("""
                    INSERT INTO lotes_detalles (id_lote, id_producto, cantidad, precio_compra, precio_venta)
                    VALUES (?, ?, ?, ?, ?)
                """, (id_lote, id_producto, float(cantidad), float(pcompra), float(pventa)))
                
                # Actualizar el stock del producto
                cursor.execute("""
                    UPDATE productos 
                    SET stock = stock + ? 
                    WHERE id_producto = ?
                """, (float(cantidad), id_producto))

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
               c.nombre as categoria, s.nombre as subcategoria, m.nombre as marca_nombre, v.nombre as version
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
               c.nombre AS categoria
        FROM lotes_detalles ld
        JOIN productos p ON ld.id_producto = p.id_producto
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria

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
                """, (id_lote, int(prod_id), float(cantidad), float(pcompra or 0), float(pventa or 0)))
        
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
        """, (float(cantidad), id_producto))
    
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
               COALESCE(SUM(v.total), 0) as total_comprado
        FROM clientes c
        LEFT JOIN ventas v ON c.id_cliente = v.cliente_id
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
            COALESCE(SUM(v.total), 0) as total_deuda,
            MAX(v.fecha_venta) as ultima_compra
        FROM clientes c
        INNER JOIN ventas v ON c.id_cliente = v.cliente_id
        WHERE v.prestamo_personal > 0
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
                v.total,
                v.observaciones
            FROM ventas v
            WHERE v.cliente_id = ? AND v.prestamo_personal > 0
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
def ventas():
    try:
        conn = get_db_connection()
        ventas = conn.execute("""
            SELECT v.*, c.nombre AS cliente_nombre,
                   (SELECT SUM(vd.cantidad) FROM detalles_venta vd WHERE vd.venta_id = v.id_venta) AS items
            FROM ventas v
            LEFT JOIN clientes c ON v.cliente_id = c.id_cliente
            ORDER BY v.fecha_venta DESC
        """).fetchall()
        conn.close()
        return render_template("ventas.html", ventas=ventas)
    except Exception as e:
        print(f"Error en ventas: {e}")
        return render_template("ventas.html", ventas=[], error=str(e))

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
                cantidad = float(cantidad)  # Permitir decimales para productos pesables
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
                    INSERT INTO detalles_venta (venta_id, producto_id, cantidad, precio_unitario, subtotal)
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
            SET total = ? 
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
               c.nombre AS categoria, p.es_pesable, p.unidad_medida
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria
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
@login_required
def ver_venta(id_venta):
    try:
        conn = get_db_connection()
        
        # Obtener información de la venta
        venta = conn.execute("""
            SELECT v.*, c.nombre AS cliente_nombre, c.apellido AS cliente_apellido
            FROM ventas v
            LEFT JOIN clientes c ON v.cliente_id = c.id_cliente
            WHERE v.id_venta = ?
        """, (id_venta,)).fetchone()
        
        if not venta:
            conn.close()
            flash("Venta no encontrada", "danger")
            return redirect(url_for("ventas"))
        
        # Obtener detalles de la venta
        detalles = conn.execute("""
            SELECT vd.*, p.codigo, p.nombre AS producto_nombre
            FROM detalles_venta vd
            JOIN productos p ON vd.producto_id = p.id_producto
            WHERE vd.venta_id = ?
            ORDER BY p.nombre
        """, (id_venta,)).fetchall()
        
        conn.close()
        return render_template("ver_venta.html", venta=venta, detalles=detalles)
        except Exception as e:
            print(f"Error en ver_venta: {e}")
            flash(f"Error al cargar la venta: {e}", "danger")
            return redirect(url_for("ventas"))

@app.route("/prestamos_personales")
@login_required
def prestamos_personales():
    """Muestra los préstamos personales"""
    try:
        conn = get_db_connection()
        
        # Obtener préstamos personales
        prestamos = conn.execute("""
            SELECT 
                v.id_venta,
                v.fecha_venta,
                v.prestamo_personal,
                c.nombre AS cliente_nombre,
                c.apellido AS cliente_apellido,
                c.telefono,
                c.email
            FROM ventas v
            LEFT JOIN clientes c ON v.cliente_id = c.id_cliente
            WHERE v.prestamo_personal > 0
            ORDER BY v.fecha_venta DESC
        """).fetchall()
        
        conn.close()
        return render_template("prestamos_personales.html", prestamos=prestamos)
    except Exception as e:
        print(f"Error en prestamos_personales: {e}")
        return render_template("prestamos_personales.html", prestamos=[], error=str(e))

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
        SELECT producto_id, cantidad 
        FROM detalles_venta 
        WHERE venta_id = ?
    """, (id_venta,)).fetchall()
    
    # Revertir el stock de cada producto
    for detalle in detalles:
        producto_id, cantidad = detalle
        conn.execute("""
            UPDATE productos 
            SET stock = stock + ? 
            WHERE id_producto = ?
        """, (float(cantidad), producto_id))
    
    # Eliminar detalles de la venta
    conn.execute("DELETE FROM detalles_venta WHERE venta_id = ?", (id_venta,))
    
    # Eliminar la venta
    conn.execute("DELETE FROM ventas WHERE id_venta = ?", (id_venta,))
    
    conn.commit()
    conn.close()
    flash("Venta eliminada correctamente", "success")
    return redirect(url_for("ventas"))

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
        'marca': p.marca_nombre,
        'version': p.version_nombre
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
               c.nombre AS categoria
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria

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
# API ROUTES (EXISTENTES)
# -------------------
@app.route("/api/proveedores", methods=["GET", "POST"])
def api_proveedores():
    if request.method == "GET":
        """Endpoint para obtener proveedores"""
        try:
            conn = get_db_connection()
            proveedores = conn.execute("""
                SELECT id_proveedor, nombre, telefono, email
                FROM proveedores
                ORDER BY nombre
            """).fetchall()
            conn.close()
            
            return jsonify([dict(proveedor) for proveedor in proveedores])
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "POST":
        """Endpoint para crear proveedores"""
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
        v.total,
        CASE 
            WHEN v.efectivo > 0 THEN 'Efectivo'
            WHEN v.transferencia > 0 THEN 'Transferencia'
            WHEN v.credito > 0 THEN 'Crédito'
            WHEN v.prestamo_personal > 0 THEN 'Préstamo Personal'
            ELSE 'Mixto'
        END as metodo_pago,
        '' as observaciones
    FROM ventas v
    LEFT JOIN clientes c ON v.cliente_id = c.id_cliente
    LEFT JOIN detalles_venta vd ON v.id_venta = vd.venta_id
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
        SELECT 
            CASE 
                WHEN efectivo > 0 THEN 'Efectivo'
                WHEN transferencia > 0 THEN 'Transferencia'
                WHEN credito > 0 THEN 'Crédito'
                WHEN prestamo_personal > 0 THEN 'Préstamo Personal'
                ELSE 'Mixto'
            END as metodo_pago,
            COUNT(*), 
            SUM(total)
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
        FROM detalles_venta vd
        JOIN productos p ON vd.producto_id = p.id_producto
        LEFT JOIN categorias cat ON p.categoria_id = cat.id_categoria
        JOIN ventas v ON vd.venta_id = v.id_venta
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
            (AVG(vd.precio_unitario) - AVG(COALESCE(ld.precio_compra, 0))) / NULLIF(AVG(vd.precio_unitario), 0) * 100 as margen_porcentual
        FROM detalles_venta vd
        JOIN productos p ON vd.producto_id = p.id_producto
        LEFT JOIN lotes_detalles ld ON p.id_producto = ld.id_producto
        JOIN ventas v ON vd.venta_id = v.id_venta
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
            COALESCE(ROUND(CAST(COALESCE(SUM(vd.cantidad), 0) AS FLOAT) / NULLIF(p.stock, 0) * 100, 2), 0) as rotacion_porcentual
        FROM detalles_venta vd
        JOIN productos p ON vd.producto_id = p.id_producto
        LEFT JOIN categorias cat ON p.categoria_id = cat.id_categoria
        JOIN ventas v ON vd.venta_id = v.id_venta
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
            COALESCE(ROUND(CAST(COALESCE(SUM(vd.cantidad), 0) AS FLOAT) / NULLIF(p.stock, 0) * 100, 2), 0) as rotacion_porcentual
        FROM productos p
        LEFT JOIN categorias cat ON p.categoria_id = cat.id_categoria
        LEFT JOIN detalles_venta vd ON p.id_producto = vd.producto_id
        LEFT JOIN ventas v ON vd.venta_id = v.id_venta AND v.eliminado = 0
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
            COALESCE(ROUND(CAST(SUM(COALESCE(vd.cantidad, 0)) AS FLOAT) / NULLIF(AVG(p.stock), 0) * 100, 2), 0) as rotacion_categoria
        FROM categorias cat
        LEFT JOIN productos p ON cat.id_categoria = p.categoria_id AND p.eliminado = 0
        LEFT JOIN detalles_venta vd ON p.id_producto = vd.producto_id
        LEFT JOIN ventas v ON vd.venta_id = v.id_venta AND v.eliminado = 0
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
        LEFT JOIN detalles_venta vd ON p.id_producto = vd.producto_id
        LEFT JOIN ventas v ON vd.venta_id = v.id_venta 
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
            ROUND(CAST(COALESCE(SUM(vd.cantidad), 0) AS FLOAT) / NULLIF(COUNT(DISTINCT p.id_producto), 0), 1) as promedio_por_producto,
            ROUND(CAST(COALESCE(SUM(vd.cantidad), 0) AS FLOAT) / 30, 1) as promedio_diario_categoria
        FROM categorias cat
        LEFT JOIN productos p ON cat.id_categoria = p.categoria_id AND p.eliminado = 0
        LEFT JOIN detalles_venta vd ON p.id_producto = vd.producto_id
        LEFT JOIN ventas v ON vd.venta_id = v.id_venta 
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
            (AVG(vd.precio_unitario) - AVG(COALESCE(ld.precio_compra, 0))) / NULLIF(AVG(vd.precio_unitario), 0) * 100 as margen_porcentual,
            SUM(vd.cantidad) as total_vendido
        FROM productos p
        LEFT JOIN categorias cat ON p.categoria_id = cat.id_categoria
        LEFT JOIN detalles_venta vd ON p.id_producto = vd.producto_id
        LEFT JOIN lotes_detalles ld ON p.id_producto = ld.id_producto
        LEFT JOIN ventas v ON vd.venta_id = v.id_venta AND v.eliminado = 0
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
            SUM(v.total) as ingresos_mes,
            COUNT(DISTINCT vd.producto_id) as productos_vendidos
        FROM ventas v
        LEFT JOIN detalles_venta vd ON v.id_venta = vd.venta_id
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





# Registrar blueprint de la API
from api_routes import api
app.register_blueprint(api)

# -------------------
# API ROUTES ADICIONALES
# -------------------

@app.route("/api/test_connection", methods=["POST"])
@admin_required
def api_test_connection():
    """Probar conexión con un cliente POS"""
    try:
        data = request.get_json()
        cliente_id = data.get('cliente_id')
        url = data.get('url')
        
        if not cliente_id or not url:
            return jsonify({"success": False, "error": "Datos incompletos"}), 400
        
        # Probar conexión HTTP
        try:
            response = requests.get(f"{url}/api/health", timeout=5)
            if response.status_code == 200:
                # Actualizar estado en base de datos
                conn = get_db_connection()
                conn.execute("""
                    UPDATE clientes_pos 
                    SET estado = 'conectado', ultima_sincronizacion = CURRENT_TIMESTAMP
                    WHERE id_cliente = ?
                """, (cliente_id,))
                conn.commit()
                conn.close()
                
                return jsonify({"success": True, "message": "Conexión exitosa"})
            else:
                return jsonify({"success": False, "error": f"HTTP {response.status_code}"})
        except requests.exceptions.RequestException as e:
            # Actualizar estado de error
            conn = get_db_connection()
            conn.execute("""
                UPDATE clientes_pos 
                SET estado = 'error', ultimo_error = ?
                WHERE id_cliente = ?
            """, (str(e), cliente_id))
            conn.commit()
            conn.close()
            
            return jsonify({"success": False, "error": str(e)})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sync_client", methods=["POST"])
@admin_required
def api_sync_client():
    """Sincronizar con un cliente POS específico"""
    try:
        data = request.get_json()
        cliente_id = data.get('cliente_id')
        
        if not cliente_id:
            return jsonify({"success": False, "error": "ID de cliente requerido"}), 400
        
        conn = get_db_connection()
        cliente = conn.execute("SELECT * FROM clientes_pos WHERE id_cliente = ?", (cliente_id,)).fetchone()
        
        if not cliente:
            return jsonify({"success": False, "error": "Cliente no encontrado"}), 404
        
        # Obtener productos para sincronizar
        productos = conn.execute("""
            SELECT 
                id_producto, codigo, nombre, precio_venta, stock, 
                es_pesable, unidad_medida, activo
            FROM productos 
            WHERE activo = 1 AND eliminado = 0
        """).fetchall()
        
        sync_data = {
            'productos': [dict(p) for p in productos],
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }
        
        # Enviar datos al cliente
        try:
            response = requests.post(
                f"{cliente['url']}/api/sync",
                json=sync_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                # Actualizar estado
                conn.execute("""
                    UPDATE clientes_pos 
                    SET estado = 'conectado', ultima_sincronizacion = CURRENT_TIMESTAMP
                    WHERE id_cliente = ?
                """, (cliente_id,))
                conn.commit()
                conn.close()
                
                return jsonify({"success": True, "message": f"Sincronización exitosa con {cliente['nombre']}"})
            else:
                return jsonify({"success": False, "error": f"HTTP {response.status_code}"})
                
        except requests.exceptions.RequestException as e:
            # Actualizar estado de error
            conn.execute("""
                UPDATE clientes_pos 
                SET estado = 'error', ultimo_error = ?
                WHERE id_cliente = ?
            """, (str(e), cliente_id))
            conn.commit()
            conn.close()
            
            return jsonify({"success": False, "error": str(e)})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delete_client_pos", methods=["POST"])
@admin_required
def api_delete_client_pos():
    """Eliminar un cliente POS"""
    try:
        data = request.get_json()
        cliente_id = data.get('cliente_id')
        
        if not cliente_id:
            return jsonify({"success": False, "error": "ID de cliente requerido"}), 400
        
        conn = get_db_connection()
        
        # Verificar que existe
        cliente = conn.execute("SELECT * FROM clientes_pos WHERE id_cliente = ?", (cliente_id,)).fetchone()
        if not cliente:
            return jsonify({"success": False, "error": "Cliente no encontrado"}), 404
        
        # Eliminar (marcar como inactivo)
        conn.execute("UPDATE clientes_pos SET activo = 0 WHERE id_cliente = ?", (cliente_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Cliente eliminado exitosamente"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/pagos_parciales", methods=["GET", "POST"])
def api_pagos_parciales():
    """API para pagos parciales de créditos personales"""
    try:
        if request.method == "GET":
            # Obtener pagos parciales
            conn = get_db_connection()
            pagos = conn.execute("""
                SELECT pp.*, c.dni, c.nombre, c.apellido, v.id_venta, v.fecha_venta
                FROM pagos_parciales pp
                JOIN clientes c ON pp.cliente_id = c.id_cliente
                JOIN ventas v ON pp.venta_id = v.id_venta
                ORDER BY pp.fecha_pago DESC
            """).fetchall()
            conn.close()
            
            return jsonify({
                "success": True,
                "pagos": [dict(pago) for pago in pagos]
            })
            
        elif request.method == "POST":
            # Recibir nuevo pago parcial
            data = request.get_json()
            
            if not all(key in data for key in ['cliente_id', 'venta_id', 'monto_pago', 'usuario_id']):
                return jsonify({"success": False, "error": "Datos incompletos"}), 400
            
            conn = get_db_connection()
            
            # Insertar pago parcial
            cursor = conn.execute("""
                INSERT INTO pagos_parciales (cliente_id, venta_id, monto_pago, usuario_id, fecha_pago)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (data['cliente_id'], data['venta_id'], data['monto_pago'], data['usuario_id']))
            
            pago_id = cursor.lastrowid
            
            # Actualizar monto pendiente en la venta
            conn.execute("""
                UPDATE ventas 
                SET monto_pendiente = COALESCE(monto_pendiente, prestamo_personal) - ?
                WHERE id_venta = ?
            """, (data['monto_pago'], data['venta_id']))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                "success": True,
                "message": "Pago parcial registrado exitosamente",
                "pago_id": pago_id
            })
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/creditos_personales", methods=["GET"])
def api_creditos_personales():
    """API para obtener información de créditos personales"""
    try:
        conn = get_db_connection()
        
        # Obtener clientes con deudas pendientes
        clientes = conn.execute("""
            SELECT 
                c.id_cliente, c.dni, c.nombre, c.apellido,
                SUM(COALESCE(v.monto_pendiente, v.prestamo_personal)) as total_deuda,
                COUNT(v.id_venta) as cantidad_facturas
            FROM clientes c
            JOIN ventas v ON c.id_cliente = v.cliente_id
            WHERE v.prestamo_personal > 0 
            AND COALESCE(v.monto_pendiente, v.prestamo_personal) > 0
            GROUP BY c.id_cliente, c.dni, c.nombre, c.apellido
            ORDER BY total_deuda DESC
        """).fetchall()
        
        conn.close()
        
        return jsonify({
            "success": True,
            "clientes": [dict(cliente) for cliente in clientes]
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



# -------------------
# SINCRONIZACIÓN AUTOMÁTICA
# -------------------

def start_sync_scheduler():
    """Iniciar el programador de sincronización automática"""
    def sync_task():
        while True:
            try:
                sync_with_pos_clients()
                time.sleep(app.config['SYNC_INTERVAL'])
            except Exception as e:
                print(f"Error en sincronización automática: {e}")
                time.sleep(60)  # Esperar 1 minuto antes de reintentar
    
    # Iniciar en un hilo separado
    sync_thread = threading.Thread(target=sync_task, daemon=True)
    sync_thread.start()

# -------------------
# ELIMINAR CATEGORÍAS, SUBCATEGORÍAS Y MARCAS
# -------------------
@app.route("/eliminar_categoria/<int:id_categoria>")
@login_required
def eliminar_categoria(id_categoria):
    try:
        conn = get_db_connection()
        
        # Verificar si hay productos usando esta categoría
        productos = conn.execute("SELECT COUNT(*) FROM productos WHERE categoria_id = ? AND eliminado = 0", (id_categoria,)).fetchone()[0]
        if productos > 0:
            flash(f"No se puede eliminar la categoría porque tiene {productos} productos asociados", "error")
            conn.close()
            return redirect(url_for("listar_categorias"))
        
        # Verificar si hay subcategorías
        subcategorias = conn.execute("SELECT COUNT(*) FROM subcategorias WHERE categoria_id = ?", (id_categoria,)).fetchone()[0]
        if subcategorias > 0:
            flash(f"No se puede eliminar la categoría porque tiene {subcategorias} subcategorías asociadas", "error")
            conn.close()
            return redirect(url_for("listar_categorias"))
        
        # Eliminar la categoría
        conn.execute("DELETE FROM categorias WHERE id_categoria = ?", (id_categoria,))
        conn.commit()
        conn.close()
        
        flash("Categoría eliminada correctamente", "success")
        return redirect(url_for("listar_categorias"))
        
    except Exception as e:
        flash(f"Error al eliminar la categoría: {str(e)}", "error")
        return redirect(url_for("listar_categorias"))

@app.route("/eliminar_subcategoria/<int:id_subcategoria>")
@login_required
def eliminar_subcategoria(id_subcategoria):
    try:
        conn = get_db_connection()
        
        # Verificar si hay productos usando esta subcategoría
        productos = conn.execute("SELECT COUNT(*) FROM productos WHERE subcategoria_id = ? AND eliminado = 0", (id_subcategoria,)).fetchone()[0]
        if productos > 0:
            flash(f"No se puede eliminar la subcategoría porque tiene {productos} productos asociados", "error")
            conn.close()
            return redirect(url_for("listar_subcategorias"))
        
        # Verificar si hay marcas
        marcas = conn.execute("SELECT COUNT(*) FROM marcas WHERE subcategoria_id = ?", (id_subcategoria,)).fetchone()[0]
        if marcas > 0:
            flash(f"No se puede eliminar la subcategoría porque tiene {marcas} marcas asociadas", "error")
            conn.close()
            return redirect(url_for("listar_subcategorias"))
        
        # Eliminar la subcategoría
        conn.execute("DELETE FROM subcategorias WHERE id_subcategoria = ?", (id_subcategoria,))
        conn.commit()
        conn.close()
        
        flash("Subcategoría eliminada correctamente", "success")
        return redirect(url_for("listar_subcategorias"))
        
    except Exception as e:
        flash(f"Error al eliminar la subcategoría: {str(e)}", "error")
        return redirect(url_for("listar_subcategorias"))

@app.route("/eliminar_marca/<int:id_marca>")
@login_required
def eliminar_marca(id_marca):
    try:
        conn = get_db_connection()
        
        # Verificar si hay productos usando esta marca
        productos = conn.execute("SELECT COUNT(*) FROM productos WHERE marca_id = ? AND eliminado = 0", (id_marca,)).fetchone()[0]
        if productos > 0:
            flash(f"No se puede eliminar la marca porque tiene {productos} productos asociados", "error")
            conn.close()
            return redirect(url_for("listar_marcas"))
        
        # Verificar si hay versiones
        versiones = conn.execute("SELECT COUNT(*) FROM versiones WHERE marca_id = ?", (id_marca,)).fetchone()[0]
        if versiones > 0:
            flash(f"No se puede eliminar la marca porque tiene {versiones} versiones asociadas", "error")
            conn.close()
            return redirect(url_for("listar_marcas"))
        
        # Eliminar la marca
        conn.execute("DELETE FROM marcas WHERE id_marca = ?", (id_marca,))
        conn.commit()
        conn.close()
        
        flash("Marca eliminada correctamente", "success")
        return redirect(url_for("listar_marcas"))
        
    except Exception as e:
        flash(f"Error al eliminar la marca: {str(e)}", "error")
        return redirect(url_for("listar_marcas"))

@app.route("/eliminar_version/<int:id_version>")
@login_required
def eliminar_version(id_version):
    try:
        conn = get_db_connection()
        
        # Verificar si hay productos usando esta versión
        productos = conn.execute("SELECT COUNT(*) FROM productos WHERE version_id = ? AND eliminado = 0", (id_version,)).fetchone()[0]
        if productos > 0:
            flash(f"No se puede eliminar la versión porque tiene {productos} productos asociados", "error")
            conn.close()
            return redirect(url_for("listar_versiones"))
        
        # Eliminar la versión
        conn.execute("DELETE FROM versiones WHERE id_version = ?", (id_version,))
        conn.commit()
        conn.close()
        
        flash("Versión eliminada correctamente", "success")
        return redirect(url_for("listar_versiones"))
        
    except Exception as e:
        flash(f"Error al eliminar la versión: {str(e)}", "error")
        return redirect(url_for("listar_versiones"))

# Rutas API para el frontend
@app.route("/api/subcategorias/<int:categoria_id>")
def api_subcategorias_por_categoria(categoria_id):
    """Obtener subcategorías por categoría"""
    try:
        conn = get_db_connection()
        subcategorias = conn.execute("""
            SELECT id_subcategoria, nombre, categoria_id
            FROM subcategorias
            WHERE categoria_id = ?
            ORDER BY nombre
        """, (categoria_id,)).fetchall()
        
        conn.close()
        return jsonify([dict(s) for s in subcategorias])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/marcas/<int:subcategoria_id>")
def api_marcas_por_subcategoria(subcategoria_id):
    """Obtener marcas por subcategoría"""
    try:
        conn = get_db_connection()
        marcas = conn.execute("""
            SELECT id_marca, nombre, subcategoria_id
            FROM marcas
            WHERE subcategoria_id = ?
            ORDER BY nombre
        """, (subcategoria_id,)).fetchall()
        
        conn.close()
        return jsonify([dict(m) for m in marcas])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/versiones/<int:marca_id>")
def api_versiones_por_marca(marca_id):
    """Obtener versiones por marca"""
    try:
        conn = get_db_connection()
        versiones = conn.execute("""
            SELECT id_version, nombre, marca_id
            FROM versiones
            WHERE marca_id = ?
            ORDER BY nombre
        """, (marca_id,)).fetchall()
        
        conn.close()
        return jsonify([dict(v) for v in versiones])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ruta para crear lotes
@app.route("/crear_lote", methods=["POST"])
@login_required
def crear_lote():
    """Crear un nuevo lote con productos"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data.get('numero_lote') or not data.get('nro_factura') or not data.get('id_proveedor'):
            return jsonify({"success": False, "message": "Faltan datos requeridos del lote"}), 400
        
        if not data.get('productos') or len(data['productos']) == 0:
            return jsonify({"success": False, "message": "Debe agregar al menos un producto al lote"}), 400
        
        conn = get_db_connection()
        
        # Insertar el lote
        cursor = conn.execute("""
            INSERT INTO lotes (numero_lote, nro_factura, id_proveedor, fecha_factura, observaciones, fecha_carga)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (
            data['numero_lote'],
            data['nro_factura'],
            data['id_proveedor'],
            data['fecha_factura'],
            data.get('observaciones', '')
        ))
        
        lote_id = cursor.lastrowid
        
        # Procesar cada producto del lote
        for producto in data['productos']:
            if producto['tipo'] == 'existente':
                # Producto existente - solo agregar al lote
                conn.execute("""
                    INSERT INTO lotes_detalles (id_lote, id_producto, cantidad, precio_compra, precio_venta)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    lote_id,
                    producto['producto_existente'],
                    producto['cantidad'],
                    producto['precio_compra'],
                    producto['precio_venta']
                ))
                
                # Actualizar stock del producto existente
                conn.execute("""
                    UPDATE productos 
                    SET stock = stock + ?, 
                        precio_compra = ?, 
                        precio_venta = ?
                    WHERE id_producto = ?
                """, (
                    producto['cantidad'],
                    producto['precio_compra'],
                    producto['precio_venta'],
                    producto['producto_existente']
                ))
                
            else:
                # Producto nuevo - crear primero el producto
                cursor_producto = conn.execute("""
                    INSERT INTO productos (codigo, nombre, categoria_id, subcategoria_id, marca_id, version_id, precio_compra, precio_venta, eliminado)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    producto['codigo'],
                    producto['nombre'],
                    producto['categoria_id'],
                    producto['subcategoria_id'],
                    producto['marca_id'],
                    producto['version_id'],
                    producto['precio_compra'],
                    producto['precio_venta']
                ))
                
                producto_id = cursor_producto.lastrowid
                
                # Agregar al lote
                conn.execute("""
                    INSERT INTO lotes_detalles (id_lote, id_producto, cantidad, precio_compra, precio_venta)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    lote_id,
                    producto_id,
                    producto['cantidad'],
                    producto['precio_compra'],
                    producto['precio_venta']
                ))
                
                # Actualizar stock del producto
                conn.execute("""
                    UPDATE productos 
                    SET stock = stock + ?, 
                        precio_compra = ?, 
                        precio_venta = ?
                    WHERE id_producto = ?
                """, (
                    producto['cantidad'],
                    producto['precio_compra'],
                    producto['precio_venta'],
                    producto_id
                ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Lote creado correctamente",
            "lote_id": lote_id
        })
        
    except Exception as e:
        conn.close()
        print(f"Error al crear lote: {str(e)}")
        return jsonify({"success": False, "message": f"Error al crear el lote: {str(e)}"}), 500

# -------------------
# GESTIÓN DE USUARIOS
# -------------------
@app.route("/usuarios")
@login_required
def listar_usuarios():
    """Listar todos los usuarios del sistema"""
    conn = get_db_connection()
    usuarios = conn.execute("""
        SELECT id_usuario, username, nombre_completo, rol, activo, ultimo_login, fecha_creacion
        FROM usuarios
        ORDER BY fecha_creacion DESC
    """).fetchall()
    conn.close()
    return render_template("usuarios.html", usuarios=usuarios)

@app.route("/nuevo_usuario", methods=["GET", "POST"])
@login_required
def nuevo_usuario():
    """Crear un nuevo usuario"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        nombre_completo = request.form.get("nombre_completo")
        rol = request.form.get("rol", "vendedor")
        
        if not username or not password or not nombre_completo:
            flash("Todos los campos son requeridos", "error")
            return redirect(url_for("nuevo_usuario"))
        
        conn = get_db_connection()
        
        # Verificar si el usuario ya existe
        usuario_existente = conn.execute("SELECT id_usuario FROM usuarios WHERE username = ?", (username,)).fetchone()
        if usuario_existente:
            conn.close()
            flash("El nombre de usuario ya existe", "error")
            return redirect(url_for("nuevo_usuario"))
        
        # Crear hash de la contraseña
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Insertar nuevo usuario
        conn.execute("""
            INSERT INTO usuarios (username, password_hash, nombre_completo, rol, activo)
            VALUES (?, ?, ?, ?, 1)
        """, (username, password_hash, nombre_completo, rol))
        
        conn.commit()
        conn.close()
        
        flash("Usuario creado correctamente", "success")
        return redirect(url_for("listar_usuarios"))
    
    return render_template("nuevo_usuario.html")

@app.route("/editar_usuario/<int:id_usuario>", methods=["GET", "POST"])
@login_required
def editar_usuario(id_usuario):
    """Editar un usuario existente"""
    conn = get_db_connection()
    usuario = conn.execute("SELECT * FROM usuarios WHERE id_usuario = ?", (id_usuario,)).fetchone()
    
    if not usuario:
        conn.close()
        flash("Usuario no encontrado", "error")
        return redirect(url_for("listar_usuarios"))
    
    if request.method == "POST":
        nombre_completo = request.form.get("nombre_completo")
        rol = request.form.get("rol")
        activo = 1 if request.form.get("activo") else 0
        password = request.form.get("password")
        
        if not nombre_completo:
            flash("El nombre completo es requerido", "error")
            return redirect(url_for("editar_usuario", id_usuario=id_usuario))
        
        # Actualizar usuario
        if password:
            # Si se proporciona una nueva contraseña
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            conn.execute("""
                UPDATE usuarios 
                SET nombre_completo = ?, rol = ?, activo = ?, password_hash = ?
                WHERE id_usuario = ?
            """, (nombre_completo, rol, activo, password_hash, id_usuario))
        else:
            # Sin cambiar la contraseña
            conn.execute("""
                UPDATE usuarios 
                SET nombre_completo = ?, rol = ?, activo = ?
                WHERE id_usuario = ?
            """, (nombre_completo, rol, activo, id_usuario))
        
        conn.commit()
        conn.close()
        
        flash("Usuario actualizado correctamente", "success")
        return redirect(url_for("listar_usuarios"))
    
    conn.close()
    return render_template("editar_usuario.html", usuario=usuario)

@app.route("/eliminar_usuario/<int:id_usuario>")
@login_required
def eliminar_usuario(id_usuario):
    """Eliminar un usuario (solo desactivar)"""
    conn = get_db_connection()
    
    # Verificar que no sea el usuario admin principal
    usuario = conn.execute("SELECT username FROM usuarios WHERE id_usuario = ?", (id_usuario,)).fetchone()
    if usuario and usuario[0] == 'admin':
        conn.close()
        flash("No se puede eliminar el usuario administrador principal", "error")
        return redirect(url_for("listar_usuarios"))
    
    # Desactivar usuario
    conn.execute("UPDATE usuarios SET activo = 0 WHERE id_usuario = ?", (id_usuario,))
    conn.commit()
    conn.close()
    
    flash("Usuario desactivado correctamente", "success")
    return redirect(url_for("listar_usuarios"))

# -------------------
# API PARA SINCRONIZACIÓN DE USUARIOS
# -------------------
@app.route("/api/usuarios")
def api_usuarios():
    """Endpoint para sincronizar usuarios con el POS"""
    try:
        conn = get_db_connection()
        usuarios = conn.execute("""
            SELECT username, password_hash, nombre_completo, activo
            FROM usuarios
            WHERE activo = 1
        """).fetchall()
        conn.close()
        
        return jsonify([dict(usuario) for usuario in usuarios])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Iniciar sincronización automática si está habilitada
if __name__ == "__main__":
    print("🚀 Iniciando servidor Flask Admin...")
    port = int(os.environ.get('PORT', 5000))
    print(f"📍 URL: http://0.0.0.0:{port}")
    print("🔑 Usuario: admin")
    print("🔑 Contraseña: admin123")
    print("=" * 50)
    
    if app.config.get('SYNC_INTERVAL', 0) > 0:
        start_sync_scheduler()
    
    try:
        # Configuración para Render
        port = int(os.environ.get('PORT', 5000))
        debug = app.config.get('DEBUG', False)
        
        app.run(debug=debug, 
                host='0.0.0.0',  # Permitir conexiones externas
                port=port, 
                use_reloader=False)  # Desactivar reloader para evitar problemas
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error al iniciar el servidor: {e}")
