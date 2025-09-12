#!/usr/bin/env python3
"""
Script para probar todas las importaciones del app.py
"""

def test_imports():
    """Prueba todas las importaciones"""
    
    imports = [
        "flask",
        "sqlite3", 
        "os",
        "random",
        "json",
        "hashlib",
        "datetime",
        "reportlab.pdfgen",
        "reportlab.lib.pagesizes",
        "reportlab.lib.units",
        "reportlab.pdfbase",
        "reportlab.pdfbase.ttfonts",
        "reportlab.graphics.barcode",
        "reportlab.graphics.shapes",
        "io",
        "barcode",
        "barcode.writer",
        "functools",
        "requests"
    ]
    
    print("🔍 Probando importaciones...")
    
    for module in imports:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
        except Exception as e:
            print(f"⚠️ {module}: {e}")

if __name__ == "__main__":
    test_imports()
