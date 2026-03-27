import json
import os
from flask import Flask, render_template

# ==================================
# Configuración Aplicación
# ==================================

# Crear la app de Flask
app = Flask(__name__)

# ==================================
# Manejo de Rutas
# ==================================

# Ruta principal
@app.route('/')
def inicio():
    return render_template('inicio.html')

# Ruta pruebas
# RUTA QUE SERÁ ELIMINADA O MODIFICADA EN EL FUTURO
# PUEDE SERVIR DE CARA A LA MUESTRA DE DATOS, DE FORMA EXPERIMENTAL
@app.route('/preview/pruebas')
def preview_pruebas():
    # Construir la ruta al archivo JSON
    ruta_json = os.path.join(app.root_path, 'data', 'dataset_prueba2.json')

    with open(ruta_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extraemos edificios y aulas
    edificios = data.get('buildings', [])
    aulas = data.get('rooms', [])

    # Extraemos datos de profesores
    profesores = data.get('teachers', [])
    # Obtenemos ramas únicas para las columnas (Informática, Empresa, General)
    ramas = sorted(list(set(p['branch'] for p in profesores)))

    # Extraemos datos de grados y asignaturas
    grados = data.get('grades', [])
    asignaturas = data.get('courses', [])

    return render_template('preview_pruebas.html', 
                           edificios=edificios, aulas=aulas,
                           profesores=profesores, ramas=ramas,
                           grados=grados, asignaturas=asignaturas)

# ==================================
# Ejecución APP
# ==================================

# Ejecutar la app
if __name__ == '__main__':
    # debug=True recarga automáticamente al guardar cambios
    app.run(debug=True)