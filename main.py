import json
import os
from flask import Flask, render_template, Response
from utils.algoritmos import generar_horario_iterativo

app = Flask(__name__)

# ---------------------------------------------------------
# RUTAS DE NAVEGACIÓN
# ---------------------------------------------------------

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

# Ruta de datos de profesores
@app.route('/profesores')
def lista_profesores():
    data = cargar_datos()
    profesores = data.get('teachers', [])
    return render_template('profesores.html', profesores=profesores)

# Ruta de datos de aulas
@app.route('/aulas')
def lista_aulas():
    data = cargar_datos()
    edificios = data.get('buildings', [])
    aulas = data.get('rooms', [])
    return render_template('aulas.html', edificios=edificios, aulas=aulas)

# Ruta de datos de grados y asignaturas por cuatrimestre
@app.route('/grados')
def lista_grados():
    data = cargar_datos()
    grados = data.get('grades', [])
    asignaturas = data.get('courses', [])
    return render_template('grados.html', grados=grados, asignaturas=asignaturas)

# Esta ruta solo carga la página HTML con el contador y el botón
@app.route('/solver/stream')
def vista_stream():
    return render_template('resultado.html')

# Esta es la ruta que REALMENTE ejecuta el algoritmo y envía datos
@app.route('/solver/progress')
def solver_progress():
    ruta_json = os.path.join(app.root_path, 'data', 'dataset_prueba2.json')
    
    if not os.path.exists(ruta_json):
        return "Error: No se encontró el dataset", 404

    def generate():
        with open(ruta_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Ejecutamos el generador del algoritmo
        for progreso, horario in generar_horario_iterativo(data, term="Q1"):
            # Enviamos cada paso del 1 al 20 al navegador
            yield f"data: {json.dumps({'progreso': progreso, 'horario': horario})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

# ---------------------------------------------------------
# FUNCIONES
# ---------------------------------------------------------

def cargar_datos(): # Función general de carga de datos para evitar repetición en cada caso individual
    ruta_json = os.path.join(app.root_path, 'data', 'dataset_prueba2.json')
    with open(ruta_json, 'r', encoding='utf-8') as f:
        return json.load(f)

# ---------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------

if __name__ == '__main__':
    # Debug=True para que el servidor se reinicie al guardar cambios
    app.run(debug=True, port=5000)