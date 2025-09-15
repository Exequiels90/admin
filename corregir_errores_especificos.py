#!/usr/bin/env python3
"""
Script para corregir errores específicos identificados en los logs
"""

import os
import re

def corregir_errores_especificos():
    """Corrige los errores específicos identificados en los logs"""
    
    app_path = "app.py"
    
    if not os.path.exists(app_path):
        print("❌ No se encontró app.py")
        return False
    
    print("🔍 Leyendo app.py...")
    
    # Leer el archivo actual
    with open(app_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"📄 Archivo leído: {len(lines)} líneas")
    
    # 1. Corregir error de sintaxis en línea 1723
    if len(lines) > 1722:
        line_1723 = lines[1722].strip()  # Línea 1723 (índice 1722)
        print(f"🔍 Línea 1723: {line_1723}")
        
        if line_1723.startswith('except Exception as e:'):
            print("⚠️  Encontrado 'except' sin 'try' en línea 1723")
            # Comentar la línea problemática
            lines[1722] = f"    # {line_1723}\n"
            print("✅ Línea 1723 comentada")
    
    # 2. Buscar y corregir endpoints duplicados
    print("🔍 Buscando endpoints duplicados...")
    
    # Buscar todas las definiciones de rutas
    route_definitions = {}
    for i, line in enumerate(lines):
        if '@app.route(' in line:
            # Extraer la ruta
            match = re.search(r'@app\.route\([\'"]([^\'"]+)[\'"]', line)
            if match:
                route = match.group(1)
                if route not in route_definitions:
                    route_definitions[route] = []
                route_definitions[route].append(i)
    
    # Identificar duplicados
    duplicates = {route: indices for route, indices in route_definitions.items() if len(indices) > 1}
    
    if duplicates:
        print(f"⚠️  Endpoints duplicados encontrados: {list(duplicates.keys())}")
        
        for route, indices in duplicates.items():
            print(f"🔧 Corrigiendo duplicado: {route}")
            # Comentar todas las definiciones excepto la primera
            for i, line_idx in enumerate(indices[1:], 1):
                if not lines[line_idx].strip().startswith('#'):
                    lines[line_idx] = f"# {lines[line_idx]}"
                    print(f"✅ Línea {line_idx + 1} comentada (duplicado #{i + 1})")
    
    # 3. Corregir consultas SQL problemáticas
    print("🔍 Buscando consultas SQL problemáticas...")
    
    for i, line in enumerate(lines):
        if 'v.fecha_registro' in line:
            print(f"⚠️  Línea {i + 1}: {line.strip()}")
            # Reemplazar fecha_registro con fecha_venta
            lines[i] = line.replace('v.fecha_registro', 'v.fecha_venta')
            print(f"✅ Línea {i + 1} corregida")
    
    # 4. Corregir referencias a endpoints inexistentes
    print("🔍 Buscando referencias a endpoints inexistentes...")
    
    for i, line in enumerate(lines):
        if 'listar_ventas' in line:
            print(f"⚠️  Línea {i + 1}: {line.strip()}")
            # Reemplazar listar_ventas con ventas
            lines[i] = line.replace('listar_ventas', 'ventas')
            print(f"✅ Línea {i + 1} corregida")
    
    # 5. Crear template subcategorias.html si no existe
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
    
    # 6. Agregar columna id_usuario a tabla ventas si no existe
    print("🔍 Verificando estructura de base de datos...")
    
    # Buscar la función que crea la tabla ventas
    for i, line in enumerate(lines):
        if 'CREATE TABLE IF NOT EXISTS ventas' in line:
            print(f"🔍 Encontrada definición de tabla ventas en línea {i + 1}")
            # Buscar si ya tiene id_usuario
            j = i
            has_id_usuario = False
            while j < len(lines) and not lines[j].strip().startswith(')'):
                if 'id_usuario' in lines[j]:
                    has_id_usuario = True
                    break
                j += 1
            
            if not has_id_usuario:
                print("⚠️  Tabla ventas no tiene columna id_usuario")
                # Agregar la columna antes del cierre de la tabla
                j = i
                while j < len(lines) and not lines[j].strip().startswith(')'):
                    j += 1
                
                if j < len(lines):
                    # Insertar la columna antes del cierre
                    lines.insert(j, '    id_usuario INTEGER,\n')
                    print("✅ Columna id_usuario agregada a tabla ventas")
    
    # Guardar el archivo corregido
    print("💾 Guardando archivo corregido...")
    with open(app_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
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
    print("🚀 Iniciando corrección de errores específicos...")
    
    if corregir_errores_especificos():
        if verificar_sintaxis():
            print("🎉 ¡Todos los errores específicos han sido corregidos!")
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


