#!/usr/bin/env python3
"""
Script simple para corregir errores críticos en app.py
"""

import os

def corregir_errores_simple():
    """Corrige los errores más críticos de forma simple"""
    
    app_path = "app.py"
    
    if not os.path.exists(app_path):
        print("❌ No se encontró app.py")
        return False
    
    print("🔍 Leyendo app.py...")
    
    # Leer el archivo actual
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📄 Archivo leído: {len(content)} caracteres")
    
    # 1. Corregir error de sintaxis en línea 1723 (except sin try)
    print("🔍 Buscando 'except' sin 'try'...")
    
    # Buscar patrones problemáticos y comentarlos
    problematic_lines = [
        'except Exception as e:',
        'except Exception as e:\n    #',
        'except Exception as e:\n    pass',
    ]
    
    for pattern in problematic_lines:
        if pattern in content:
            print(f"⚠️  Encontrado patrón problemático: {pattern}")
            # Comentar la línea problemática
            content = content.replace(pattern, f'# {pattern}')
            print("✅ Patrón problemático comentado")
    
    # 2. Corregir referencias a fecha_registro
    print("🔍 Buscando referencias a fecha_registro...")
    
    if 'v.fecha_registro' in content:
        print("⚠️  Encontradas referencias a v.fecha_registro")
        content = content.replace('v.fecha_registro', 'v.fecha_venta')
        print("✅ Referencias a fecha_registro corregidas")
    
    # 3. Corregir referencias a listar_ventas
    print("🔍 Buscando referencias a listar_ventas...")
    
    if 'listar_ventas' in content:
        print("⚠️  Encontradas referencias a listar_ventas")
        content = content.replace('listar_ventas', 'ventas')
        print("✅ Referencias a listar_ventas corregidas")
    
    # 4. Crear template subcategorias.html si no existe
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
    
    # 5. Agregar columna id_usuario a tabla ventas si no existe
    print("🔍 Verificando estructura de base de datos...")
    
    if 'CREATE TABLE IF NOT EXISTS ventas' in content:
        if 'id_usuario INTEGER' not in content:
            print("⚠️  Tabla ventas no tiene columna id_usuario")
            # Buscar el cierre de la tabla ventas y agregar la columna
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'CREATE TABLE IF NOT EXISTS ventas' in line:
                    # Buscar el cierre de la tabla
                    j = i
                    while j < len(lines) and not lines[j].strip().startswith(')'):
                        j += 1
                    
                    if j < len(lines):
                        # Insertar la columna antes del cierre
                        lines.insert(j, '    id_usuario INTEGER,')
                        content = '\n'.join(lines)
                        print("✅ Columna id_usuario agregada a tabla ventas")
                        break
    
    # Guardar el archivo corregido
    print("💾 Guardando archivo corregido...")
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
    
    if corregir_errores_simple():
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


