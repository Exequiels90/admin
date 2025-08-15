#!/usr/bin/env python3
"""
Configuración específica para Render gratuito
Maneja auto-sleep y falta de persistencia de datos
"""

import os
import sqlite3
from datetime import datetime

class RenderFreeConfig:
    """Configuración optimizada para Render gratuito"""
    
    @staticmethod
    def init_database_on_startup():
        """Inicializa la base de datos cada vez que la app arranca"""
        print("🔄 Render Gratuito: Inicializando base de datos...")
        
        # Crear directorio db si no existe
        os.makedirs("db", exist_ok=True)
        
        # Verificar si la base de datos existe y tiene datos
        db_path = "db/productos.db"
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Verificar si hay datos
                count = cursor.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
                conn.close()
                
                if count > 0:
                    print("✅ Base de datos existente con datos encontrada")
                    return True
                else:
                    print("⚠️ Base de datos vacía, reinicializando...")
            except:
                print("⚠️ Error en base de datos existente, reinicializando...")
        
        # Reinicializar base de datos
        try:
            from setup_database import main
            main()
            print("✅ Base de datos inicializada correctamente")
            return True
        except Exception as e:
            print(f"❌ Error al inicializar base de datos: {e}")
            return False
    
    @staticmethod
    def get_welcome_message():
        """Mensaje de bienvenida para usuarios de Render gratuito"""
        return {
            "title": "🚀 Sistema en Render Gratuito",
            "message": """
            <div class="alert alert-info">
                <h5><i class="fas fa-info-circle"></i> Información importante:</h5>
                <ul class="mb-0">
                    <li><strong>Auto-sleep:</strong> La aplicación puede tardar 30-60 segundos en cargar la primera vez</li>
                    <li><strong>Datos:</strong> Los datos se reinician periódicamente (característica del plan gratuito)</li>
                    <li><strong>Credenciales:</strong> Usuario: <code>admin</code> | Contraseña: <code>admin123</code></li>
                </ul>
                <hr>
                <small class="text-muted">
                    Para uso profesional, considera el plan Starter ($7/mes) que incluye persistencia de datos.
                </small>
            </div>
            """
        }
    
    @staticmethod
    def add_health_check():
        """Endpoint de health check para Render"""
        from flask import Flask, jsonify
        from datetime import datetime
        
        def health_check():
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "Sistema de Administración",
                "plan": "Render Free"
            })
        
        return health_check

# Configuración para variables de entorno en Render gratuito
RENDER_FREE_ENV = {
    "FLASK_ENV": "production",
    "SECRET_KEY": "clave_secreta_super_segura_2025_render_free",
    "SESSION_COOKIE_SECURE": "false",  # Render gratuito no tiene HTTPS permanente
    "DATABASE_PATH": "db/productos.db"
}
