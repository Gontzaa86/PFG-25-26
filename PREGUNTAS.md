__15/04/2026__
# Preguntas

## Profesores
- ¿Se tiene en cuenta si un profesor viene de Bilbao para asignar sus clases?
    - ¿No se le asignan a primera hora?
    - ¿Se trata de reducir la cantidad de días que tienen que venir?
- ¿Hay más elementos que pueden influir a las horas que un profesor puede dar clase?
- ¿Hay casos donde una clase no se asigna a cierto día por que el profesor no puede dar clase ese día?

## Aulas
- Clases que tengan dos aulas distintas, una para cada sesión de la semana
    - ¿Hay alguna razón por la que es así? O simplemente es por complicaciones al asignar la sesión.
    - ¿Hay asignaturas donde debe ser así? 
        - Ej.: *Electrónica Digital*

## Horas y Duración
- Horas de inicio y final en las clases por la tarde.
    - ¿Hora de inicio de las clases por la tarde? ¿14:30?
    - ¿Hora máxima a la que puede terminar una clase por la tarde? ¿21:00?
- Para las clases que tienen, por ejemplo, cinco horas semanales, se puede distribuir en dos sesiones de 02:30 o en una de 02:00 y una de 03:00.
    - ¿En qué caso se hace cada una? ¿Hay alguna razón o simplemente para encajar el horario?
- Clases que están divididas en varios grupos
    - Varias carreras pueden dar la misma asignatura simultaneamente, o en el mismo cuatrimestre, pero en grupos distintos, es decir, no coinciden en clase. ¿Puede haber estudiantes de un mismo grado en clases distintas?

# Restricciones
## Hard Constrains
- No puede haber dos clases en misma aula simultáneamente.
- Un profesor no impartir dar dos clases a la misma vez.
- Un *grupo* de estudiantes no puede dar dos clases a la vez.
- Solo puede haber una clase de la misma asignatura al día.

## Soft Constrains
__Niveles de Importancia, de 1-3.__ Siendo el 1 el más bajo y 3 el más alto. Si es cero, simplemente es indiferente.

- Evitar huecos __3__
- Minimizar desplazamiento entre edificios __2__
- Clases al día
    - Tres clases __1__
    - Dos clases __0__
    - Una clase __1__