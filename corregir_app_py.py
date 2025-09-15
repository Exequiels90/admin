#!/usr/bin/env python3
"""
Script para corregir todos los errores de indentación en app.py
"""

import re

def corregir_app_py():
    """Corrige todos los errores de indentación en app.py"""
    
    print("🔧 Corrigiendo app.py...")
    
    # Leer el archivo
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Dividir en líneas
    lines = content.split('\n')
    
    # Corregir errores específicos
    for i, line in enumerate(lines):
        # Corregir función login_required mal indentada
        if line.strip() == 'def login_required(f):' and line.startswith('        '):
            lines[i] = 'def login_required(f):'
        
        # Corregir función admin_required mal indentada
        if line.strip() == 'def admin_required(f):' and line.startswith('        '):
            lines[i] = 'def admin_required(f):'
        
        # Corregir función hash_password mal indentada
        if line.strip() == 'def hash_password(password):' and line.startswith('    '):
            lines[i] = 'def hash_password(password):'
        
        # Corregir función verify_user mal indentada
        if line.strip() == 'def verify_user(username, password):' and line.startswith('    '):
            lines[i] = 'def verify_user(username, password):'
        
        # Corregir función update_last_login mal indentada
        if line.strip() == 'def update_last_login(user_id):' and line.startswith('    '):
            lines[i] = 'def update_last_login(user_id):'
        
        # Corregir función get_db_connection mal indentada
        if line.strip() == 'def get_db_connection():' and line.startswith('    '):
            lines[i] = 'def get_db_connection():'
    
    # Unir las líneas corregidas
    content_corregido = '\n'.join(lines)
    
    # Guardar el archivo corregido
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content_corregido)
    
    print("✅ app.py corregido exitosamente")

def verificar_sintaxis():
    """Verifica que la sintaxis de app.py sea correcta"""
    try:
        import py_compile
        py_compile.compile('app.py', doraise=True)
        print("✅ Sintaxis de app.py verificada correctamente")
        return True
    except py_compile.PyCompileError as e:
        print(f"❌ Error de sintaxis: {e}")
        return False

def main():
    print("🚀 Iniciando corrección de app.py...")
    
    corregir_app_py()
    
    if verificar_sintaxis():
        print("🎉 ¡app.py corregido exitosamente!")
        print("📋 Próximos pasos:")
        print("1. Hacer commit y push de los cambios")
        print("2. Recargar la web app en PythonAnywhere")
        print("3. Verificar que la aplicación funcione correctamente")
    else:
        print("❌ Aún hay errores de sintaxis que necesitan corrección manual")

if __name__ == "__main__":
    main()


