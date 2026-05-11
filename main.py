import json
import os
import csv
import io
from flask import Flask, render_template, Response, request, jsonify
from utils.algoritmos import generar_horario_iterativo, evaluar_horario, optimizar_horario
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
    profesores_originales = data.get('teachers', [])
    asignaturas = data.get('courses', []) # Recopilación de asignaturas para visualización de asignaturas impartidas por cada profesor.

    # Expandir profesores por cada rama (si un profesor tiene múltiples ramas, aparecerá en cada una)
    profesores_expandidos = []
    for profesor in profesores_originales:
        ramas_profesor = profesor.get('branch', [])
        # Manejar tanto strings antiguos como arrays nuevos
        if isinstance(ramas_profesor, str):
            ramas_profesor = [ramas_profesor]
        
        for rama in ramas_profesor:
            prof_expandido = profesor.copy()
            prof_expandido['branch'] = rama  # Una sola rama para esta instancia
            profesores_expandidos.append(prof_expandido)

    # Añadir un indicador de si el profesor tiene asignaturas asignadas
    for profesor in profesores_expandidos:
        profesor_id = str(profesor.get('id', ''))
        profesor['has_courses'] = any(
            str(curso.get('teacher', '')) == profesor_id
            for curso in asignaturas
        )

    # Agrupación por rama a los profesores
    ramas = sorted(list(set(p['branch'] for p in profesores_expandidos)))

    return render_template('profesores.html', profesores=profesores_expandidos, asignaturas=asignaturas, ramas=ramas)

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
        
        pool_horarios = [] # Para almacenar los 20 intentos iniciales

        # Ejecutamos el generador del algoritmo
        for progreso, resultado in generar_horario_iterativo(data, term=term_usuario, restricciones=restricciones_usuario):
            if resultado['horario']:
                puntaje, logs = evaluar_horario(resultado['horario'], restricciones_usuario, data)
                pool_horarios.append({
                    "horario": resultado['horario'],
                    "puntuacion": puntaje,
                    "logs": logs
                })

            # Notificamos progreso al frontend
            yield f"data: {json.dumps({'progreso': progreso, 'fase': 'generando'})}\n\n"
        
        # Optimización de la "Élite" (Top 5)
        # Ordenamos por menor puntuación (penalización)
        pool_horarios.sort(key=lambda x: x['puntuacion'])
        top_5 = pool_horarios[:5]

        ganador_absoluto = None
        mejor_puntaje_global = float('inf')

        for i, candidato in enumerate(top_5):
            # Notificamos al usuario que estamos optimizando
            yield f"data: {json.dumps({'progreso': 20, 'fase': f'optimizando {i+1}/5'})}\n\n"

            h_opt, p_opt = optimizar_horario(candidato['horario'], restricciones_usuario, data)

            if p_opt < mejor_puntaje_global:
                mejor_puntaje_global = p_opt
                _, logs_finales = evaluar_horario(h_opt, restricciones_usuario, data)
                ganador_absoluto = {"horario": h_opt, "logs": logs_finales}
        
        # Resultado final
        payload = {
            'progreso': 20,
            'fase': 'finalizado',
            'horario': ganador_absoluto['horario'],
            'logs': ganador_absoluto['logs']
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
        # Manejo de branch como array
        ramas = nuevo.get('branch', [])
        if isinstance(ramas, str):
            ramas = [ramas]
        
        rama_principal = ramas[0].upper() if ramas else "DEF"
        prefijo = rama_principal[:3] # 3 primeras letras como prefijo

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
        nuevo['branch'] = ramas  # Guardar como array
        if 'unavailability' not in nuevo:
            nuevo['unavailability'] = {}
        data['teachers'].append(nuevo)
    else:
        for i, p in enumerate(data['teachers']):
            if p['id'] == nuevo['id']:
                data['teachers'][i]['name'] = nuevo['name']
                # Manejar branch como array
                ramas = nuevo.get('branch', [])
                if isinstance(ramas, str):
                    ramas = [ramas]
                data['teachers'][i]['branch'] = ramas
                break

    guardar_datos(data)
    return jsonify({"success": True, "id": nuevo['id']})

@app.route('/api/profesores/<id>', methods=['GET'])
def obtener_profesor(id):
    data = cargar_datos()
    profesor = next((p for p in data['teachers'] if p['id'] == id), None)
    if profesor:
        return jsonify(profesor)
    return jsonify({"error": "Profesor no encontrado"}), 404

@app.route('/api/profesores/<id>', methods=['DELETE'])
def eliminar_profesor(id):
    data = cargar_datos()
    # Filtrar para eliminar
    data['teachers'] = [p for p in data['teachers'] if p ['id'] != id]
    guardar_datos(data)
    return jsonify({"success": True})

@app.route('/api/profesores/<id>/unavailability', methods=['PUT'])
def actualizar_disponibilidad(id):
    data = cargar_datos()
    nueva_disponibilidad = request.json.get('unavailability', {})
    
    for i, p in enumerate(data['teachers']):
        if p['id'] == id:
            data['teachers'][i]['unavailability'] = nueva_disponibilidad
            break
    
    guardar_datos(data)
    return jsonify({"success": True})

@app.route('/api/profesores/importar', methods=['POST'])
def importar_profesores():
    if 'file' not in request.files:
        return jsonify({"error": "No hay archivo"}), 400
    
    file = request.files['file']
    try:
        # Leer el contenido y decodificarlo manejando posibles BOM de Excel (utf-8-sig)
        content = file.stream.read().decode("utf-8-sig")
        stream = io.StringIO(content)
        
        # Detectar automáticamente si el separador es , o ;
        dialect = csv.Sniffer().sniff(content[:1024])
        reader = csv.DictReader(stream, delimiter=dialect.delimiter)
        
        nuevos_profesores = []
        data = cargar_datos()
        
        # Obtener el número más alto de ID de profesor existente
        existing_ids = [p.get('id', '') for p in data.get('teachers', [])]
        max_num = 0
        for id_str in existing_ids:
            if id_str.startswith('T') and id_str[1:].isdigit():
                try:
                    num = int(id_str[1:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        
        next_id_num = max_num + 1
        row_index = 0
        
        for index, row in enumerate(reader):
            # Limpiamos las claves por si tienen espacios o caracteres raros
            # Esto ayuda si la columna se llama " NOMBRE" o "NOMBRE "
            clean_row = {k.strip().upper(): v.strip() for k, v in row.items() if k}
            
            nombre = clean_row.get('NOMBRE')
            facultad = clean_row.get('FACULTAD')

            if not nombre:
                continue

            grupo_facultad = facultad if facultad else "SIN FACULTAD"
            nuevo_id = f"T{next_id_num:03d}"

            nuevos_profesores.append({
                "id": nuevo_id,
                "name": nombre,
                "branch": [grupo_facultad],
                "unavailability": {}
            })
            
            next_id_num += 1

        if not nuevos_profesores:
            # Si llegamos aquí, es que leyó el archivo pero no encontró la columna 'NOMBRE'
            return jsonify({
                "error": "No se encontraron datos. Verifica que las columnas se llamen NOMBRE y FACULTAD."
            }), 400

        # Solo sobreescribimos si realmente hay datos nuevos
        data['teachers'] = nuevos_profesores
        guardar_datos(data)
        
        return jsonify({"success": True, "count": len(nuevos_profesores)})
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": f"Error al procesar el CSV: {str(e)}"}), 500

# ==== Rutas de restricciones ====
@app.route('/api/config/restricciones')
def obtener_restricciones():
    # Enviamos ID, label y descripción para que el frontend pueda mostrar tooltips.
    return jsonify({k: {"label": v['label'], "description": v.get('description', '')} for k, v in RESTRICCIONES_DISPONIBLES.items()})

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