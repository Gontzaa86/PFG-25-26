import json
import os
from flask import Flask, render_template, Response, request, jsonify
from utils.algoritmos import generar_horario_iterativo
from utils.restricciones import RESTRICCIONES_DISPONIBLES

app = Flask(__name__)

# ---------------------------------------------------------
# RUTAS DE NAVEGACIÓN
# ---------------------------------------------------------

@app.route('/')
def inicio():
    return render_template('inicio.html')

# Ruta de datos de profesores
@app.route('/profesores')
def lista_profesores():
    data = cargar_datos()
    profesores = data.get('teachers', [])
    asignaturas = data.get('courses', []) # Recopilación de asignaturas para visualización de asignaturas impartidas por cada profesor.

    # Añadir un indicador de si el profesor tiene asignaturas asignadas
    for profesor in profesores:
        profesor_id = str(profesor.get('id', ''))
        profesor['has_courses'] = any(
            str(curso.get('teacher', '')) == profesor_id
            for curso in asignaturas
        )

    # Agrupación por rama a los profesores
    ramas = sorted(list(set(p['branch'] for p in profesores)))

    return render_template('profesores.html', profesores=profesores, asignaturas=asignaturas, ramas=ramas)

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
    profesores = {p['id']: p['name'] for p in data.get('teachers', [])}

    return render_template('grados.html', grados=grados, asignaturas=asignaturas, profesores=profesores)

# Esta ruta solo carga la página HTML con el contador y el botón
@app.route('/solver/stream')
def vista_stream():
    return render_template('resultado.html')

# Esta es la ruta que REALMENTE ejecuta el algoritmo y envía datos
@app.route('/solver/progress')
def solver_progress():
    # Obtener el term de la URL, por defecto Q1 si no viene nada
    term_usuario = request.args.get('term', 'Q1')

    # Obtener lista de restricciones (ej: ?res=minimizar_ventanas&res=evitar_clase_unica)
    restricciones_usuario = request.args.getlist('res')

    ruta_json = os.path.join(app.root_path, 'data', 'dataset_prueba2.json')
    
    if not os.path.exists(ruta_json):
        return "Error: No se encontró el dataset", 404

    def generate():
        with open(ruta_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Ejecutamos el generador del algoritmo
        for progreso, resultado in generar_horario_iterativo(data, term=term_usuario, restricciones=restricciones_usuario):
            # Enviamos cada paso del 1 al 20 al navegador
            payload = {
                'progreso': progreso,
                'horario': resultado['horario'],
                'logs': resultado['logs']
            }
            yield f"data: {json.dumps(payload)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

# ---------------------------------------------------------
# RUTAS API
# ---------------------------------------------------------

# ==== Rutas de profesores ====
@app.route('/api/profesores', methods=['POST'])
def gestionar_profesor():
    data = cargar_datos()
    nuevo = request.json

    # Si tiene ID es una edición, si no una agregación/creación
    if not nuevo.get('id'):
        rama = nuevo['branch'].upper()
        prefijo = rama[:3] # 3 primeras letras como prefijo

        profesores_rama = [p for p in data['teachers'] if p['id'].startswith(f"T_{prefijo}_")]

        max_num = 0
        for p in profesores_rama:
            try:
                num_parte = int(p['id'].split('_')[-1])
                if num_parte > max_num:
                    max_num = num_parte
            except (ValueError, IndexError):
                continue
        
        nuevo['id'] = f"T_{prefijo}_{str(max_num + 1).zfill(2)}"
        data['teachers'].append(nuevo)
    else:
        for i, p in enumerate(data['teachers']):
            if p['id'] == nuevo['id']:
                data['teachers'][i]['name'] = nuevo['name']
                data['teachers'][i]['branch'] = nuevo['branch']
                break

    guardar_datos(data)
    return jsonify({"success": True, "id": nuevo['id']})

@app.route('/api/profesores/<id>', methods=['DELETE'])
def eliminar_profesor(id):
    data = cargar_datos()
    # Filtrar para eliminar
    data['teachers'] = [p for p in data['teachers'] if p ['id'] != id]
    guardar_datos(data)
    return jsonify({"success": True})

# ==== Rutas de restricciones ====
@app.route('/api/config/restricciones')
def obtener_restricciones():
    # Enviamos solo los ID y los nombres legibles al frontend
    return jsonify({k: v['label'] for k, v in RESTRICCIONES_DISPONIBLES.items()})

# ---------------------------------------------------------
# FUNCIONES
# ---------------------------------------------------------

def cargar_datos(): # Función general de carga de datos para evitar repetición en cada caso individual
    ruta_json = os.path.join(app.root_path, 'data', 'dataset_prueba2.json')
    with open(ruta_json, 'r', encoding='utf-8') as f:
        return json.load(f)

def guardar_datos(data): # Modificación de datos en el JSON
    ruta_json = os.path.join(app.root_path, 'data', 'dataset_prueba2.json')
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------

if __name__ == '__main__':
    # Debug=True para que el servidor se reinicie al guardar cambios
    app.run(debug=True, port=5000)