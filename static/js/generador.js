// Configuración de horas y días
const START_HOUR = 8;
const END_HOUR = 14; 
const SLOTS_PER_HOUR = 2; 
const TOTAL_SLOTS = (END_HOUR - START_HOUR) * SLOTS_PER_HOUR;

const diasSemana = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const diasNombresES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"];

// UI Elements
const btn = document.getElementById('btnEjecutar');
const selectorTerm = document.getElementById('selectorTerm');
const loadingArea = document.getElementById('loading-area');
const loadingLabel = document.getElementById('loading-label');
const loadingSuffix = document.getElementById('loading-suffix');
const contadorText = document.getElementById('contador');
const contenedorCalendarios = document.getElementById('calendarios-grados');

// Mapa de colores para asignaturas
const asignaturaColores = {};
let colorCounter = 1;
// Grados seleccionados por el usuario
let selectedGrades = new Set();
let rootCalendarState = new Map();
let gradeNamesMap = new Map();

// Modal bootstrap
let modalSeleccionGradosEl = null;
let modalSeleccionGrados = null;

btn.onclick = function() {
    const termSeleccionado = selectorTerm.value; // Capturamos Q1 o Q2
    
    btn.disabled = true;
    btn.style.display = 'none';
    selectorTerm.disabled = true; // Bloqueamos el selector durante la generación
    loadingArea.style.display = 'block';
    contenedorCalendarios.innerHTML = "";
    contadorText.innerText = "0";

    const checks = document.querySelectorAll('.res-check:checked');
    let paramsRes = "";
    checks.forEach(c => paramsRes += `&res=${c.value}`);

    // Añadimos los grados seleccionados (si los hay). Roots están prefijados 'root:ADE'
    let paramsGrados = "";
    selectedGrades.forEach(g => paramsGrados += `&grados=${encodeURIComponent(g)}`);

    // Pasamos el cuatrimestre, restricciones y grados en la URL
    const eventSource = new EventSource(`/solver/progress?term=${termSeleccionado}${paramsRes}${paramsGrados}`);

    eventSource.onmessage = function(e) {
        const data = JSON.parse(e.data);
        
        // Mostramos la fase actual (Generando o Optimizando)
        if (data.fase && data.fase.startsWith('optimizando')) {
            loadingLabel.innerText = "Optimizando Horarios...";
            contadorText.innerText = "";
            loadingSuffix.style.display = 'none';
        } else {
            loadingLabel.innerText = "Generando Horarios:";
            contadorText.innerText = data.progreso;
            loadingSuffix.style.display = 'inline';
        }

        if (data.fase === 'finalizado') {
            eventSource.close();
            btn.disabled = false;
            btn.style.display = 'inline-block';
            selectorTerm.disabled = false;
            loadingArea.style.display = 'none';

            clearMessage();

            if (data.error) {
                showMessage(data.error);
                return;
            }

            if (data.horario && data.horario.length > 0) {
                procesarYDibujarCalendarios(data.horario);
                
                // Actualizar panel de auditoría
                const logArea = document.getElementById('log-restricciones');
                const lista = document.getElementById('lista-logs');
                logArea.style.display = 'block';
                lista.innerHTML = "";
                for (const [res, puntos] of Object.entries(data.logs)) {
                    lista.innerHTML += `<li>${res}: <strong>${puntos} pts</strong></li>`;
                }
            } else {
                showMessage('No se generó ningún horario. Por favor, inténtelo de nuevo.');
            }
        }
    };

    eventSource.onerror = function() {
        eventSource.close();
        btn.disabled = false;
        selectorTerm.disabled = false;
        loadingArea.style.display = 'none';
        showMessage('Se produjo un error en la conexión con el servidor, por favor inténtelo de nuevo.');
        console.error("Error de conexión SSE.");
    };
};

function showMessage(text) {
    const messageArea = document.getElementById('message-area');
    if (!messageArea) return;
    messageArea.textContent = text;
    messageArea.style.display = 'block';
}

function clearMessage() {
    const messageArea = document.getElementById('message-area');
    if (!messageArea) return;
    messageArea.textContent = '';
    messageArea.style.display = 'none';
}

function normalizarRoot(grado) {
    return grado.replace(/^\d+/, '');
}

function compararGrados(a, b) {
    const matchA = String(a).match(/^\d+/) || [];
    const matchB = String(b).match(/^\d+/) || [];
    const numA = parseInt(matchA[0] || '0', 10);
    const numB = parseInt(matchB[0] || '0', 10);
    if (numA !== numB) return numA - numB;
    return String(a).localeCompare(String(b));
}

function procesarYDibujarCalendarios(horario) {
    const sesionesPorGrado = {};
    const gruposPorRoot = new Map();

    horario.forEach(sesion => {
        sesion.grades.forEach(grado => {
            if (!sesionesPorGrado[grado]) sesionesPorGrado[grado] = [];
            sesionesPorGrado[grado].push(sesion);

            const root = normalizarRoot(grado);
            if (!gruposPorRoot.has(root)) gruposPorRoot.set(root, new Set());
            gruposPorRoot.get(root).add(grado);
        });
    });

    rootCalendarState.clear();
    const roots = Array.from(gruposPorRoot.keys()).sort((a, b) => a.localeCompare(b));

    contenedorCalendarios.innerHTML = roots.map(root => {
        const grados = Array.from(gruposPorRoot.get(root)).sort(compararGrados);
        const gradoActual = grados[0];
        const rootName = gradeNamesMap.get(gradoActual) || root;
        const gradoActualName = gradeNamesMap.get(gradoActual) || gradoActual;

        rootCalendarState.set(root, {
            grades: grados,
            currentIndex: 0,
            sesionesPorGrado: sesionesPorGrado
        });

        return `
            <section class="root-calendar-group card shadow-sm p-3 mb-4" data-root="${root}">
                <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
                    <div>
                        <p class="text-muted mb-1">Carrera / grado</p>
                        <h3 class="mb-0">${rootName}</h3>
                        ${rootName !== root ? `<p class="text-muted small mb-0">${root}</p>` : ''}
                    </div>
                    <div class="grade-nav d-flex align-items-center gap-2">
                        <button type="button" class="btn btn-outline-secondary btn-sm grade-nav-btn" data-action="prev">←</button>
                        <span class="fw-bold grade-label">${gradoActualName}</span>
                        <button type="button" class="btn btn-outline-secondary btn-sm grade-nav-btn" data-action="next">→</button>
                    </div>
                </div>
                <div class="calendar-slot">
                    ${crearEstructuraCalendario(gradoActual, sesionesPorGrado[gradoActual], false)}
                </div>
                <p class="small text-muted mt-3 mb-0">
                    Mostrando <strong>${gradoActualName}</strong> • ${grados.length} curso${grados.length === 1 ? '' : 's'} disponible${grados.length === 1 ? '' : 's'}
                </p>
            </section>
        `;
    }).join('');

    activarNavegacionDeGrados();
}

function activarNavegacionDeGrados() {
    document.querySelectorAll('.grade-nav-btn').forEach(boton => {
        boton.onclick = (evento) => {
            const seccion = evento.currentTarget.closest('.root-calendar-group');
            const accion = evento.currentTarget.dataset.action;
            const delta = accion === 'prev' ? -1 : 1;
            actualizarGrado(seccion, delta);
        };
    });
}

function actualizarGrado(seccion, delta) {
    const root = seccion.dataset.root;
    const estado = rootCalendarState.get(root);

    if (!estado) return;

    estado.currentIndex = (estado.currentIndex + delta + estado.grades.length) % estado.grades.length;
    const gradoActual = estado.grades[estado.currentIndex];
    const gradoActualName = gradeNamesMap.get(gradoActual) || gradoActual;

    seccion.querySelector('.grade-label').textContent = gradoActualName;
    seccion.querySelector('.calendar-slot').innerHTML = crearEstructuraCalendario(gradoActual, estado.sesionesPorGrado[gradoActual], false);
    seccion.querySelector('.small.text-muted').innerHTML = `Mostrando <strong>${gradoActualName}</strong> • ${estado.grades.length} curso${estado.grades.length === 1 ? '' : 's'} disponible${estado.grades.length === 1 ? '' : 's'}`;
}

function crearEstructuraCalendario(grado, sesiones, mostrarTitulo = true) {
    let html = `
        <div class="calendar-container card shadow-sm p-3">
    `;

    if (mostrarTitulo) {
        html += `<h3 class="grade-title text-center">Grado: ${grado}</h3>`;
    }

    html += `
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
    return html;
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

// Cargar checks al iniciar (restricciones)
document.addEventListener('DOMContentLoaded', () => {
fetch('/api/config/restricciones')
    .then(res => res.json())
    .then(data => {
        const container = document.getElementById('contenedor-checks');
        for (const [id, config] of Object.entries(data)) {
            const label = config.label || '';
            const description = config.description || '';
            container.innerHTML += `
                <div class="form-check me-3 mb-2 d-flex align-items-center gap-1">
                    <input class="form-check-input res-check" type="checkbox" value="${id}" id="check-${id}">
                    <label class="form-check-label mb-0" for="check-${id}">${label}</label>
                    <span class="text-muted" title="${description}" style="cursor: help; font-size: 1.2rem;">🛈</span>
                </div>`;
        }
    });

fetch('/api/grados/list')
    .then(res => res.json())
    .then(data => {
        data.forEach(g => {
            gradeNamesMap.set(g.id, g.name || g.id);
        });
    })
    .catch(err => {
        console.warn('No se pudo cargar nombres de grados:', err);
    });

    // Preparar modal y botón de selección de grados
    modalSeleccionGradosEl = document.getElementById('modalSeleccionGrados');
    if (modalSeleccionGradosEl) {
        modalSeleccionGrados = new bootstrap.Modal(modalSeleccionGradosEl, {});

        document.getElementById('btnSeleccionGrados').addEventListener('click', () => {
            cargarListaGrados();
            modalSeleccionGrados.show();
        });

        document.getElementById('btnConfirmarGrados').addEventListener('click', () => {
            // Recoger grades individuales seleccionados
            const checks = modalSeleccionGradosEl.querySelectorAll('input.grade-check:checked');
            const grades = Array.from(checks).map(c => c.value);

            // Recoger roots seleccionados y prefixearlos para distinguirlos
            const rootChecks = modalSeleccionGradosEl.querySelectorAll('input.root-check:checked');
            const roots = Array.from(rootChecks).map(r => r.value);

            // Guardar ambas cosas en selectedGrades (roots prefijados con 'root:')
            selectedGrades = new Set();
            grades.forEach(g => selectedGrades.add(g));
            roots.forEach(r => selectedGrades.add('root:' + r));

            const badge = document.getElementById('badgeGrados');
            if (selectedGrades.size === 0) {
                badge.innerText = 'Todos';
            } else {
                // Mostrar número de grados individuales + raíces seleccionadas
                badge.innerText = `${grades.length + roots.length} seleccionados`;
            }
        });
    }
});

function cargarListaGrados() {
    fetch('/api/grados/list')
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('modal-grados-list');
            container.innerHTML = '';

            // Calcular raíces únicas (quitar prefijo numérico)
            const roots = {};
            data.forEach(g => {
                const root = g.id.replace(/^\d+/, '');
                roots[root] = roots[root] || [];
                roots[root].push(g);
            });

            // Render grades grouped by root in compact cards
            const groupsContainer = document.createElement('div');
            groupsContainer.className = 'row row-cols-1 row-cols-md-2 row-cols-xl-3 g-3';
            Object.keys(roots).sort().forEach(root => {
                const rootName = roots[root][0]?.name || '';
                const isCheckedRoot = Array.from(selectedGrades).some(s => s === root || s === 'root:' + root);
                const cardCol = document.createElement('div');
                cardCol.className = 'col';
                cardCol.innerHTML = `
                    <div class="card h-100 shadow-sm">
                        <div class="card-body py-3 px-3">
                            <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
                                <div>
                                    <h6 class="card-title mb-1">${root}</h6>
                                    ${rootName ? `<p class="card-text small text-muted mb-1">${rootName}</p>` : ''}
                                    <p class="card-text small text-muted mb-0">${roots[root].length} grado${roots[root].length === 1 ? '' : 's'}</p>
                                </div>
                                <div class="form-check form-switch mb-0">
                                    <input class="form-check-input root-check" type="checkbox" value="${root}" id="root-${root}" ${isCheckedRoot ? 'checked' : ''}>
                                    <label class="form-check-label small" for="root-${root}">Todos</label>
                                </div>
                            </div>
                            <div class="d-flex flex-column gap-1">
                                ${roots[root].map(g => {
                                    const checked = selectedGrades.has(g.id) ? 'checked' : '';
                                    return `
                                        <div class="form-check form-check-sm">
                                            <input class="form-check-input grade-check" data-root="${root}" type="checkbox" value="${g.id}" id="grade-${g.id}" ${checked}>
                                            <label class="form-check-label small" for="grade-${g.id}">${g.id}</label>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    </div>
                `;
                groupsContainer.appendChild(cardCol);
            });
            container.appendChild(groupsContainer);

            const rootChecks = container.querySelectorAll('input.root-check');
            rootChecks.forEach(rc => {
                rc.addEventListener('change', (e) => {
                    const rootVal = e.target.value;
                    const gradeChecks = container.querySelectorAll(`input.grade-check[data-root="${rootVal}"]`);
                    gradeChecks.forEach(gc => gc.checked = e.target.checked);
                });
            });
        });
}