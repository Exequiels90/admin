import bcrypt
import re
from functools import wraps
from flask import request, jsonify, session
import logging

logger = logging.getLogger(__name__)

def hash_password(password):
    """Genera un hash bcrypt de la contraseña"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def verify_password(password, hashed):
    """Verifica una contraseña contra su hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def validate_password_strength(password):
    """Valida la fortaleza de una contraseña"""
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    if not re.search(r"[A-Z]", password):
        return False, "La contraseña debe contener al menos una mayúscula"
    
    if not re.search(r"[a-z]", password):
        return False, "La contraseña debe contener al menos una minúscula"
    
    if not re.search(r"\d", password):
        return False, "La contraseña debe contener al menos un número"
    
    return True, "Contraseña válida"

def sanitize_input(text):
    """Sanitiza entrada de texto para prevenir XSS"""
    if not text:
        return ""
    
    # Remover caracteres peligrosos
    dangerous_chars = ['<', '>', '"', "'", '&']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text.strip()

def validate_email(email):
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def rate_limit(max_requests=100, window=3600):
    """Decorador para limitar rate de requests"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Implementación básica de rate limiting
            # En producción usar Redis o similar
            client_ip = request.remote_addr
            # Aquí iría la lógica de rate limiting
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_roles(*roles):
    """Decorador para requerir roles específicos"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'rol' not in session:
                return jsonify({'error': 'No autorizado'}), 401
            
            if session['rol'] not in roles:
                return jsonify({'error': 'Acceso denegado'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_security_event(event_type, user_id=None, details=None):
    """Registra eventos de seguridad"""
    logger.warning(f"SECURITY_EVENT: {event_type} | User: {user_id} | Details: {details}")

def validate_product_data(data):
    """Valida datos de producto"""
    errors = []
    
    if not data.get('nombre'):
        errors.append("El nombre del producto es requerido")
    
    if not data.get('codigo'):
        errors.append("El código del producto es requerido")
    
    precio_compra = data.get('precio_compra', 0)
    precio_venta = data.get('precio_venta', 0)
    
    try:
        precio_compra = float(precio_compra)
        precio_venta = float(precio_venta)
    except ValueError:
        errors.append("Los precios deben ser números válidos")
    
    if precio_compra < 0 or precio_venta < 0:
        errors.append("Los precios no pueden ser negativos")
    
    if precio_venta < precio_compra:
        errors.append("El precio de venta no puede ser menor al de compra")
    
    return errors

def validate_sale_data(data):
    """Valida datos de venta"""
    errors = []
    
    if not data.get('fecha_venta'):
        errors.append("La fecha de venta es requerida")
    
    if not data.get('productos') or len(data['productos']) == 0:
        errors.append("Debe incluir al menos un producto")
    
    return errors
