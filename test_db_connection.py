#!/usr/bin/env python3
"""
Script para probar la conexión a la base de datos
"""

import sqlite3
import os

def test_db_connection():
    """Prueba la conexión a la base de datos"""
    
    try:
        # Verificar si existe el archivo de BD
        db_path = "db/admin_database.db"
        if not os.path.exists(db_path):
            print(f"❌ No existe el archivo de BD: {db_path}")
            return False
        
        # Conectar a la BD
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tablas principales
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print("✅ Conexión a BD exitosa")
        print(f"📋 Tablas encontradas: {len(tables)}")
        
        for table in tables:
            print(f"   - {table[0]}")
        
        # Verificar tabla ventas
        try:
            cursor.execute("SELECT COUNT(*) FROM ventas")
            count = cursor.fetchone()[0]
            print(f"✅ Tabla ventas: {count} registros")
        except Exception as e:
            print(f"❌ Error en tabla ventas: {e}")
        
        # Verificar tabla clientes
        try:
            cursor.execute("SELECT COUNT(*) FROM clientes")
            count = cursor.fetchone()[0]
            print(f"✅ Tabla clientes: {count} registros")
        except Exception as e:
            print(f"❌ Error en tabla clientes: {e}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    test_db_connection()



