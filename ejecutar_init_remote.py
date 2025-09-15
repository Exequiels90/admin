#!/usr/bin/env python3
"""
Script para ejecutar la inicialización remota
"""

import requests
import time

def main():
    print("🔧 Ejecutando inicialización remota...")
    
    # Esperar un momento para que PythonAnywhere actualice
    print("⏳ Esperando actualización de PythonAnywhere...")
    time.sleep(10)
    
    try:
        print("📤 Ejecutando inicialización...")
        response = requests.post(
            'https://chimuelo1290.pythonanywhere.com/api/init_db',
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Inicialización exitosa")
            else:
                print(f"❌ Error: {result.get('error')}")
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()




