#!/usr/bin/env python3
"""
Script para crear la tabla detalles_venta en el Admin
"""

import sqlite3
import os

def main():
    print("🔧 Creando tabla detalles_venta en el Admin...")
    
    # Conectar a la base de datos del Admin
    db_path = 'db/admin_database.db'
    if not os.path.exists(db_path):
        print(f"❌ Error: La base de datos no existe en {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
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
        print("✅ Tabla detalles_venta creada correctamente")
        
        # Verificar que la tabla existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='detalles_venta'")
        if cursor.fetchone():
            print("✅ Tabla detalles_venta verificada")
        else:
            print("❌ Error: La tabla no se creó")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()




