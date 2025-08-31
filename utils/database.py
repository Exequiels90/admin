import sqlite3
import logging
from contextlib import contextmanager
from flask import current_app
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """Context manager para conexiones a la base de datos"""
    conn = None
    try:
        conn = sqlite3.connect(current_app.config['DATABASE_PATH'])
        conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        logger.error(f"Error en conexión a BD: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Ejecuta una consulta SELECT y retorna los resultados"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error ejecutando query: {e}")
        raise

def execute_update(query: str, params: tuple = ()) -> int:
    """Ejecuta una consulta UPDATE/INSERT/DELETE y retorna filas afectadas"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        logger.error(f"Error ejecutando update: {e}")
        raise

def get_product_by_code(codigo: str) -> Optional[Dict[str, Any]]:
    """Obtiene un producto por código"""
    query = """
    SELECT p.*, c.nombre as categoria_nombre 
    FROM productos p 
    LEFT JOIN categorias c ON p.categoria_id = c.id_categoria 
    WHERE p.codigo = ? AND p.activo = 1 AND p.eliminado = 0
    """
    results = execute_query(query, (codigo,))
    return results[0] if results else None

def get_products_by_category(categoria_id: int) -> List[Dict[str, Any]]:
    """Obtiene productos por categoría"""
    query = """
    SELECT p.*, c.nombre as categoria_nombre 
    FROM productos p 
    LEFT JOIN categorias c ON p.categoria_id = c.id_categoria 
    WHERE p.categoria_id = ? AND p.activo = 1 AND p.eliminado = 0
    ORDER BY p.nombre
    """
    return execute_query(query, (categoria_id,))

def get_products_low_stock(threshold: int = 10) -> List[Dict[str, Any]]:
    """Obtiene productos con stock bajo"""
    query = """
    SELECT p.*, c.nombre as categoria_nombre 
    FROM productos p 
    LEFT JOIN categorias c ON p.categoria_id = c.id_categoria 
    WHERE p.stock <= ? AND p.activo = 1 AND p.eliminado = 0
    ORDER BY p.stock ASC
    """
    return execute_query(query, (threshold,))

def update_product_stock(producto_id: int, cantidad: float, operation: str = 'add') -> bool:
    """Actualiza el stock de un producto"""
    try:
        if operation == 'add':
            query = "UPDATE productos SET stock = stock + ? WHERE id_producto = ?"
        elif operation == 'subtract':
            query = "UPDATE productos SET stock = stock - ? WHERE id_producto = ?"
        else:
            raise ValueError("Operación debe ser 'add' o 'subtract'")
        
        execute_update(query, (cantidad, producto_id))
        return True
    except Exception as e:
        logger.error(f"Error actualizando stock: {e}")
        return False

def get_sales_summary(fecha_inicio: str, fecha_fin: str) -> Dict[str, Any]:
    """Obtiene resumen de ventas por período"""
    query = """
    SELECT 
        COUNT(*) as total_ventas,
        SUM(total_venta) as total_ingresos,
        AVG(total_venta) as promedio_venta,
        COUNT(DISTINCT id_cliente) as clientes_unicos
    FROM ventas 
    WHERE fecha_venta BETWEEN ? AND ? AND eliminado = 0
    """
    results = execute_query(query, (fecha_inicio, fecha_fin))
    return results[0] if results else {}

def get_top_products(limit: int = 10) -> List[Dict[str, Any]]:
    """Obtiene los productos más vendidos"""
    query = """
    SELECT 
        p.nombre,
        p.codigo,
        SUM(vd.cantidad) as total_vendido,
        SUM(vd.subtotal) as total_ingresos
    FROM ventas_detalles vd
    JOIN productos p ON vd.id_producto = p.id_producto
    JOIN ventas v ON vd.id_venta = v.id_venta
    WHERE v.eliminado = 0
    GROUP BY p.id_producto
    ORDER BY total_vendido DESC
    LIMIT ?
    """
    return execute_query(query, (limit,))

def get_category_sales(fecha_inicio: str, fecha_fin: str) -> List[Dict[str, Any]]:
    """Obtiene ventas por categoría"""
    query = """
    SELECT 
        c.nombre as categoria,
        COUNT(DISTINCT v.id_venta) as ventas,
        SUM(vd.cantidad) as unidades_vendidas,
        SUM(vd.subtotal) as ingresos
    FROM ventas_detalles vd
    JOIN productos p ON vd.id_producto = p.id_producto
    JOIN categorias c ON p.categoria_id = c.id_categoria
    JOIN ventas v ON vd.id_venta = v.id_venta
    WHERE v.fecha_venta BETWEEN ? AND ? AND v.eliminado = 0
    GROUP BY c.id_categoria
    ORDER BY ingresos DESC
    """
    return execute_query(query, (fecha_inicio, fecha_fin))

def backup_database() -> bool:
    """Crea un backup de la base de datos"""
    try:
        import shutil
        from datetime import datetime
        
        source_path = current_app.config['DATABASE_PATH']
        backup_path = f"backups/db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        # Crear directorio de backups si no existe
        import os
        os.makedirs("backups", exist_ok=True)
        
        shutil.copy2(source_path, backup_path)
        logger.info(f"Backup creado: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Error creando backup: {e}")
        return False

def get_database_stats() -> Dict[str, Any]:
    """Obtiene estadísticas de la base de datos"""
    stats = {}
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Contar registros en cada tabla
            tables = ['productos', 'categorias', 'clientes', 'ventas', 'lotes', 'proveedores']
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats[f'total_{table}'] = count
            
            # Productos activos
            cursor.execute("SELECT COUNT(*) FROM productos WHERE activo = 1 AND eliminado = 0")
            stats['productos_activos'] = cursor.fetchone()[0]
            
            # Stock total
            cursor.execute("SELECT SUM(stock) FROM productos WHERE activo = 1 AND eliminado = 0")
            stats['stock_total'] = cursor.fetchone()[0] or 0
            
            # Valor del inventario
            cursor.execute("""
                SELECT SUM(stock * precio_venta) 
                FROM productos 
                WHERE activo = 1 AND eliminado = 0
            """)
            stats['valor_inventario'] = cursor.fetchone()[0] or 0
            
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
    
    return stats
