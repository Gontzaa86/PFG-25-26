# Restricciones blandas

def penalizar_clase_unica(por_grado_dia):
    """
    Penaliza días que tienen una sola clase (evita que el alumno vaya para nada).
    Teniendo en cuenta que puede haber alumnos que tengan que movilizarse desde lejos
    """

    penalizacion = 0
    for sesiones in por_grado_dia.values():
        if len(sesiones) == 1:
            penalizacion += 500
    return penalizacion

def penalizar_tres_clases(por_grado_dia):
    """Penaliza ligeramente los días con 3 clases para intentar equilibrar el horario."""
    penalizacion = 0
    for sesiones in por_grado_dia.values():
        if len(sesiones) == 3:
            penalizacion += 200
    return penalizacion

def penalizar_ventanas(por_grado_dia):
    """Penaliza huecos libres entre clases en un mismo día."""
    penalizacion = 0
    for sesiones in por_grado_dia.values():
        sesiones.sort(key=lambda x: x['slot'])
        for i in range(len(sesiones) - 1):
            fin_actual = sesiones[i]['slot'] + sesiones[i]['duracion']
            hueco = sesiones[i+1]['slot'] - fin_actual
            if hueco > 0:
                penalizacion += hueco * 1000
    return penalizacion

def penalizar_cambio_edificio(por_grado_dia):
    """Penaliza si el alumno debe cambiar de edificio entre clases consecutivas."""
    penalizacion = 0
    for sesiones in por_grado_dia.values():
        sesiones.sort(key=lambda x: x['slot'])
        for i in range(len(sesiones) - 1):
            if sesiones[i]['edificio'] != sesiones[i+1]['edificio']:
                penalizacion += 200
    return penalizacion

def penalizar_unavailability(por_grado_dia, data):
    """
    Penaliza asignaciones que caen dentro de la 'unavailability' del profesor.
    Devuelve una penalización numérica; por simplicidad la función usa el config
    de data para convertir slots a minutos y calcula solapamientos con rangos HH:MM-HH:MM
    o penaliza fuertemente si el día es 'all'.
    """
    penalizacion = 0
    teachers = {t['id']: t for t in data.get('teachers', [])}
    cfg = data.get('config', {})
    minutes_per_slot = cfg.get('minutes_per_slot', 30)
    start_hour = cfg.get('start_hour', '08:00')
    sh_h, sh_m = map(int, start_hour.split(':'))

    for sesiones in por_grado_dia.values():
        for s in sesiones:
            tid = s.get('teacher_id')
            if not tid:
                continue
            teacher = teachers.get(tid)
            if not teacher:
                continue
            unav = teacher.get('unavailability')
            if not unav:
                # aceptar [] o {} como sin restricciones
                continue

            dia = s.get('dia')
            periodo = None
            if isinstance(unav, dict):
                periodo = unav.get(dia)
            elif isinstance(unav, list):
                periodo = unav  # compatibilidad con listas vacías previas

            if not periodo:
                continue

            # sesión en minutos desde medianoche
            session_start = sh_h * 60 + sh_m + s['slot'] * minutes_per_slot
            session_end = session_start + s['duracion'] * minutes_per_slot

            if isinstance(periodo, str) and periodo == 'all':
                penalizacion += 5000
                continue

            if isinstance(periodo, list):
                for rng in periodo:
                    try:
                        a, b = rng.split('-')
                        ah, am = map(int, a.split(':'))
                        bh, bm = map(int, b.split(':'))
                        r_start = ah * 60 + am
                        r_end = bh * 60 + bm
                        if session_start < r_end and r_start < session_end:
                            overlap = min(session_end, r_end) - max(session_start, r_start)
                            penalizacion += int(overlap * 20)
                    except Exception:
                        penalizacion += 1000

    return penalizacion

# Diccionario para mapear los IDs que envíe el usuario con las funciones
RESTRICCIONES_DISPONIBLES = {
    "evitar_clase_unica": {"func": penalizar_clase_unica, "label": "Evitar días de clase única"},
    "equilibrar_tres_clases": {"func": penalizar_tres_clases, "label": "Equilibrar días de 3 clases"},
    "minimizar_ventanas": {"func": penalizar_ventanas, "label": "Minimizar huecos (Ventanas)"},
    "minimizar_desplazamientos": {"func": penalizar_cambio_edificio, "label": "Evitar cambios de edificio"},
    "evitar_unavailability": {"func": penalizar_unavailability, "label": "Evitar horarios fuera de disponibilidad (Unavailability)"}
}