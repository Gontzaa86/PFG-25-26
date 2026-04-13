// Configuración de horas y días
const START_HOUR = 8;
const END_HOUR = 14; 
const SLOTS_PER_HOUR = 2; 
const TOTAL_SLOTS = (END_HOUR - START_HOUR) * SLOTS_PER_HOUR;

const diasSemana = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const diasNombresES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"];

// UI Elements
const btn = document.getElementById('btnEjecutar');
const loadingArea = document.getElementById('loading-area');
const contadorText = document.getElementById('contador');
const contenedorCalendarios = document.getElementById('calendarios-grados');

// Mapa de colores para asignaturas
const asignaturaColores = {};
let colorCounter = 1;

btn.onclick = function() {
    btn.disabled = true;
    loadingArea.style.display = 'block';
    contenedorCalendarios.innerHTML = "";
    contadorText.innerText = "0";
    Object.keys(asignaturaColores).forEach(key => delete asignaturaColores[key]);
    colorCounter = 1;

    const eventSource = new EventSource('/solver/progress');

    eventSource.onmessage = function(e) {
        const data = JSON.parse(e.data);
        contadorText.innerText = data.progreso;

        if (data.error) {
            contenedorCalendarios.innerHTML = `<div class='alert alert-danger'>Error: ${data.error}</div>`;
            eventSource.close();
            btn.disabled = false;
            loadingArea.style.display = 'none';
            return;
        }

        if (data.progreso === 20) {
            eventSource.close();
            btn.disabled = false;
            loadingArea.style.display = 'none';
            
            if (data.horario && data.horario.length > 0) {
                procesarYDibujarCalendarios(data.horario);
            } else {
                contenedorCalendarios.innerHTML = "<div class='alert alert-warning text-center'>No se encontró solución válida en 20 intentos.</div>";
            }
        }
    };

    eventSource.onerror = function() {
        eventSource.close();
        btn.disabled = false;
        loadingArea.style.display = 'none';
        console.error("Error de conexión SSE.");
    };
};

function procesarYDibujarCalendarios(horario) {
    const gradosSet = new Set();
    horario.forEach(sesion => {
        sesion.grades.forEach(grado => gradosSet.add(grado));
    });
    const listaGrados = Array.from(gradosSet).sort();

    listaGrados.forEach(grado => {
        const sesionesGrado = horario.filter(sesion => sesion.grades.includes(grado));
        if (sesionesGrado.length > 0) {
            crearEstructuraCalendario(grado, sesionesGrado);
        }
    });
}

function crearEstructuraCalendario(grado, sesiones) {
    let html = `
        <div class="calendar-container card shadow-sm p-3">
            <h3 class="grade-title text-center">Grado: ${grado}</h3>
            <table class="calendar-table">
                <thead>
                    <tr>
                        <th class="time-col">Hora</th>
                        ${diasNombresES.map(dia => `<th>${dia}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
    `;

    const matrizOcupada = Array(TOTAL_SLOTS).fill().map(() => Array(diasSemana.length).fill(false));

    for (let slotIdx = 0; slotIdx < TOTAL_SLOTS; slotIdx++) {
        const horaPaquete = calcularHoraHtml(slotIdx);
        html += `<tr>`;
        html += `<td class="time-col">${horaPaquete}</td>`;

        for (let diaIdx = 0; diaIdx < diasSemana.length; diaIdx++) {
            const diaEn = diasSemana[diaIdx];
            if (matrizOcupada[slotIdx][diaIdx]) continue;

            const sesion = sesiones.find(s => s.dia === diaEn && s.slot === slotIdx);

            if (sesion) {
                const duracion = sesion.duracion;
                const colorClass = obtenerColorAsignatura(sesion.curso);
                for (let d = 0; d < duracion; d++) {
                    if (slotIdx + d < TOTAL_SLOTS) matrizOcupada[slotIdx + d][diaIdx] = true;
                }
                html += `
                    <td rowspan="${duracion}">
                        <div class="session-cell ${colorClass}">
                            <div class="session-title">${sesion.curso}</div>
                            <div class="session-info">${sesion.aula} (${sesion.edificio})</div>
                            <div class="session-prof">${sesion.profesor || 'Sin Profesor'}</div>
                        </div>
                    </td>
                `;
            } else {
                html += `<td></td>`;
            }
        }
        html += `</tr>`;
    }
    html += `</tbody></table></div>`;
    contenedorCalendarios.innerHTML += html;
}

function calcularHoraHtml(slotIdx) {
    const totalMinutosDesdeOcho = slotIdx * 30;
    const hora = START_HOUR + Math.floor(totalMinutosDesdeOcho / 60);
    const minutos = totalMinutosDesdeOcho % 60;
    return `${String(hora).padStart(2, '0')}:${String(minutos).padStart(2, '0')}`;
}

function obtenerColorAsignatura(curso) {
    if (!asignaturaColores[curso]) {
        asignaturaColores[curso] = `bg-cat-${colorCounter}`;
        colorCounter = (colorCounter % 5) + 1;
    }
    return asignaturaColores[curso];
}