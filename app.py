from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# Ruta de la base de datos
DB_PATH = os.path.join("db", "productos.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    return redirect(url_for('admin'))


@app.route('/admin')
def admin():
    conn = get_db_connection()
    productos = conn.execute("""
        SELECT productos.id_producto, productos.nombre, categorias.nombre AS categoria, productos.activo
        FROM productos
        LEFT JOIN categorias ON productos.id_categoria = categorias.id_categoria
        ORDER BY productos.nombre
    """).fetchall()

    conn.close()
    return render_template('admin.html', productos=productos)


@app.route('/nuevo_producto', methods=['GET', 'POST'])
def nuevo_producto():
    conn = sqlite3.connect('db/productos.db')
    c = conn.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre']
        categoria_id = request.form['categoria_id']
        stock = int(request.form['stock'])
        lote = request.form['lote']

        c.execute("INSERT INTO productos (nombre, id_categoria, stock, lote) VALUES (?, ?, ?, ?)",
                (nombre, categoria_id, stock, lote))

        conn.commit()
        conn.close()
        return redirect(url_for('admin'))

    # Si es GET, mostrar el formulario con las categorías disponibles
    c.execute("SELECT id_categoria, nombre FROM categorias")
    categorias = c.fetchall()
    conn.close()
    return render_template('nuevo_producto.html', categorias=categorias)


@app.route('/categorias')
def listar_categorias():
    conn = get_db_connection()
    categorias = conn.execute("SELECT * FROM categorias").fetchall()
    conn.close()
    return render_template('categorias.html', categorias=categorias)


@app.route('/nueva_categoria', methods=['GET', 'POST'])
def nueva_categoria():
    if request.method == 'POST':
        nombre = request.form['nombre']
        conn = get_db_connection()
        conn.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
        conn.commit()
        conn.close()
        return redirect(url_for('listar_categorias'))
    return render_template('nueva_categoria.html')

@app.route('/editar_producto/<int:id_producto>', methods=['GET', 'POST'])
def editar_producto(id_producto):
    conn = get_db_connection()

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        id_categoria = request.form['id_categoria']
        precio = float(request.form['precio'])

        # Actualiza el producto
        conn.execute("""UPDATE productos 
                        SET nombre = ?, descripcion = ?, id_categoria = ? 
                        WHERE id_producto = ?""",
                     (nombre, descripcion, id_categoria, id_producto))

        # Actualiza el precio solo si es distinto al último
        ultimo_precio = conn.execute("""SELECT precio_unitario 
                                        FROM precios_venta 
                                        WHERE id_producto = ? 
                                        ORDER BY desde_fecha DESC 
                                        LIMIT 1""", (id_producto,)).fetchone()

        if not ultimo_precio or float(ultimo_precio['precio_unitario']) != precio:
            conn.execute("""INSERT INTO precios_venta (id_producto, precio_unitario, desde_fecha) 
                            VALUES (?, ?, ?)""", (id_producto, precio, datetime.now().date()))

        conn.commit()
        conn.close()
        return redirect(url_for('admin'))

    else:
        producto = conn.execute("""SELECT * FROM productos WHERE id_producto = ?""", (id_producto,)).fetchone()
        categorias = conn.execute("SELECT * FROM categorias").fetchall()
        precio = conn.execute("""SELECT precio_unitario FROM precios_venta 
                                 WHERE id_producto = ? ORDER BY desde_fecha DESC LIMIT 1""",
                              (id_producto,)).fetchone()

        conn.close()
        return render_template('editar_producto.html',
                               producto=producto,
                               categorias=categorias,
                               precio=precio['precio_unitario'] if precio else 0)


if __name__ == '__main__':
    app.run(debug=True)
