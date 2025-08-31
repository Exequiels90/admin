#!/usr/bin/env python3
"""
Script para mantener el servidor Flask corriendo de forma estable
"""

import subprocess
import sys
import os
import time

def run_server():
    print("🚀 Iniciando servidor Flask...")
    print("📍 URL: http://127.0.0.1:5000")
    print("🔑 Usuario: admin")
    print("🔑 Contraseña: admin123")
    print("=" * 50)
    
    try:
        # Ejecutar el servidor Flask
        process = subprocess.Popen([sys.executable, "app.py"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        
        print(f"✅ Servidor iniciado con PID: {process.pid}")
        print("⏳ Manteniendo el servidor corriendo...")
        print("📝 Presiona Ctrl+C para detener")
        
        # Mantener el proceso vivo
        while True:
            if process.poll() is not None:
                print("❌ El servidor se detuvo inesperadamente")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor...")
        if 'process' in locals():
            process.terminate()
            process.wait()
        print("✅ Servidor detenido")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_server()


