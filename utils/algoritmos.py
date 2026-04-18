import random
import time
from utils.restricciones import RESTRICCIONES_DISPONIBLES

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

def evaluar_horario(asignaciones, restricciones_activas=None):
    """
    RESTRICCIONES BLANDAS (Sistema de penalización)
    Menor puntuación = Mejor horario
    """
    
    # Diccionario para guardar el desglose de restricciones (mas que nada para saber si funciona correctamente)
    log_penalizaciones = {clave: 0 for clave in (restricciones_activas or [])}
    total = 0

    if not restricciones_activas:
        return 0
    
    penalizacion = 0
    por_grado_dia = {}

    # Agrupar uan sola vez para todas las funciones
    for asig in asignaciones:
        for grado in asig['grades']:
            key = (grado, asig['dia'])
            por_grado_dia.setdefault(key, []).append(asig)
        
    # Ejecutamos solo las funciones seleccionadas
    for clave in (restricciones_activas or []):
        if clave in RESTRICCIONES_DISPONIBLES:
            valor = RESTRICCIONES_DISPONIBLES[clave]["func"](por_grado_dia)
            log_penalizaciones[clave] = valor
            total += valor
                
    return total, log_penalizaciones

def generar_horario_iterativo(data, term="Q1", restricciones=None):
    cursos = [c for c in data['courses'] if c['term'] == term]
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
            puntuacion, logs_actuales = evaluar_horario(asignaciones_actuales, restricciones)
            
            if puntuacion < mejor_puntuacion:
                mejor_puntuacion = puntuacion
                mejor_horario = list(asignaciones_actuales)
                mejores_logs = logs_actuales # Guardamos los logs ganadores
        
        yield i, {"horario": mejor_horario, "logs": mejores_logs}

def resolver_recursivo(index_curso, num_sesion, cursos, aulas, slots_posibles, asignaciones, start_time, limit, profesores_map):
    if time.time() - start_time > limit: return False
    if index_curso >= len(cursos): return True
    
    curso = cursos[index_curso]
    dias = list(curso['possible_days'])
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