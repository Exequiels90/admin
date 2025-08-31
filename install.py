#!/usr/bin/env python3
"""
Script de instalación automática para el Sistema de Administración POS
"""

import os
import sys
import sqlite3
import hashlib
import shutil
from pathlib import Path

def print_banner():
    """Imprime el banner de instalación"""
    print("=" * 60)
    print("🏪 SISTEMA DE ADMINISTRACIÓN POS - INSTALADOR")
    print("=" * 60)
    print("Versión 2.0 - Agosto 2024")
    print("=" * 60)

def check_python_version():
    """Verifica la versión de Python"""
    if sys.version_info < (3, 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {sys.version}")
        sys.exit(1)
    print("✅ Python 3.8+ detectado")

def install_dependencies():
    """Instala las dependencias"""
    print("\n📦 Instalando dependencias...")
    try:
        os.system("pip install -r requirements.txt")
        print("✅ Dependencias instaladas correctamente")
    except Exception as e:
        print(f"❌ Error al instalar dependencias: {e}")
        sys.exit(1)

def create_directories():
    """Crea los directorios necesarios"""
    print("\n📁 Creando directorios...")
    directories = ["db", "logs", "static/uploads"]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Directorio creado: {directory}")

def setup_database():
    """Configura la base de datos"""
    print("\n🗄️ Configurando base de datos...")
    try:
        # Ejecutar script de configuración de BD
        os.system("python setup_db.py")
        print("✅ Base de datos configurada correctamente")
    except Exception as e:
        print(f"❌ Error al configurar base de datos: {e}")
        sys.exit(1)

def create_env_file():
    """Crea el archivo .env si no existe"""
    print("\n⚙️ Configurando variables de entorno...")
    
    env_file = ".env"
    if os.path.exists(env_file):
        print("✅ Archivo .env ya existe")
        return
    
    # Generar clave secreta
    import secrets
    secret_key = secrets.token_hex(32)
    
    env_content = f"""# Configuración del Sistema de Administración POS
SECRET_KEY={secret_key}
DATABASE_PATH=db/productos.db
FLASK_ENV=development
SESSION_LIFETIME=3600
LOG_LEVEL=INFO
SYNC_INTERVAL=300
SYNC_TIMEOUT=10

# Configuración de seguridad
SESSION_COOKIE_SECURE=False
WTF_CSRF_ENABLED=True
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("✅ Archivo .env creado con configuración por defecto")

def create_admin_user():
    """Crea el usuario administrador por defecto"""
    print("\n👤 Configurando usuario administrador...")
    
    try:
        conn = sqlite3.connect("db/productos.db")
        cursor = conn.cursor()
        
        # Verificar si ya existe el usuario admin
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            # Crear usuario admin
            password_hash = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("""
                INSERT INTO usuarios (username, password_hash, nombre_completo, rol, activo)
                VALUES ('admin', ?, 'Administrador', 'admin', 1)
            """, (password_hash,))
            conn.commit()
            print("✅ Usuario administrador creado:")
            print("   Usuario: admin")
            print("   Contraseña: admin123")
        else:
            print("✅ Usuario administrador ya existe")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error al crear usuario administrador: {e}")

def create_sample_data():
    """Crea datos de ejemplo"""
    print("\n📊 Creando datos de ejemplo...")
    
    try:
        conn = sqlite3.connect("db/productos.db")
        cursor = conn.cursor()
        
        # Categorías básicas
        categorias = [
            "Alimentos",
            "Bebidas", 
            "Limpieza",
            "Higiene Personal",
            "Otros"
        ]
        
        for categoria in categorias:
            cursor.execute("SELECT COUNT(*) FROM categorias WHERE nombre = ?", (categoria,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO categorias (nombre) VALUES (?)", (categoria,))
        
        # Unidades de medida
        unidades = [
            ("unidad", "Unidad"),
            ("kg", "Kilogramo"),
            ("g", "Gramo"),
            ("l", "Litro"),
            ("ml", "Mililitro"),
            ("m", "Metro"),
            ("cm", "Centímetro"),
            ("lb", "Libra"),
            ("oz", "Onza")
        ]
        
        for codigo, nombre in unidades:
            cursor.execute("SELECT COUNT(*) FROM unidades_medida WHERE codigo = ?", (codigo,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO unidades_medida (codigo, nombre) VALUES (?, ?)", (codigo, nombre))
        
        conn.commit()
        conn.close()
        print("✅ Datos de ejemplo creados")
    except Exception as e:
        print(f"❌ Error al crear datos de ejemplo: {e}")

def show_final_instructions():
    """Muestra las instrucciones finales"""
    print("\n" + "=" * 60)
    print("🎉 ¡INSTALACIÓN COMPLETADA!")
    print("=" * 60)
    print("\n📋 Próximos pasos:")
    print("1. Iniciar el servidor:")
    print("   python app.py")
    print("\n2. Abrir en el navegador:")
    print("   http://localhost:5000")
    print("\n3. Iniciar sesión con:")
    print("   Usuario: admin")
    print("   Contraseña: admin123")
    print("\n4. Configurar clientes POS:")
    print("   - Ir a 'Clientes POS'")
    print("   - Registrar URLs de clientes POS")
    print("\n📚 Documentación:")
    print("   Ver README.md para más información")
    print("\n🔧 Configuración avanzada:")
    print("   Editar archivo .env para personalizar")
    print("=" * 60)

def main():
    """Función principal de instalación"""
    print_banner()
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("app.py"):
        print("❌ Error: Ejecutar este script desde el directorio admin/")
        sys.exit(1)
    
    try:
        check_python_version()
        install_dependencies()
        create_directories()
        create_env_file()
        setup_database()
        create_admin_user()
        create_sample_data()
        show_final_instructions()
        
    except KeyboardInterrupt:
        print("\n\n❌ Instalación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error durante la instalación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
