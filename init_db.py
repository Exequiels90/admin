#!/usr/bin/env python3
"""
Script de inicialización de la base de datos para Render
Este script se ejecuta automáticamente cuando se despliega la aplicación
"""

import os
import sys

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def init_database():
    """Inicializa la base de datos en producción"""
    try:
        print("🔧 Inicializando base de datos en producción...")
        
        # Crear directorio db si no existe
        os.makedirs("db", exist_ok=True)
        
        # Ejecutar setup_database.py
        from setup_database import main
        main()
        
        print("✅ Base de datos inicializada correctamente en producción!")
        return True
        
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
