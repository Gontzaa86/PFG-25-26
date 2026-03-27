import random

def verificar_solapamiento(inicio1, duracion1, inicio2, duracion2):
    """Implementa la fórmula: (inicio1 < fin2) AND (inicio2 < fin1) """
    fin1 = inicio1 + duracion1
    fin2 = inicio2 + duracion2
    return inicio1 < fin2 and inicio2 < fin1

def es_valida(sesion_actual, asignaciones, data):
    """Verifica restricciones duras: Aula, Profesor y Grado [cite: 134, 135, 136]"""
    for sig in asignaciones:
        # Si coinciden en día y hay solapamiento de slots
        if sig['dia'] == sesion_actual['dia'] and \
           verificar_solapamiento(sesion_actual['slot'], sesion_actual['duracion'], 
                                  sig['slot'], sig['duracion']):
            
            # 1. Restricción de Aula [cite: 134]
            if sig['aula'] == sesion_actual['aula']:
                return False
            
            # 2. Restricción de Profesor [cite: 135]
            if sig['teacher_id'] == sesion_actual['teacher_id']:
                return False
            
            # 3. Restricción de Grado (Cohortes) 
            # Comprobar si comparten algún grado en la lista de 'grades'
            if any(grado in sig['grades'] for grado in sesion_actual['grades']):
                return False
    return True

def generar_horario(data, term="Q1"):
    cursos = [c for c in data['courses'] if c['term'] == term]
    aulas = data['rooms']
    dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    # Slots disponibles (de 0 a 47 según tu config de 30min) [cite: 99, 100]
    slots_posibles = list(range(0, 20)) # Limitamos a mañana para la prueba

    asignaciones_finales = []

    def resolver(index_curso, num_sesion):
        if index_curso >= len(cursos):
            return True
        
        curso = cursos[index_curso]
        
        # Intentar asignar la sesión actual
        posibles_dias = curso['possible_days']
        random.shuffle(posibles_dias) # Mezclar para no dar siempre el mismo resultado

        for dia in posibles_dias:
            for slot in slots_posibles:
                for aula_id in curso['possible_rooms']:
                    aula = next(r for r in aulas if r['id'] == aula_id)
                    
                    # Restricción de capacidad [cite: 137]
                    if aula['capacity'] < curso['students']:
                        continue

                    sesion_propuesta = {
                        "curso": curso['name'],
                        "id": curso['id'],
                        "teacher_id": curso['teacher'],
                        "grades": curso['grades'],
                        "aula": aula['id'],
                        "edificio": aula['building'],
                        "dia": dia,
                        "slot": slot,
                        "duracion": curso['duration_slots']
                    }

                    if es_valida(sesion_propuesta, asignaciones_finales, data):
                        asignaciones_finales.append(sesion_propuesta)
                        
                        # Pasar a la siguiente sesión o siguiente curso
                        sig_curso = index_curso
                        sig_sesion = num_sesion + 1
                        if sig_sesion >= curso['sessions_per_week']:
                            sig_curso += 1
                            sig_sesion = 0
                        
                        if resolver(sig_curso, sig_sesion):
                            return True
                        
                        asignaciones_finales.pop() # Backtrack
        return False

    if resolver(0, 0):
        return asignaciones_finales
    return None