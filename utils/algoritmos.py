import random
import time
import copy
from utils.restricciones import RESTRICCIONES_DISPONIBLES
import inspect

def verificar_solapamiento(inicio1, duracion1, inicio2, duracion2):
    return inicio1 < (inicio2 + duracion2) and inicio2 < (inicio1 + duracion1)

def es_valida(sesion_actual, asignaciones):
    """
    RESTRICCIONES DURAS
    """
    for sig in asignaciones:
        if sig['dia'] == sesion_actual['dia']:
            # 4. Solo una sesión del mismo curso al día
            if sig['curso'] == sesion_actual['curso']:
                return False
            
            # Chequeo de solapamiento horario
            if verificar_solapamiento(sesion_actual['slot'], sesion_actual['duracion'], 
                                      sig['slot'], sig['duracion']):
                
                # 1. No dos clases en misma aula
                if sig['aula'] == sesion_actual['aula']: return False
                # 2. No profesor dando dos clases
                if sig['teacher_id'] == sesion_actual['teacher_id']: return False
                # 3. No grupo (grados) dando dos clases
                if any(g in sig['grades'] for g in sesion_actual['grades']): return False
                
    return True

def evaluar_horario(asignaciones, restricciones_activas=None, data=None):
    """
    RESTRICCIONES BLANDAS (Sistema de penalización)
    Menor puntuación = Mejor horario
    """
    
    # Diccionario para guardar el desglose de restricciones (mas que nada para saber si funciona correctamente)
    log_penalizaciones = {clave: 0 for clave in (restricciones_activas or [])}
    total = 0

    if not restricciones_activas:
        return 0, log_penalizaciones
    
    penalizacion = 0
    por_grado_dia = {}

    # Agrupar uan sola vez para todas las funciones
    for asig in asignaciones:
        for grado in asig['grades']:
            key = (grado, asig['dia'])
            por_grado_dia.setdefault(key, []).append(asig)
        
    # Antes de ejecutar, comprobación defensiva: si alguna restricción activa necesita el dataset
    # y no se ha pasado `data`, lanzar un error claro para evitar AttributeError en funciones internas.
    if data is None:
        for clave in (restricciones_activas or []):
            if clave in RESTRICCIONES_DISPONIBLES:
                func = RESTRICCIONES_DISPONIBLES[clave]["func"]
                try:
                    sig = inspect.signature(func)
                    if len(sig.parameters) == 2:
                        raise ValueError(f"La restricción '{clave}' requiere el dataset 'data'. Pasa 'data' a evaluar_horario")
                except ValueError:
                    # re-raise para que el mensaje llegue al usuario
                    raise
                except Exception:
                    # si no podemos inspeccionar, no asumimos nada
                    continue

    # Ejecutamos solo las funciones seleccionadas
    for clave in (restricciones_activas or []):
        if clave in RESTRICCIONES_DISPONIBLES:
            func = RESTRICCIONES_DISPONIBLES[clave]["func"]
            # si la función acepta 2 parámetros (por_grado_dia, data) la llamamos con data
            try:
                sig = inspect.signature(func)
                if len(sig.parameters) == 2:
                    valor = func(por_grado_dia, data)
                else:
                    valor = func(por_grado_dia)
            except Exception:
                # fallback
                try:
                    valor = func(por_grado_dia, data)
                except TypeError:
                    valor = func(por_grado_dia)

            log_penalizaciones[clave] = valor
            total += valor
                
    return total, log_penalizaciones

def generar_horario_iterativo(data, term="Q1", restricciones=None, selected_grades=None):
    # Filtrar cursos por cuatrimestre, excluir optativas y (opcional) filtrar por grados seleccionados
    selected_set = set(selected_grades) if selected_grades else None

    def grade_matches_selection(grade):
        # grade: e.g., '1ADE' -> root 'ADE'
        if not selected_set:
            return True
        root = __import__('re').sub(r'^\\d+', '', grade)
        # Direct match (e.g., '1ADE') or root match (we encode roots as e.g. 'root:ADE' from frontend)
        if grade in selected_set:
            return True
        if root in selected_set:
            return True
        if ('root:' + root) in selected_set:
            return True
        return False

    cursos = [
        c for c in data.get('courses', [])
        if c.get('term') == term
        and not c.get('optativa', False)
        and (selected_set is None or any(grade_matches_selection(g) for g in c.get('grades', [])))
    ]
    aulas = data['rooms']
    slots_posibles = list(range(0, 12)) # 08:00 - 14:00
    profesores_map = {p['id']: p['name'] for p in data.get('teachers', [])}
    
    mejor_horario = None
    mejor_puntuacion = float('inf')
    mejores_logs = {} # Guardar logs del mejor horario

    for i in range(1, 21):
        asignaciones_actuales = []
        random.shuffle(cursos)
        start_time = time.time()
        
        # Intentamos resolver (con un límite de 3 segundos para no bloquear)
        if resolver_recursivo(0, 0, cursos, aulas, slots_posibles, asignaciones_actuales, start_time, 3, profesores_map):
            # Si es válido, evaluamos las restricciones blandas
            puntuacion, logs_actuales = evaluar_horario(asignaciones_actuales, restricciones, data)
            
            if puntuacion < mejor_puntuacion:
                mejor_puntuacion = puntuacion
                mejor_horario = list(asignaciones_actuales)
                mejores_logs = logs_actuales # Guardamos los logs ganadores
        
        yield i, {"horario": mejor_horario, "logs": mejores_logs}

def resolver_recursivo(index_curso, num_sesion, cursos, aulas, slots_posibles, asignaciones, start_time, limit, profesores_map):
    if time.time() - start_time > limit: return False
    if index_curso >= len(cursos): return True
    
    curso = cursos[index_curso]
    # possible_days puede ser una lista de días o 'all', representando los cinco días
    pd = curso.get('possible_days', 'all')
    if isinstance(pd, str) and pd == 'all':
        dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    else:
        dias = list(pd)
    random.shuffle(dias)
    
    # Para favorecer la falta de huecos, intentamos los slots en orden (0, 1, 2...)
    # en lugar de aleatorios, así las clases tienden a "pegarse" al inicio.
    for dia in dias:
        for slot in slots_posibles:
            if slot + curso['duration_slots'] > max(slots_posibles) + 1: continue
            
            aulas_c = [r for r in aulas if r['id'] in curso['possible_rooms']]
            # Para minimizar desplazamientos, podrías priorizar aquí el último edificio usado
            random.shuffle(aulas_c) 

            for aula in aulas_c:
                if aula['capacity'] < curso['students']: continue
                
                sesion = {
                    "curso": curso['name'], "teacher_id": curso['teacher'],
                    "profesor": profesores_map.get(curso['teacher'], "Desconocido"),
                    "grades": curso['grades'], "aula": aula['id'],
                    "edificio": aula['building'], "dia": dia, "slot": slot,
                    "duracion": curso['duration_slots']
                }

                if es_valida(sesion, asignaciones):
                    asignaciones.append(sesion)
                    
                    sig_c, sig_s = (index_curso + 1, 0) if num_sesion + 1 >= curso['sessions_per_week'] else (index_curso, num_sesion + 1)
                    
                    if resolver_recursivo(sig_c, sig_s, cursos, aulas, slots_posibles, asignaciones, start_time, limit, profesores_map):
                        return True
                    asignaciones.pop()
    return False

# Función de optimización de horarios
def optimizar_horario(horario_inicial, restricciones, data, iteraciones=5000): # Cantidad de iteraciones modificable
    """
    Toma un horario base y realiza mutaciones aleatorias controladas para reducir
    las penalizaciones de restricciones blandas.
    """
    mejor_horario = copy.deepcopy(horario_inicial)
    mejor_puntuacion, _ = evaluar_horario(mejor_horario, restricciones, data)
    puntuacion_inicial = mejor_puntuacion

    print(f"\n--- Iniciando Optimización ---")
    print(f"Puntuación inicial: {puntuacion_inicial}")

    aulas = data['rooms']
    slots_posibles = list(range(0, 12))
    dias_posibles = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    for i in range(1, iteraciones + 1):
        # Copiar para no corromper el horario original
        candidato = copy.deepcopy(mejor_horario)

        # Seleccionar una clase al azar y extrar para validar solapamientos
        idx = random.randrange(len(candidato))
        sesion = candidato.pop(idx)

        # Mutación aleatoria: Cambiar día, slot o aula
        sesion['dia'] = random.choice(dias_posibles)
        sesion['slot'] = random.choice(slots_posibles)

        # Ajuste de seguridad para no desbordar el último slot
        if sesion['slot'] + sesion['duracion'] > max(slots_posibles) + 1:
            sesion['slot'] = max(slots_posibles) + 1 - sesion['duracion']
        
        # Validar restricciones duras antes de evaluar las blandas
        if es_valida(sesion, candidato):
            candidato.append(sesion)
            puntuacion_actual, _ = evaluar_horario(candidato, restricciones, data)

            # Si la penalización es menor, actualizar el "mejor"
            if puntuacion_actual < mejor_puntuacion:
                mejor_puntuacion = puntuacion_actual
                mejor_horario = candidato
        
        else:
            # Si el cambio es inválido, descartar
            continue

        # Mostrar progeso por consola para ver avance real
        if i % 100 == 0:
            print (f"Puntuacion tras {i} iteraciones: {mejor_puntuacion}")
    
    print(f"Optimización finalizada. Puntuación final: {mejor_puntuacion}")
    print(f"Mejora total: {puntuacion_inicial - mejor_puntuacion} puntos.")
    print(f"------------------------------\n")
    
    return mejor_horario, mejor_puntuacion