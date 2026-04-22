# Algoritmo
### Texto ofrecido por Gemini para la mejora y realización del algoritmo actual (22/04/2026)
Tu enfoque actual es una búsqueda estocástica iterativa (fuerza bruta controlada con backtracking). Aunque es funcional para problemas pequeños, se queda corto en problemas de optimización combinatoria porque no tiene una "memoria" de qué decisiones llevaron a un buen resultado ni una estrategia para escapar de óptimos locales.

El CPSolver de Tomáš Müller (UniTime) se basa en Búsqueda Local con Restricciones (Constraint-Based Local Search) combinada con Algoritmos Genéticos y Búsqueda Tabú. 

Para transformar tu código actual hacia esa arquitectura sin reescribirlo todo desde cero, aquí tienes las estrategias clave que debes implementar:

## 1. De "Generar 20" a "Mejora Iterativa"
En lugar de desechar los horarios y empezar de cero cada vez, debes aplicar operadores de movimiento sobre un horario ya existente para reducir su penalización.

El Ciclo de Optimización:

1. **Generar una solución inicial**: Usa tu resolver_recursivo una sola vez para obtener un horario válido (aunque sea "malo").
2. **Fase de Reparación/Mejora**: Selecciona una variable (una clase) que esté causando penalizaciones (p. ej., una clase en un edificio distinto a la anterior).
3. **Movimiento**: Cambia esa clase a otro slot o aula.
4. **Aceptar o Rechazar**: Si la nueva puntuación es mejor, quédatela. Si es peor, acéptala solo con una probabilidad pequeña (Simulated Annealing) para evitar atascarte.

## 2. Implementar un "Conflict-Based Statistics"
El CPSolver destaca por aprender de sus errores. En tu código, podrías añadir un contador de conflictos:
- Si el backtracking falla mucho en una asignatura específica, auméntale un peso de dificultad.
- En la siguiente iteración, intenta asignar primero las asignaturas que más conflictos generaron.

## 3. Estructura de Gran Vecindad (LNS)
Esta es la técnica "secreta" de muchos solvers modernos. En lugar de cambiar una clase, "destruyes" una parte del horario y la vuelves a construir:

```
def optimizar_lns(mejor_horario, iteraciones=100):
    for _ in range(iteraciones):
        # 1. 'Romper' el 10% del horario aleatoriamente
        fragmento_borrado = seleccionar_clases_a_reubicar(mejor_horario)
        
        # 2. Intentar reinsertar esas clases usando tu resolver_recursivo
        # pero con un enfoque más agresivo de optimización
        nuevo_horario = reinsertar_clases(fragmento_borrado, mejor_horario)
        
        # 3. Comparar con evaluar_horario()
        if evaluar_horario(nuevo_horario) < evaluar_horario(mejor_horario):
            mejor_horario = nuevo_horario
```
## 4. Mejoras Técnicas en tu Código
1. Pre-cálculo de Dominios

    Tu función es_valida se ejecuta miles de veces. En lugar de iterar sobre todas las asignaciones existentes cada vez, utiliza una matriz de ocupación:
- ```ocupacion_aulas[aula_id][dia][slot]```
- ```ocupacion_profesores[profe_id][dia][slot]```

    Esto reduce la complejidad de $O(N)$ a $O(1)$ para verificar restricciones duras.

2. Evaluación Delta

    Actualmente, ``evaluar_horario`` recorre todo el horario cada vez. Un solver profesional solo calcula la diferencia (delta):

    "Si muevo la clase A del Slot 1 al Slot 5, ¿cuánto cambia la penalización de ventanas solo para ese grupo?"

## 5. Ejemplo de Algoritmo de Búsqueda Local (Hill Climbing)
Si quieres algo más potente que tus 20 intentos, implementa este bucle después de obtener tu primer horario:

```
def busqueda_local(horario_inicial, max_intentos=1000):
    actual = horario_inicial
    puntuacion_actual = evaluar_horario(actual)
    
    for _ in range(max_intentos):
        # Seleccionar una sesión al azar
        idx = random.randrange(len(actual))
        original = actual[idx].copy()
        
        # Intentar un cambio aleatorio (Movimiento)
        actual[idx]['slot'] = random.choice(range(0, 12))
        actual[idx]['dia'] = random.choice(['L', 'M', 'X', 'J', 'V'])
        
        if es_valida(actual[idx], actual[:idx] + actual[idx+1:]):
            nueva_puntuacion = evaluar_horario(actual)
            if nueva_puntuacion < puntuacion_actual:
                puntuacion_actual = nueva_puntuacion
            else:
                # Deshacer si es peor (Hill Climbing puro)
                actual[idx] = original
        else:
            actual[idx] = original
    return actual
```
**¿Por qué esto es mejor?**

Porque en lugar de disparar a ciegas (20 veces), el algoritmo camina hacia la solución óptima, refinando constantemente los bordes del horario. Si quieres ir al nivel de UniTime, deberías investigar librerías como Google OR-Tools (CP-SAT), que implementa estas heurísticas de forma nativa en Python y es extremadamente eficiente para este tipo de problemas.

# Enlace a la conversación (Gemini)
https://gemini.google.com/share/b80ee6f106f0