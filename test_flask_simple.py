#!/usr/bin/env python3
"""
Script simple para probar Flask
"""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/test')
def test():
    return 'Test OK!'

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask simple...")
    app.run(debug=True, port=5001)
