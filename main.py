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
    aulas_lista = data.get('rooms', [])

    # Ordenar aulas por ID
    aulas_ordenadas = sorted(aulas_lista, key=lambda x: (
        int(''.join(filter(str.isdigit, x['id']))) if any(char.isdigit() for char in x['id']) else float('inf'),
        x['id']
    ))

    return render_template('aulas.html', edificios=edificios, aulas=aulas_ordenadas)

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

# ==== Rutas de profesores ====
@app.route('/api/aulas/importar', methods=['POST'])
def importar_aulas():
    if 'file' not in request.files:
        return jsonify({"error": "No se subió ningún archivo"}), 400
    
    file = request.files['file']
    try:
        # Leer contenido y normalizar saltos de línea
        content = file.stream.read().decode("utf-8-sig").replace('\r\n', '\n').replace('\r', '\n')
        stream = io.StringIO(content)
        
        # Intentar detectar el separador manualmente si falla el sniffer
        sample = content[:1024]
        if ';' in sample:
            delimiter = ';'
        elif '\t' in sample:
            delimiter = '\t'
        else:
            delimiter = ','
            
        reader = csv.DictReader(stream, delimiter=delimiter)
        
        nuevas_aulas = []
        nombres_edificios = set()
        aulas_procesadas = set() # Para evitar aulas duplicadas

        for row in reader:
            # Normalización extrema de claves: quitar espacios, acentos y pasar a mayúsculas
            # Esto ayuda si la columna se llama "Aulas", "AULA " o "aula"
            clean_row = {}
            for k, v in row.items():
                if k:
                    key_norm = str(k).strip().upper()
                    clean_row[key_norm] = str(v).strip() if v else ""

            # Buscamos las columnas por nombre exacto o aproximado
            aula_raw = clean_row.get('AULA')
            edificio_raw = clean_row.get('EDIFICIO')
            aforo_raw = clean_row.get('AFORO') or "0"

            if not aula_raw or not edificio_raw:
                print(f"Fila ignorada por falta de datos: {clean_row}") # Ver en consola de Flask
                continue

            nombre_edificio = normalizar_nombre_edificio(edificio_raw)
            
            # Si contiene "(" se queda solo con lo anterior
            aula_id = aula_raw.split('(')[0].strip()

            # Filtro de aulas duplicadas
            if aula_id in aulas_procesadas:
                print(f"Aula duplicada ignorada: {aula_id}")
                continue

            aulas_procesadas.add(aula_id)

            try:
                # Limpiar el aforo de posibles decimales o caracteres no numéricos
                capacidad = int(float(aforo_raw.replace(',', '.')))
            except:
                capacidad = 0
            
            nuevas_aulas.append({
                "id": aula_id,
                "building": nombre_edificio,
                "capacity": capacidad
            })
            nombres_edificios.add(nombre_edificio)

        if not nuevas_aulas:
            # Imprimir las cabeceras detectadas para depurar si falla
            print(f"Cabeceras detectadas: {reader.fieldnames}")
            return jsonify({
                "error": f"No se encontraron datos. Cabeceras detectadas: {reader.fieldnames}. Asegúrate de usar AULA, AFORO y EDIFICIO."
            }), 400

        # Sobrescribir datos en el JSON
        data = cargar_datos()
        data['rooms'] = nuevas_aulas
        data['buildings'] = sorted(list(nombres_edificios))
        
        guardar_datos(data)
        
        return jsonify({"success": True, "count": len(nuevas_aulas)})
    
    except Exception as e:
        print(f"Error crítico: {e}")
        return jsonify({"error": f"Error al procesar el CSV: {str(e)}"}), 500

# ==== Rutas de aulas ==== 
@app.route('/api/aulas', methods=['POST'])
def gestionar_aula():
    data = cargar_datos()
    aula = request.json or {}

    original_id = str(aula.get('original_id', '')).strip()
    aula_id = str(aula.get('id', '')).strip()
    building = str(aula.get('building', '')).strip()
    capacity_value = aula.get('capacity')

    if not aula_id or not building or capacity_value in (None, ''):
        return jsonify({"error": "El ID del aula, el edificio y la capacidad son obligatorios."}), 400

    building = normalizar_nombre_edificio(building)

    try:
        capacity = int(capacity_value)
    except (ValueError, TypeError):
        return jsonify({"error": "La capacidad debe ser un número entero."}), 400

    rooms = data.get('rooms', [])

    if original_id:
        existing = next((r for r in rooms if r['id'] == original_id), None)
        if not existing:
            return jsonify({"error": "Aula no encontrada para edición."}), 404
        if aula_id != original_id and any(r['id'] == aula_id for r in rooms):
            return jsonify({"error": "Ya existe un aula con ese ID."}), 400
        existing['id'] = aula_id
        existing['building'] = building
        existing['capacity'] = capacity
    else:
        if any(r['id'] == aula_id for r in rooms):
            return jsonify({"error": "Ya existe un aula con ese ID."}), 400
        rooms.append({
            "id": aula_id,
            "building": building,
            "capacity": capacity
        })

    edificios = sorted({r['building'] for r in rooms})
    data['rooms'] = rooms
    data['buildings'] = edificios
    guardar_datos(data)
    return jsonify({"success": True, "id": aula_id})

@app.route('/api/aulas/<id>', methods=['GET'])
def obtener_aula(id):
    data = cargar_datos()
    aula = next((r for r in data.get('rooms', []) if r['id'] == id), None)
    if aula:
        return jsonify(aula)
    return jsonify({"error": "Aula no encontrada"}), 404

@app.route('/api/aulas/<id>', methods=['DELETE'])
def eliminar_aula(id):
    data = cargar_datos()
    rooms = [r for r in data.get('rooms', []) if r['id'] != id]
    if len(rooms) == len(data.get('rooms', [])):
        return jsonify({"error": "Aula no encontrada"}), 404

    data['rooms'] = rooms
    data['buildings'] = sorted({r['building'] for r in rooms})
    guardar_datos(data)
    return jsonify({"success": True})

# ==== Rutas de restricciones ====
@app.route('/api/config/restricciones')
def obtener_restricciones():
    # Enviamos ID, label y descripción para que el frontend pueda mostrar tooltips.
    return jsonify({k: {"label": v['label'], "description": v.get('description', '')} for k, v in RESTRICCIONES_DISPONIBLES.items()})

# ---------------------------------------------------------
# RUTAS PRUEBAS ============ ELIMINAR EN EL FUTURO ==============
# ---------------------------------------------------------

@app.route("/revision/carreras", methods=['GET', 'POST'])
def revision_carreras():
    elementos_unicos = set()
    
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                content = file.stream.read().decode("utf-8-sig")
                stream = io.StringIO(content)
                
                # Detectar delimitador automáticamente
                dialect = csv.Sniffer().sniff(content[:1024]) if content else None
                delimiter = dialect.delimiter if dialect else ','
                
                reader = csv.DictReader(stream, delimiter=delimiter)
                
                for row in reader:
                    # Normalizar cabeceras para encontrar "SE JUNTA CON"
                    clean_row = {str(k).strip().upper(): v for k, v in row.items() if k}
                    valor = clean_row.get('SE JUNTA CON')
                    
                    if valor:
                        # Si hay varios elementos separados por comas en la misma celda, los separamos
                        partes = [p.strip() for p in str(valor).split(',') if p.strip()]
                        for p in partes:
                            elementos_unicos.add(p)

    # Ordenar alfabéticamente
    lista_ordenada = sorted(list(elementos_unicos))
    
    return render_template('revision_carreras.html', carreras=lista_ordenada)

# ---------------------------------------------------------
# FUNCIONES
# ---------------------------------------------------------

def normalizar_nombre_edificio(raw):
    if raw is None:
        return ''

    value = str(raw).strip()
    if value.lower().startswith('ed-'):
        value = value[3:].strip()

    if '(' in value:
        value = value.split('(')[0].strip()

    value = ' '.join(value.split())

    def capitalizar_segmento(segmento):
        partes = segmento.split('-')
        return '-'.join(part.capitalize() for part in partes if part)

    value = ' '.join(capitalizar_segmento(palabra) for palabra in value.split(' '))
    return f"Ed-{value}" if value else ''


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