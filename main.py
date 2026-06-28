import json
import os
import csv
import io
import re
from flask import Flask, render_template, Response, request, jsonify 
from utils.algoritmos import generar_horario_iterativo, evaluar_horario, optimizar_horario
from utils.restricciones import RESTRICCIONES_DISPONIBLES

GRADO_NOMBRES_COMPLETOS = {
    'ADE': 'Administración de Empresas',
    'AII': 'Administración de Empresas + Ingeniería Informática',
    'CDIA': 'Ciencia de Datos e Inteligencia Artificial',
    'CDIA+': 'Ciencia de Datos e Inteligencia Artificial + Ingeniería Informática',
    'CO': 'Comunicación',
    'D': 'Derecho',
    'ESTS': 'Educación Social + Trabajo Social',
    'II': 'Ingeniería Informática',
    'RID': 'Relaciones Internacionales + Derecho',
    'TS': 'Trabajo Social'
}

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
    rooms = data.get('rooms', [])
    buildings = data.get('buildings', [])

    # Cursos agrupados por grado (1II, 2II, 3II / 1ADE, 2ADE, 3ADE / 1CDIA, 2CDIA, 3CDIA...) 
    grupos = {}
    for grado in grados:
        grado_id = str(grado.get('id', '')).strip()
        match = re.match(r'^(\d+)(.+)$', grado_id)
        if match:
            curso = int(match.group(1))
            grupo_codigo = match.group(2).strip()
        else:
            curso = 0
            grupo_codigo = grado_id

        grupos.setdefault(grupo_codigo, []).append({
            'id': grado_id,
            'name': grado.get('name', grado_id),
            'year': curso
        })

    grupos_grados = []
    for grupo_codigo, lista in sorted(grupos.items(), key=lambda item: item[0]):
        lista.sort(key=lambda g: (g['year'], g['id']))
        grupos_grados.append({
            'root': grupo_codigo,
            'root_name': lista[0]['name'] if lista else grupo_codigo,
            'grados': lista
        })

    return render_template('grados.html', grupos_grados=grupos_grados, asignaturas=asignaturas, profesores=profesores, rooms=rooms, buildings=buildings, grados_lista=grados)

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
    # Obtener lista de grados seleccionados (ej: ?grados=1II&grados=2II)
    grados_seleccionados = request.args.getlist('grados')

    ruta_json = os.path.join(app.root_path, 'data', 'dataset_prueba2.json')
    
    if not os.path.exists(ruta_json):
        return "Error: No se encontró el dataset", 404

    def generate():
        with open(ruta_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        pool_horarios = [] # Para almacenar los 20 intentos iniciales

        # Ejecutamos el generador del algoritmo
        for progreso, resultado in generar_horario_iterativo(data, term=term_usuario, restricciones=restricciones_usuario, selected_grades=grados_seleccionados):
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

        if not top_5:
            payload = {
                'progreso': 20,
                'fase': 'finalizado',
                'horario': [],
                'logs': {},
                'error': 'El algoritmo no encontró ninguna solución, por favor, inténtelo de nuevo.'
            }
            yield f"data: {json.dumps(payload)}\n\n"
            return

        ganador_absoluto = None
        mejor_puntaje_global = float('inf')

        for i, candidato in enumerate(top_5):
            # Notificamos al usuario que estamos optimizando
            yield f"data: {json.dumps({'progreso': 20, 'fase': f'optimizando {i+1}/5'})}\n\n"

            h_opt, p_opt = optimizar_horario(candidato['horario'], restricciones_usuario, data)

            if h_opt is None or p_opt is None:
                continue

            if p_opt < mejor_puntaje_global:
                mejor_puntaje_global = p_opt
                _, logs_finales = evaluar_horario(h_opt, restricciones_usuario, data)
                ganador_absoluto = {"horario": h_opt, "logs": logs_finales}

        if ganador_absoluto is None:
            payload = {
                'progreso': 20,
                'fase': 'finalizado',
                'horario': [],
                'logs': {},
                'error': 'El algoritmo no encontró ninguna solución, por favor, inténtelo de nuevo.'
            }
        else:
            payload = {
                'progreso': 20,
                'fase': 'finalizado',
                'horario': ganador_absoluto['horario'],
                'logs': ganador_absoluto['logs']
            }
        yield f"data: {json.dumps(payload)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/grados/list')
def api_grados_list():
    data = cargar_datos()
    return jsonify(data.get('grades', []))

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
        
        for index, row in enumerate(reader):
            # Limpiamos las claves por si tienen espacios o caracteres raros
            # Esto ayuda si la columna se llama " NOMBRE" o "NOMBRE "
            clean_row = {k.strip().upper(): v.strip() for k, v in row.items() if k}
            
            nombre = clean_row.get('NOMBRE')
            facultades = parsear_facultades(clean_row.get('FACULTAD'))

            if not nombre:
                continue

            nuevo_id = generar_id_profesor(index)

            nuevos_profesores.append({
                "id": nuevo_id,
                "name": nombre,
                "branch": facultades,
                "unavailability": {}
            })

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

# ==== Rutas de aulas ====
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

# ==== Rutas de asignaturas/grados ====
@app.route('/api/asignaturas/importar', methods=['POST'])
def importar_asignaturas():
    if 'file' not in request.files:
        return jsonify({"error": "No se ha subido ningún archivo"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Archivo no seleccionado"}), 400
    
    if file and file.filename.endswith('.csv'):
        # Leer el contenido
        content = file.stream.read().decode("utf-8-sig")
        stream = io.StringIO(content)
        reader = csv.DictReader(stream)

        # Cargar datos actuales (dataset) para búsqueda de profesores
        data = cargar_datos()
        profesores_db = data.get('teachers', [])
        profesores_por_nombre = {
            normalize_name(p['name']): p['id']
            for p in profesores_db
            if p.get('name')
        }

        nuevas_asignaturas = [] # Listado de asignaturas importadas
        contador_id = 1 # ID único para las asignaturas, no se utilizará el del csv. Al menos no de momento.
        grados_importados = set()

        # Diccionario para contar sesiones (Agrupación por nombre + idioma)
        conteo_sesiones = {}
        filas_csv = list(reader)

        # Primera pasada: Contar sesiones por asignatua e idioma
        for fila in filas_csv:
            clave = (fila['Asignatura'], fila['IDIOMA'], fila['SEMESTRE'], fila['Docente'])
            conteo_sesiones[clave] = conteo_sesiones.get(clave, 0) + 1
        
        # Segunda pasada: Crear los objetos de asignatura (evitando duplicados en el JSON final)
        asignaturas_procesadas = set()
        for fila in filas_csv:
            nombre_base = fila.get('Asignatura', '')
            idioma = fila.get('IDIOMA', '')
            docente_nombre = fila.get('Docente', '')
            semestre = fila.get('SEMESTRE', '')

            id_proceso = f"{nombre_base}-{idioma}-{semestre}-{docente_nombre}"
            if id_proceso in asignaturas_procesadas:
                continue
                
            # Buscar ID del profesor por el nombre usando normalización
            nombre_docente_norm = normalize_name(docente_nombre)
            if nombre_docente_norm.startswith('pendiente') or nombre_docente_norm == '':
                profesor_id = "No asignado"
            else:
                profesor_id = profesores_por_nombre.get(nombre_docente_norm, "No asignado")
            
            # Procesar Aula: En el csv: "{id_aula} (edificio)" --> Extraer únicamente id
            aula_raw = fila.get('Aula', '')
            aula_id = ""
            if aula_raw and '(' in aula_raw:
                aula_id = aula_raw.split('(')[0].strip()
            elif aula_raw:
                aula_id = aula_raw.strip()
            
            # Procesar Alumnos, si el campo está vacio, entonces 0
            try:
                estudiantes = int(fila.get('Nº alumnos', '')) if fila.get('Nº alumnos', '') else 0
            except ValueError:
                estudiantes = 0
            
            # Procesar códigos de carreras (Grados)
            grados = [g.strip() for g in fila.get('SE JUNTA CON', '').split(',')] if fila.get('SE JUNTA CON', '') else []
            for alias in ['GRADO', 'CARRERA', 'GRADO/CARRERA', 'CARRERA PRINCIPAL', 'CURSO']:
                if alias in fila and fila[alias]:
                    for valor in [g.strip() for g in fila[alias].split(',') if g.strip()]:
                        if valor not in grados:
                            grados.append(valor)

            for grado in grados:
                if grado:
                    grados_importados.add(grado)

            # Construir Objeto
            nueva_asignatura = {
                "id": str(contador_id),
                "name": f"{nombre_base} ({idioma})",
                "term": f"Q{semestre}",
                "teacher": profesor_id,
                "grades": grados,
                "students": estudiantes,
                "sessions_per_week": conteo_sesiones[(nombre_base, idioma, semestre, docente_nombre)],
                "duration_slots": 4, # Valor por defecto
                "possible_rooms": [aula_id] if aula_id else [],
                "possible_days": "all",
                "optativa": False
            }

            nuevas_asignaturas.append(nueva_asignatura)
            asignaturas_procesadas.add(id_proceso)
            contador_id += 1
        
        # Sobreescribir datos de asignaturas
        data['courses'] = nuevas_asignaturas

        # Añadir grados importados si no existen ya
        grades_existentes = {g['id'] for g in data.get('grades', [])}
        nuevos_grados = 0
        for codigo in sorted(grados_importados):
            if codigo and codigo not in grades_existentes:
                data.setdefault('grades', []).append({
                    "id": codigo,
                    "name": get_grade_display_name(codigo)
                })
                grades_existentes.add(codigo)
                nuevos_grados += 1

        guardar_datos(data)

        return jsonify({
            "message": f"Importación completada. {len(nuevas_asignaturas)} asignaturas agregadas, {nuevos_grados} grados nuevos actualizados."
        }), 200

    return jsonify({"error": "Formato de archivo no válido"}), 400

@app.route('/api/asignaturas/<id>/rooms', methods=['PUT'])
def actualizar_asignatura_rooms(id):
    data = cargar_datos()
    payload = request.json or {}
    nuevas = payload.get('possible_rooms')

    if nuevas is None or not isinstance(nuevas, list):
        return jsonify({"error": "Campo 'possible_rooms' inválido (se requiere lista)."}), 400

    updated = False
    for i, curso in enumerate(data.get('courses', [])):
        if str(curso.get('id')) == str(id):
            data['courses'][i]['possible_rooms'] = nuevas
            updated = True
            break

    if not updated:
        return jsonify({"error": "Asignatura no encontrada."}), 404

    guardar_datos(data)
    return jsonify({"success": True, "id": id, "possible_rooms": nuevas})

@app.route('/api/asignaturas/<id>', methods=['PUT'])
def actualizar_asignatra(id):
    data = cargar_datos()
    nuevo_data = request.json or {}

    # Buscar Asignatura
    curso_idx = next ((i for i, c in enumerate(data.get('courses', [])) if str(c.get('id')) == str(id)), None)

    if curso_idx is None:
        return jsonify({"error": "Asignatura no encontrada"}), 404
    
    # Validaciones y Conversiones Básicas
    try:
        students = int(nuevo_data.get('students', 0))
        sessions = int(nuevo_data.get('sessions_per_week', 2))
        duration = int(nuevo_data.get('duration_slots', 4))
    except (ValueError, TypeError):
        return jsonify({"error": "Los capos numéricos son inválidos"}), 400
    
    # Actualizar los campos
    curso = data['courses'][curso_idx]
    curso['name'] = str(nuevo_data.get('name', curso['name'])).strip()
    curso['term'] = f"Q{nuevo_data.get('term', '1')}" # Convierte 1 o 2 a Q1 o Q2
    curso['teacher'] = str(nuevo_data.get('teacher', 'No asignado'))
    curso['grades'] = nuevo_data.get('grades', [])
    curso['students'] = students
    curso['sessions_per_week'] = sessions
    curso['duration_slots'] = duration
    curso['optativa'] = bool(nuevo_data.get('optativa', False))

    guardar_datos(data)
    return jsonify({"success": True, "message": "Asignatura actualizada correctamente."})

@app.route('/api/grados', methods=['POST'])
def crear_grado():
    data = cargar_datos()
    nuevo = request.json or {}
    curso = str(nuevo.get('year', '')).strip()

    # Dos modos de creación:
    # 1) Selección de titulación existente: enviar 'existing_tag' con el tag (ej: ADE)
    # 2) Nueva titulación: enviar 'code' (tag) y 'name' (nombre completo)
    existing_tag = nuevo.get('existing_tag')

    if not curso:
        return jsonify({"error": "El curso (año) es obligatorio."}), 400

    if existing_tag:
        codigo = str(existing_tag).strip().upper()
        if not codigo:
            return jsonify({"error": "El tag de la titulación seleccionado es inválido."}), 400

        grado_id = f"{curso}{codigo}"

        if any(g['id'] == grado_id for g in data.get('grades', [])):
            return jsonify({"error": f"El grado {grado_id} ya existe."}), 400

        # Intentar recuperar el nombre de la titulación a partir de grados existentes
        nombre = None
        for g in data.get('grades', []):
            m = re.match(r'^(?:\d+)(.+)$', str(g.get('id', '')))
            if m and m.group(1).strip().upper() == codigo:
                nombre = g.get('name')
                break

        if not nombre:
            # Si no hay una entrada previa, intentar con el mapeo estático
            nombre = GRADO_NOMBRES_COMPLETOS.get(codigo, codigo)

        data.setdefault('grades', []).append({
            "id": grado_id,
            "name": nombre
        })

        guardar_datos(data)
        return jsonify({"success": True, "message": f"Grado {grado_id} creado con éxito (titulación existente)."})

    # Modo: nueva titulación completa
    codigo = str(nuevo.get('code', '')).strip().upper()
    nombre_proporcionado = str(nuevo.get('name', '')).strip()

    if not codigo or not nombre_proporcionado:
        return jsonify({"error": "Para crear una nueva titulación se requiere el tag y el nombre completo."}), 400

    grado_id = f"{curso}{codigo}"

    if any(g['id'] == grado_id for g in data.get('grades', [])):
        return jsonify({"error": f"El grado {grado_id} ya existe."}), 400

    data.setdefault('grades', []).append({
        "id": grado_id,
        "name": nombre_proporcionado
    })

    # También actualizar el mapeo estático en memoria para futuras inferencias (no persistente fuera de runtime)
    GRADO_NOMBRES_COMPLETOS[codigo] = nombre_proporcionado

    guardar_datos(data)
    return jsonify({"success": True, "message": f"Grado {grado_id} creado con éxito (nueva titulación)."})


@app.route('/api/asignaturas', methods=['POST'])
def crear_asignatura():
    data = cargar_datos()
    nuevo_data = request.json or {}
    
    if not nuevo_data.get('name'):
        return jsonify({"error": "El nombre de la asignatura es obligatorio."}), 400
        
    # Generar un ID único incremental numérico stringificado
    cursos_existentes = data.get('courses', [])
    max_id = 0
    for c in cursos_existentes:
        try:
            max_id = max(max_id, int(c.get('id', 0)))
        except ValueError:
            pass
    nuevo_id = str(max_id + 1)
    
    try:
        students = int(nuevo_data.get('students', 0))
        sessions = int(nuevo_data.get('sessions_per_week', 2))
        duration = int(nuevo_data.get('duration_slots', 4))
    except (ValueError, TypeError):
        return jsonify({"error": "Los campos numéricos son inválidos"}), 400

    nueva_asignatura = {
        "id": nuevo_id,
        "name": str(nuevo_data.get('name')).strip(),
        "term": f"Q{nuevo_data.get('term', '1')}",
        "teacher": str(nuevo_data.get('teacher', 'No asignado')),
        "grades": nuevo_data.get('grades', []),
        "students": students,
        "sessions_per_week": sessions,
        "duration_slots": duration,
        "possible_rooms": [], # Inicializa vacío para luego editarlo en su modal dedicado
        "possible_days": "all",
        "optativa": bool(nuevo_data.get('optativa', False))
    }
    
    data.setdefault('courses', []).append(nueva_asignatura)
    guardar_datos(data)
    return jsonify({"success": True, "message": "Asignatura creada correctamente."})

@app.route('/api/grados/<string:grado_id>', methods=['DELETE'])
def eliminar_grado(grado_id):
    data = cargar_datos()
    grado_id = grado_id.strip()

    # Eliminar de la lista global de 'grades'
    grados_iniciales = len(data.get('grades', []))
    data['grades'] = [g for g in data.get('grades', []) if g.get('id') != grado_id]
    
    if len(data['grades']) == grados_iniciales:
        return jsonify({"error": f"El grado {grado_id} no existe en el sistema."}), 404

    # Limpieza en cascada dentro de las asignaturas ('courses')
    asignaturas_actualizadas = []
    for curso in data.get('courses', []):
        if 'grades' in curso:
            # Quitamos el grado de la lista de esta asignatura
            curso['grades'] = [g for g in curso['grades'] if g != grado_id]
        
        # Si la asignatura ya no pertenece a ningún grado tras la eliminación, se descarta para evitar registros huérfanos.
        if len(curso.get('grades', [])) > 0:
            asignaturas_actualizadas.append(curso)
            
    data['courses'] = asignaturas_actualizadas

    guardar_datos(data)
    return jsonify({
        "success": True, 
        "message": f"Grado {grado_id} eliminado correctamente y referencias limpiadas en cascada."
    })


@app.route('/api/asignaturas/<string:curso_id>', methods=['DELETE'])
def eliminar_asignatura(curso_id):
    data = cargar_datos()
    curso_id = curso_id.strip()

    cursos_iniciales = len(data.get('courses', []))
    data['courses'] = [c for c in data.get('courses', []) if str(c.get('id')) != curso_id]

    if len(data['courses']) == cursos_iniciales:
        return jsonify({"error": f"La asignatura con ID {curso_id} no existe."}), 404

    guardar_datos(data)
    return jsonify({"success": True, "message": "Asignatura eliminada directamente del dataset."})

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

def get_grade_display_name(grade_id):
    if grade_id is None:
        return ''

    grade_id = str(grade_id).strip()
    match = re.match(r'^(?:\d+)(.+)$', grade_id)
    if not match:
        return grade_id

    suffix = match.group(1)
    return GRADO_NOMBRES_COMPLETOS.get(suffix, grade_id)


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
        data = json.load(f)

    # Asegurar nombres completos de grados cuando el nombre sea igual al ID o esté vacío
    for grado in data.get('grades', []):
        grado_id = str(grado.get('id', '')).strip()
        if not grado.get('name') or str(grado.get('name', '')).strip() == grado_id:
            grado['name'] = get_grade_display_name(grado_id)

    return data

def guardar_datos(data): # Modificación de datos en el JSON
    ruta_json = os.path.join(app.root_path, 'data', 'dataset_prueba2.json')
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_name(value): # Normaliza nombres tanto el csv como en dataset
    if value is None:
        return ""

    text = str(value).strip()
    # Eliminar texto sobrante, en el csv formato: "Apellido1 Apellido2, Nombre (url)". Eliminar url
    text = re.sub(r"\s*\([^)]*\)", "", text).strip()
    return re.sub(r"\s+", " ", text).lower()

# Parseo de facultades para importación
def parsear_facultades(facultad_raw):
    if facultad_raw is None:
        return ["SIN FACULTAD"]

    valores = [valor.strip() for valor in str(facultad_raw).split(",")]
    valores = [valor for valor in valores if valor]
    return valores if valores else ["SIN FACULTAD"]

# Ajuste de ID para mantener lógica (Si el orden es el mismo) al importar docentes.
def generar_id_profesor(index, prefijo="T"):
    return f"{prefijo}{index + 1:03d}"

# ---------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------

if __name__ == '__main__':
    # Debug=True para que el servidor se reinicie al guardar cambios
    app.run(debug=True, port=5000)