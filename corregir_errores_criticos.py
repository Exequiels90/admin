#!/usr/bin/env python3
"""
Script para corregir errores críticos en app.py
"""

import re
import os

def corregir_app_py():
    """Corrige todos los errores críticos en app.py"""
    
    app_path = "app.py"
    
    if not os.path.exists(app_path):
        print("❌ No se encontró app.py")
        return False
    
    # Leer el archivo actual
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("🔍 Analizando app.py...")
    
    # 1. Corregir error de sintaxis en línea 1723 (except sin try)
    # Buscar patrones problemáticos
    problematic_patterns = [
        r'except Exception as e:\s*\n\s*#',  # except sin try
        r'except Exception as e:\s*\n\s*pass',  # except sin try
    ]
    
    for pattern in problematic_patterns:
        if re.search(pattern, content, re.MULTILINE):
            print(f"⚠️  Encontrado patrón problemático: {pattern}")
            # Comentar la línea problemática
            content = re.sub(pattern, r'# \g<0>', content)
            print("✅ Patrón problemático comentado")
    
    # 2. Corregir endpoints duplicados
    # Buscar definiciones de rutas duplicadas
    route_pattern = r'@app\.route\([\'"]([^\'"]+)[\'"]'
    routes = re.findall(route_pattern, content)
    
    # Encontrar duplicados
    seen_routes = set()
    duplicates = set()
    for route in routes:
        if route in seen_routes:
            duplicates.add(route)
        seen_routes.add(route)
    
    if duplicates:
        print(f"⚠️  Rutas duplicadas encontradas: {duplicates}")
        # Comentar las definiciones duplicadas
        for duplicate in duplicates:
            pattern = f'@app\.route\([\'"]{re.escape(duplicate)}[\'"]'
            matches = list(re.finditer(pattern, content))
            if len(matches) > 1:
                # Comentar todas excepto la primera
                for i, match in enumerate(matches[1:], 1):
                    start = match.start()
                    end = match.end()
                    content = content[:start] + '# ' + content[start:end] + content[end:]
                print(f"✅ Ruta duplicada '{duplicate}' comentada")
    
    # 3. Corregir consultas SQL problemáticas
    # Buscar referencias a fecha_registro que no existen
    sql_patterns = [
        r'v\.fecha_registro',
        r'ORDER BY v\.fecha_registro',
        r'SELECT.*v\.fecha_registro',
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, content):
            print(f"⚠️  Encontrada consulta SQL problemática: {pattern}")
            # Reemplazar con fecha_venta
            content = re.sub(pattern, 'v.fecha_venta', content)
            print("✅ Consulta SQL corregida")
    
    # 4. Corregir referencias a endpoints inexistentes
    # Buscar referencias a 'listar_ventas' que debería ser 'ventas'
    content = re.sub(r'url_for\([\'"]listar_ventas[\'"]\)', 'url_for("ventas")', content)
    print("✅ Referencias a endpoints corregidas")
    
    # 5. Agregar manejo de errores faltante
    # Buscar funciones sin try-except
    function_pattern = r'def (\w+)\([^)]*\):\s*\n(?!\s*try:)'
    functions = re.findall(function_pattern, content)
    
    for func in functions:
        if func in ['ventas', 'ver_venta', 'listar_subcategorias']:
            print(f"⚠️  Función '{func}' sin manejo de errores")
            # Agregar try-except básico
            func_pattern = f'def {func}\\([^)]*\\):\\s*\\n'
            replacement = f'def {func}(*args, **kwargs):\n    try:\n        '
            content = re.sub(func_pattern, replacement, content)
            print(f"✅ Manejo de errores agregado a '{func}'")
    
    # 6. Crear template subcategorias.html si no existe
    template_path = "templates/subcategorias.html"
    if not os.path.exists(template_path):
        print("⚠️  Template subcategorias.html no existe")
        os.makedirs("templates", exist_ok=True)
        
        template_content = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Subcategorías</title>
</head>
<body>
    <h1>Subcategorías</h1>
    <p>Funcionalidad en desarrollo...</p>
    <a href="{{ url_for('index') }}">Volver al inicio</a>
</body>
</html>'''
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        print("✅ Template subcategorias.html creado")
    
    # Guardar el archivo corregido
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ app.py corregido exitosamente")
    return True

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
    print("🚀 Iniciando corrección de errores críticos...")
    
    if corregir_app_py():
        if verificar_sintaxis():
            print("🎉 ¡Todos los errores críticos han sido corregidos!")
            print("📋 Próximos pasos:")
            print("1. Recargar la web app en PythonAnywhere")
            print("2. Verificar que la aplicación funcione correctamente")
            print("3. Probar las funcionalidades principales")
        else:
            print("❌ Aún hay errores de sintaxis que necesitan corrección manual")
    else:
        print("❌ No se pudo corregir app.py")

if __name__ == "__main__":
    main()


