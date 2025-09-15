#!/usr/bin/env python3
"""Script para verificar la base de datos correcta"""

import sqlite3

def check_correct_db():
    """Verificar la base de datos correcta (db/admin_database.db)"""
    
    try:
        conn = sqlite3.connect('db/admin_database.db')
        cursor = conn.cursor()
        
        # Verificar tablas existentes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = cursor.fetchall()
        
        print("📋 Tablas en db/admin_database.db:")
        for tabla in tablas:
            print(f"  - {tabla[0]}")
        
        if not tablas:
            print("  ❌ No hay tablas en la base de datos")
        else:
            print(f"  ✅ Total: {len(tablas)} tablas")
        
        # Verificar si existe la tabla ventas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ventas'")
        ventas_table = cursor.fetchone()
        
        if ventas_table:
            print("\n✅ Tabla 'ventas' existe")
            # Verificar estructura
            cursor.execute("PRAGMA table_info(ventas)")
            columns = cursor.fetchall()
            print("📊 Estructura de la tabla ventas:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Verificar si hay ventas
            cursor.execute("SELECT COUNT(*) FROM ventas")
            count = cursor.fetchone()[0]
            print(f"\n📈 Total de ventas: {count}")
            
            if count > 0:
                cursor.execute("SELECT id_venta, fecha_venta, total FROM ventas ORDER BY id_venta")
                ventas = cursor.fetchall()
                print("📋 Ventas existentes:")
                for venta in ventas:
                    print(f"  - ID: {venta[0]}, Fecha: {venta[1]}, Total: {venta[2]}")
        else:
            print("\n❌ Tabla 'ventas' NO existe")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_correct_db()

