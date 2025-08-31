import os

class Config:
    """Configuración base"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or os.path.join("db", "admin_database.db")
    
    # Configuración de sesiones
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora por defecto
    
    # Configuración de seguridad
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # Configuración de logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'app.log'
    
    # Configuración de rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Configuración para productos pesables
    UNIDADES_MEDIDA = [
        ('unidad', 'Unidad'),
        ('kg', 'Kilogramo'),
        ('g', 'Gramo'),
        ('l', 'Litro'),
        ('ml', 'Mililitro'),
        ('m', 'Metro'),
        ('cm', 'Centímetro'),
        ('lb', 'Libra'),
        ('oz', 'Onza')
    ]
    
    # Configuración de sincronización
    SYNC_INTERVAL = 300  # 5 minutos
    SYNC_TIMEOUT = 10  # 10 segundos
    
    # Configuración de moneda
    CURRENCY = {
        'symbol': '$',
        'name': 'Pesos Argentinos',
        'code': 'ARS',
        'decimal_places': 2,
        'thousands_separator': ',',
        'decimal_separator': '.'
    }
    
    # Configuración de colores
    COLORS = {
        'primary': '#343a40',
        'secondary': '#495057',
        'success': '#28a745',
        'danger': '#dc3545',
        'warning': '#ffc107',
        'info': '#17a2b8',
        'light': '#f8f9fa',
        'dark': '#343a40',
        'white': '#ffffff'
    }

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = 'DEBUG'
    
    # Configuración de sincronización para desarrollo
    SYNC_INTERVAL = 60  # 1 minuto en desarrollo

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    # Configuraciones adicionales de seguridad para producción
    SESSION_COOKIE_SAMESITE = 'Strict'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora
    
    # Configuración de headers de seguridad
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
    }

# Configuración por defecto
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
