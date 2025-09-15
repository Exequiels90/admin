#!/usr/bin/env python3
"""
Script para probar la configuración
"""

import os
import sys

def test_config():
    """Prueba la configuración"""
    
    try:
        # Verificar variables de entorno
        print("🔍 Variables de entorno:")
        print(f"   FLASK_ENV: {os.environ.get('FLASK_ENV', 'No definida')}")
        print(f"   SECRET_KEY: {os.environ.get('SECRET_KEY', 'No definida')}")
        print(f"   DATABASE_PATH: {os.environ.get('DATABASE_PATH', 'No definida')}")
        
        # Importar configuración
        print("\n🔍 Importando configuración...")
        from config import config
        
        # Probar configuración
        print("✅ Configuración importada correctamente")
        
        # Verificar configuración por defecto
        default_config = config['default']
        print(f"✅ Configuración por defecto: {default_config}")
        
        # Verificar ruta de BD
        db_path = default_config.DATABASE_PATH
        print(f"📋 Ruta de BD: {db_path}")
        
        # Verificar si existe la BD
        if os.path.exists(db_path):
            print(f"✅ Base de datos existe: {db_path}")
        else:
            print(f"❌ Base de datos NO existe: {db_path}")
            
            # Verificar si existe la carpeta db
            db_dir = os.path.dirname(db_path)
            if os.path.exists(db_dir):
                print(f"✅ Carpeta db existe: {db_dir}")
            else:
                print(f"❌ Carpeta db NO existe: {db_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_config()



