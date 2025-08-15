import sqlite3
from jinja2 import Environment, FileSystemLoader

DB_PATH = "db/productos.db"

# Cargar la plantilla
env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template("catalogo_base.html")

# Obtener productos activos
with sqlite3.connect(DB_PATH) as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE activo = 1")
    productos = c.fetchall()

# Renderizar HTML
html = template.render(productos=productos)

# Guardar en archivo
with open("catalogo.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Catálogo generado como 'catalogo.html'")
import sqlite3
from jinja2 import Environment, FileSystemLoader

DB_PATH = "db/productos.db"

# Cargar la plantilla
env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template("catalogo_base.html")

# Obtener productos activos
with sqlite3.connect(DB_PATH) as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM productos WHERE activo = 1")
    productos = c.fetchall()

# Renderizar HTML
html = template.render(productos=productos)

# Guardar en archivo
with open("catalogo.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Catálogo generado como 'catalogo.html'")
