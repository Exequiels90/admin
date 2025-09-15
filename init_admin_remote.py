#!/usr/bin/env python3
"""
Script para inicializar la base de datos del Admin en PythonAnywhere
"""

import requests
import json

def main():
    print("🔧 Inicializando base de datos del Admin en PythonAnywhere...")
    
    # Crear la tabla detalles_venta
    sql_commands = [
        """
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
        """
    ]
    
    for sql in sql_commands:
        try:
            print(f"📤 Ejecutando: {sql[:50]}...")
            # Enviar comando SQL al Admin
            response = requests.post(
                'https://chimuelo1290.pythonanywhere.com/api/execute_sql',
                json={'sql': sql},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Comando ejecutado correctamente")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()




