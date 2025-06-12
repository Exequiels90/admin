from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
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

@app.route("/admin", methods=["GET", "POST"])
def admin():
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
    return render_template("admin.html")

# ----------------- INICIO ----------------- #
if __name__ == "__main__":
    os.makedirs("db", exist_ok=True)
    init_db()
    app.run(debug=True)
