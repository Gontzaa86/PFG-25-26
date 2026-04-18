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

# Diccionario para mapear los IDs que envíe el usuario con las funciones
RESTRICCIONES_DISPONIBLES = {
    "evitar_clase_unica": {"func": penalizar_clase_unica, "label": "Evitar días de clase única"},
    "equilibrar_tres_clases": {"func": penalizar_tres_clases, "label": "Equilibrar días de 3 clases"},
    "minimizar_ventanas": {"func": penalizar_ventanas, "label": "Minimizar huecos (Ventanas)"},
    "minimizar_desplazamientos": {"func": penalizar_cambio_edificio, "label": "Evitar cambios de edificio"}
}