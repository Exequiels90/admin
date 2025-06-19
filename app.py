from flask import Flask, render_template, request, redirect, url_for, session, flash

import sqlite3
import os
from functools import wraps

def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorada


app = Flask(__name__)
app.secret_key = 'admin123'  # 🔒 Agregá esta línea

DB_PATH = os.path.join("db", "productos.db")

# ----------------- BASE DE DATOS ----------------- #
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                precio REAL NOT NULL,
                stock INTEGER NOT NULL,
                categoria TEXT,
                genero TEXT,
                talle TEXT,
                imagen TEXT,
                activo INTEGER DEFAULT 1
            )
        ''')
        conn.commit()

# ----------------- RUTAS ----------------- #

@app.route("/")
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE activo = 1")
    productos = c.fetchall()
    conn.close()
    return render_template("lista.html", productos=productos)

@app.route("/admin")
@login_requerido
def admin():
    if "usuario" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE activo = 1")
    productos = c.fetchall()
    conn.close()
    return render_template("admin.html", productos=productos)


@app.route("/admin/agregar", methods=["GET", "POST"])
@login_requerido
def agregar_producto():
    if request.method == "POST":
        datos = (
            request.form["nombre"],
            request.form["descripcion"],
            float(request.form["precio"]),
            int(request.form["stock"]),
            request.form["categoria"],
            request.form["genero"],
            request.form["talle"],
            request.form["imagen"]
        )
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO productos (nombre, descripcion, precio, stock, categoria, genero, talle, imagen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, datos)
        conn.commit()
        conn.close()
        return redirect(url_for("admin"))
    return render_template("admin_form.html")


@app.route("/admin/eliminar/<int:producto_id>", methods=["POST"])
@login_requerido
def eliminar_producto(producto_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE productos SET activo = 0 WHERE id = ?", (producto_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))



@app.route("/admin/reactivar/<int:id>")
@login_requerido
def reactivar_producto(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE productos SET activo = 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/editar/<int:producto_id>", methods=["GET", "POST"])
@login_requerido
def editar_producto(producto_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == "POST":
        datos = (
            request.form["nombre"],
            request.form["descripcion"],
            float(request.form["precio"]),
            int(request.form["stock"]),
            request.form["categoria"],
            request.form["genero"],
            request.form["talle"],
            request.form["imagen"],
            producto_id
        )
        c.execute("""
            UPDATE productos SET
                nombre = ?, descripcion = ?, precio = ?, stock = ?,
                categoria = ?, genero = ?, talle = ?, imagen = ?
            WHERE id = ?
        """, datos)
        conn.commit()
        conn.close()
        return redirect(url_for("admin"))

    c.execute("SELECT * FROM productos WHERE id = ?", (producto_id,))
    producto = c.fetchone()
    conn.close()
    return render_template("editar.html", producto=producto)

@app.route("/catalogo")
def catalogo():
    genero = request.args.get("genero")
    categoria = request.args.get("categoria")
    talle = request.args.get("talle")

    query = "SELECT * FROM productos WHERE activo = 1"
    params = []

    if genero:
        query += " AND genero = ?"
        params.append(genero)

    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)

    if talle:
        query += " AND talle = ?"
        params.append(talle)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(query, params)
    productos = c.fetchall()

    # Obtener valores únicos para los filtros
    c.execute("SELECT DISTINCT genero FROM productos WHERE activo = 1 AND genero IS NOT NULL")
    generos = [row[0] for row in c.fetchall()]

    c.execute("SELECT DISTINCT categoria FROM productos WHERE activo = 1 AND categoria IS NOT NULL")
    categorias = [row[0] for row in c.fetchall()]

    c.execute("SELECT DISTINCT talle FROM productos WHERE activo = 1 AND talle IS NOT NULL")
    talles = [row[0] for row in c.fetchall()]

    conn.close()
    return render_template("catalogo.html", productos=productos, generos=generos, categorias=categorias, talles=talles)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (username, password))
        usuario = c.fetchone()
        conn.close()

        if usuario:
            session["usuario"] = username
            flash("Inicio de sesión exitoso", "success")
            return redirect(url_for("admin"))
        else:
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.pop("usuario", None)
    flash("Sesión cerrada", "info")
    return redirect(url_for("login"))

@app.route("/admin/eliminados")
@login_requerido
def ver_eliminados():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE activo = 0")
    productos = c.fetchall()
    conn.close()
    return render_template("eliminados.html", productos=productos)



# ----------------- INICIO ----------------- #
if __name__ == "__main__":
    os.makedirs("db", exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        
        # Crear tabla de productos (por si no la tenés acá)
        c.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                precio REAL NOT NULL,
                stock INTEGER NOT NULL,
                categoria TEXT,
                genero TEXT,
                talle TEXT,
                imagen TEXT,
                activo INTEGER DEFAULT 1
            )
        ''')

        # Crear tabla de usuarios
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')

        # Crear usuario admin por defecto si no existe
        c.execute("SELECT * FROM usuarios WHERE username = 'admin'")
        if not c.fetchone():
            c.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", ('admin', 'admin123'))

        conn.commit()

    app.run(debug=True)

