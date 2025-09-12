#!/usr/bin/env python3
"""
Script para probar la sintaxis del archivo app.py
"""

import ast
import sys

def test_syntax():
    """Prueba la sintaxis del archivo app.py"""
    
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Intentar parsear el archivo
        ast.parse(source)
        print("✅ Sintaxis correcta")
        return True
        
    except SyntaxError as e:
        print(f"❌ Error de sintaxis:")
        print(f"   Línea {e.lineno}: {e.text}")
        print(f"   Error: {e.msg}")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_syntax()
