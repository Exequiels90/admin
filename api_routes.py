from flask import Blueprint, jsonify, request, current_app
from functools import wraps
import sqlite3
import json
from datetime import datetime
from utils.database import get_db_connection, execute_query, execute_update
from utils.security import log_security_event

api = Blueprint('api', __name__, url_prefix='/api')

def require_api_key(f):
    """Decorador para verificar API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != current_app.config.get('API_KEY', 'default_key'):
            log_security_event('INVALID_API_KEY', request.remote_addr)
            return jsonify({'error': 'API key inválida'}), 401
        return f(*args, **kwargs)
    return decorated_function

@api.route('/productos', methods=['GET'])
@require_api_key
def get_productos():
    """Obtiene lista de productos para el POS"""
    try:
        query = """
        SELECT 
            p.id_producto,
            p.codigo,
            p.nombre,
            m.nombre as marca,
            p.precio_venta,
            p.stock,
            p.es_pesable,
            p.unidad_medida,
            c.nombre as categoria_nombre
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria
        LEFT JOIN marcas m ON p.marca_id = m.id_marca
        WHERE p.activo = 1 AND p.eliminado = 0
        ORDER BY p.nombre
        """
        
        productos = execute_query(query)
        
        return jsonify({
            'success': True,
            'data': productos,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_security_event('API_ERROR', request.remote_addr, str(e))
        return jsonify({'error': 'Error interno del servidor'}), 500

@api.route('/productos/<codigo>', methods=['GET'])
@require_api_key
def get_producto_by_code(codigo):
    """Obtiene un producto específico por código"""
    try:
        query = """
        SELECT 
            p.id_producto,
            p.codigo,
            p.nombre,
            m.nombre as marca,
            p.precio_venta,
            p.stock,
            p.es_pesable,
            p.unidad_medida,
            c.nombre as categoria_nombre
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id_categoria
        LEFT JOIN marcas m ON p.marca_id = m.id_marca
        WHERE p.codigo = ? AND p.activo = 1 AND p.eliminado = 0
        """
        
        productos = execute_query(query, (codigo,))
        
        if not productos:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        return jsonify({
            'success': True,
            'data': productos[0],
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_security_event('API_ERROR', request.remote_addr, str(e))
        return jsonify({'error': 'Error interno del servidor'}), 500

@api.route('/categorias', methods=['GET'])
@require_api_key
def get_categorias():
    """Obtiene lista de categorías"""
    try:
        query = "SELECT id_categoria, nombre, es_pesable FROM categorias ORDER BY nombre"
        categorias = execute_query(query)
        
        return jsonify({
            'success': True,
            'data': categorias,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_security_event('API_ERROR', request.remote_addr, str(e))
        return jsonify({'error': 'Error interno del servidor'}), 500

@api.route('/clientes', methods=['GET'])
@require_api_key
def get_clientes():
    """Obtiene lista de clientes"""
    try:
        query = """
        SELECT id_cliente, nombre, telefono, email, direccion 
        FROM clientes 
        ORDER BY nombre
        """
        clientes = execute_query(query)
        
        return jsonify({
            'success': True,
            'data': clientes,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_security_event('API_ERROR', request.remote_addr, str(e))
        return jsonify({'error': 'Error interno del servidor'}), 500

@api.route('/ventas', methods=['POST'])
@require_api_key
def recibir_venta():
    """Recibe una venta del POS"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
        
        # Validar datos mínimos
        required_fields = ['fecha_venta', 'productos', 'total_venta']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo requerido: {field}'}), 400
        
        # Insertar venta
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Insertar venta principal
            cursor.execute("""
                INSERT INTO ventas (id_cliente, fecha_venta, total_venta, metodo_pago, origen_venta)
                VALUES (?, ?, ?, ?, ?)
            """, (
                data.get('id_cliente'),
                data['fecha_venta'],
                data['total_venta'],
                data.get('metodo_pago', 'Efectivo'),
                'pos'
            ))
            
            id_venta = cursor.lastrowid
            
            # Insertar detalles de venta
            for producto in data['productos']:
                cursor.execute("""
                    INSERT INTO ventas_detalles (id_venta, id_producto, cantidad, precio_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    id_venta,
                    producto['id_producto'],
                    producto['cantidad'],
                    producto['precio_unitario'],
                    producto['subtotal']
                ))
            
            conn.commit()
        
        log_security_event('VENTA_RECIBIDA', request.remote_addr, f"Venta ID: {id_venta}")
        
        return jsonify({
            'success': True,
            'message': 'Venta registrada correctamente',
            'id_venta': id_venta,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_security_event('API_ERROR', request.remote_addr, str(e))
        return jsonify({'error': 'Error interno del servidor'}), 500

@api.route('/sync/status', methods=['GET'])
@require_api_key
def sync_status():
    """Obtiene estado de sincronización"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener estadísticas básicas
            cursor.execute("SELECT COUNT(*) FROM productos WHERE activo = 1 AND eliminado = 0")
            total_productos = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ventas WHERE origen_venta = 'pos'")
            ventas_pos = cursor.fetchone()[0]
            
            cursor.execute("SELECT MAX(fecha_registro) FROM ventas WHERE origen_venta = 'pos'")
            ultima_venta = cursor.fetchone()[0]
        
        return jsonify({
            'success': True,
            'data': {
                'total_productos': total_productos,
                'ventas_pos': ventas_pos,
                'ultima_venta': ultima_venta,
                'servidor_activo': True
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_security_event('API_ERROR', request.remote_addr, str(e))
        return jsonify({'error': 'Error interno del servidor'}), 500

@api.route('/productos/stock', methods=['POST'])
@require_api_key
def actualizar_stock():
    """Actualiza stock de productos (para sincronización)"""
    try:
        data = request.get_json()
        
        if not data or 'productos' not in data:
            return jsonify({'error': 'Datos requeridos'}), 400
        
        actualizados = 0
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for producto in data['productos']:
                if 'id_producto' in producto and 'stock' in producto:
                    cursor.execute("""
                        UPDATE productos 
                        SET stock = ? 
                        WHERE id_producto = ? AND activo = 1 AND eliminado = 0
                    """, (producto['stock'], producto['id_producto']))
                    actualizados += cursor.rowcount
            
            conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{actualizados} productos actualizados',
            'actualizados': actualizados,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_security_event('API_ERROR', request.remote_addr, str(e))
        return jsonify({'error': 'Error interno del servidor'}), 500

@api.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint no encontrado'}), 404

@api.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Error interno del servidor'}), 500
