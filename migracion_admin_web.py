#!/usr/bin/env python3
"""
Script de migración para unificar esquema del Admin Web
Agrega campos faltantes para compatibilidad con POS Cliente
"""

import sqlite3
import os
import sys
from datetime import datetime

def backup_database(db_path):
    """Crear backup de la base de datos antes de migrar"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup creado: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Error creando backup: {e}")
        return False

def migrate_admin_database():
    """Migrar base de datos del Admin Web"""
    db_path = "db/productos.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Base de datos no encontrada: {db_path}")
        return False
    
    print("🔄 Iniciando migración del Admin Web...")
    
    # Crear backup
    if not backup_database(db_path):
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📊 Analizando estructura actual...")
        
        # Obtener información de las tablas existentes
        cursor.execute("PRAGMA table_info(productos)")
        productos_columns = [col[1] for col in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(ventas)")
        ventas_columns = [col[1] for col in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(usuarios)")
        usuarios_columns = [col[1] for col in cursor.fetchall()]
        
        print(f"Columnas actuales en productos: {productos_columns}")
        print(f"Columnas actuales en ventas: {ventas_columns}")
        print(f"Columnas actuales en usuarios: {usuarios_columns}")
        
        # MIGRACIÓN DE PRODUCTOS
        print("\n🔄 Migrando tabla productos...")
        
        campos_productos = [
            ("venta_por_peso", "INTEGER DEFAULT 0"),
            ("ultima_sincronizacion", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("created_by", "INTEGER"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("updated_by", "INTEGER"),
            ("updated_at", "TIMESTAMP"),
            ("deleted_by", "INTEGER"),
            ("deleted_at", "TIMESTAMP"),
            ("version_sincronizacion", "INTEGER DEFAULT 1")
        ]
        
        for campo, tipo in campos_productos:
            if campo not in productos_columns:
                try:
                    cursor.execute(f"ALTER TABLE productos ADD COLUMN {campo} {tipo}")
                    print(f"  ✅ Agregado: {campo}")
                except Exception as e:
                    print(f"  ⚠️  Campo {campo} ya existe o error: {e}")
        
        # MIGRACIÓN DE VENTAS
        print("\n🔄 Migrando tabla ventas...")
        
        campos_ventas = [
            ("efectivo", "REAL DEFAULT 0"),
            ("transferencia", "REAL DEFAULT 0"),
            ("credito", "REAL DEFAULT 0"),
            ("prestamo_personal", "REAL DEFAULT 0"),
            ("usuario_id", "INTEGER"),
            ("estado", "TEXT DEFAULT 'completada'"),
            ("sincronizado", "INTEGER DEFAULT 0"),
            ("created_by", "INTEGER"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("updated_by", "INTEGER"),
            ("updated_at", "TIMESTAMP"),
            ("deleted_by", "INTEGER"),
            ("deleted_at", "TIMESTAMP"),
            ("version_sincronizacion", "INTEGER DEFAULT 1")
        ]
        
        for campo, tipo in campos_ventas:
            if campo not in ventas_columns:
                try:
                    cursor.execute(f"ALTER TABLE ventas ADD COLUMN {campo} {tipo}")
                    print(f"  ✅ Agregado: {campo}")
                except Exception as e:
                    print(f"  ⚠️  Campo {campo} ya existe o error: {e}")
        
        # MIGRACIÓN DE USUARIOS
        print("\n🔄 Migrando tabla usuarios...")
        
        campos_usuarios = [
            ("created_by", "INTEGER"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("updated_by", "INTEGER"),
            ("updated_at", "TIMESTAMP"),
            ("deleted_by", "INTEGER"),
            ("deleted_at", "TIMESTAMP"),
            ("intentos_fallidos", "INTEGER DEFAULT 0")
        ]
        
        for campo, tipo in campos_usuarios:
            if campo not in usuarios_columns:
                try:
                    cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {campo} {tipo}")
                    print(f"  ✅ Agregado: {campo}")
                except Exception as e:
                    print(f"  ⚠️  Campo {campo} ya existe o error: {e}")
        
        # CREAR TABLA DE AUDITORÍA MEJORADA
        print("\n🔄 Creando tabla de auditoría mejorada...")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS auditoria_completa (
            id_auditoria INTEGER PRIMARY KEY AUTOINCREMENT,
            tabla_afectada TEXT NOT NULL,
            id_registro INTEGER NOT NULL,
            accion TEXT NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE'
            datos_anteriores TEXT, -- JSON
            datos_nuevos TEXT, -- JSON
            usuario_id INTEGER,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            detalles TEXT,
            sincronizado INTEGER DEFAULT 0
        )
        """)
        
        # Crear índices para auditoría
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_tabla ON auditoria_completa (tabla_afectada)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON auditoria_completa (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_usuario ON auditoria_completa (usuario_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_sincronizado ON auditoria_completa (sincronizado)")
        
        # CREAR TABLA DE SINCRONIZACIÓN
        print("\n🔄 Creando tabla de sincronización...")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sincronizacion_log (
            id_log INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_sincronizacion TEXT NOT NULL, -- 'productos', 'ventas', 'auditoria'
            direccion TEXT NOT NULL, -- 'enviado', 'recibido'
            registros_procesados INTEGER DEFAULT 0,
            registros_exitosos INTEGER DEFAULT 0,
            registros_fallidos INTEGER DEFAULT 0,
            fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_fin TIMESTAMP,
            estado TEXT DEFAULT 'en_proceso', -- 'en_proceso', 'completado', 'error'
            error_mensaje TEXT,
            usuario_id INTEGER
        )
        """)
        
        # Crear índices para sincronización
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_tipo ON sincronizacion_log (tipo_sincronizacion)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_fecha ON sincronizacion_log (fecha_inicio)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_estado ON sincronizacion_log (estado)")
        
        # CREAR TABLA DE CLIENTES POS MEJORADA
        print("\n🔄 Mejorando tabla de clientes POS...")
        
        campos_clientes_pos = [
            ("ultima_sincronizacion_productos", "TIMESTAMP"),
            ("ultima_sincronizacion_ventas", "TIMESTAMP"),
            ("ultima_sincronizacion_auditoria", "TIMESTAMP"),
            ("version_productos", "INTEGER DEFAULT 1"),
            ("version_ventas", "INTEGER DEFAULT 1"),
            ("version_auditoria", "INTEGER DEFAULT 1"),
            ("configuracion_sync", "TEXT"),  # JSON con configuración
            ("created_by", "INTEGER"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("updated_by", "INTEGER"),
            ("updated_at", "TIMESTAMP")
        ]
        
        cursor.execute("PRAGMA table_info(clientes_pos)")
        clientes_pos_columns = [col[1] for col in cursor.fetchall()]
        
        for campo, tipo in campos_clientes_pos:
            if campo not in clientes_pos_columns:
                try:
                    cursor.execute(f"ALTER TABLE clientes_pos ADD COLUMN {campo} {tipo}")
                    print(f"  ✅ Agregado: {campo}")
                except Exception as e:
                    print(f"  ⚠️  Campo {campo} ya existe o error: {e}")
        
        # Actualizar datos existentes
        print("\n🔄 Actualizando datos existentes...")
        
        # Verificar si existen las columnas antes de actualizar
        cursor.execute("PRAGMA table_info(productos)")
        productos_columns = [col[1] for col in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(ventas)")
        ventas_columns = [col[1] for col in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(usuarios)")
        usuarios_columns = [col[1] for col in cursor.fetchall()]
        
        # Actualizar created_at en productos existentes
        if 'created_at' in productos_columns:
            cursor.execute("""
            UPDATE productos 
            SET created_at = COALESCE(created_at, fecha_creacion)
            WHERE created_at IS NULL
            """)
            print("  ✅ Actualizada created_at en productos")
        
        # Actualizar created_at en ventas existentes
        if 'created_at' in ventas_columns:
            cursor.execute("""
            UPDATE ventas 
            SET created_at = COALESCE(created_at, fecha_registro)
            WHERE created_at IS NULL
            """)
            print("  ✅ Actualizada created_at en ventas")
        
        # Actualizar created_at en usuarios existentes
        if 'created_at' in usuarios_columns:
            cursor.execute("""
            UPDATE usuarios 
            SET created_at = COALESCE(created_at, fecha_creacion)
            WHERE created_at IS NULL
            """)
            print("  ✅ Actualizada created_at en usuarios")
        
        conn.commit()
        print("✅ Migración completada exitosamente!")
        
        # Mostrar resumen
        print("\n📊 RESUMEN DE MIGRACIÓN:")
        cursor.execute("PRAGMA table_info(productos)")
        productos_final = [col[1] for col in cursor.fetchall()]
        print(f"Productos: {len(productos_final)} columnas")
        
        cursor.execute("PRAGMA table_info(ventas)")
        ventas_final = [col[1] for col in cursor.fetchall()]
        print(f"Ventas: {len(ventas_final)} columnas")
        
        cursor.execute("PRAGMA table_info(usuarios)")
        usuarios_final = [col[1] for col in cursor.fetchall()]
        print(f"Usuarios: {len(usuarios_final)} columnas")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("🚀 MIGRACIÓN ADMIN WEB - UNIFICACIÓN DE ESQUEMAS")
    print("=" * 50)
    
    success = migrate_admin_database()
    
    if success:
        print("\n🎉 ¡Migración completada exitosamente!")
        print("El Admin Web ahora tiene esquema unificado con el POS Cliente")
    else:
        print("\n💥 Error en la migración")
        sys.exit(1)
