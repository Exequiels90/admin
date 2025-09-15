#!/usr/bin/env python3
"""Script para probar la sincronización de ventas"""

import requests
import json

def test_sync():
    """Probar el endpoint de sincronización"""
    
    # Datos de prueba
    test_data = {
        'ventas': [{
            'id_venta': 999,
            'fecha_venta': '2025-09-12 22:06:12',
            'total': 1500.0,
            'id_usuario': 1,
            'efectivo': 1500.0,
            'transferencia': 0.0,
            'credito': 0.0,
            'prestamo_personal': 0.0,
            'cliente_id': 1,
            'items': [{
                'id_producto': 1,
                'cantidad': 1.0,
                'precio_unitario': 1500.0
            }]
        }]
    }
    
    try:
        print("🔍 Probando endpoint de sincronización...")
        print(f"📤 Enviando datos: {json.dumps(test_data, indent=2)}")
        
        # Probar con la URL correcta
        response = requests.post('http://localhost:5000/api/ventas/batch', 
                               json=test_data, 
                               headers={'Content-Type': 'application/json'})
        
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Sincronización exitosa!")
        else:
            print("❌ Error en la sincronización")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_sync()

