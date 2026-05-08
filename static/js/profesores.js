// Inicialización de componentes de Bootstrap
document.addEventListener('DOMContentLoaded', function() 
{
    window.modalProfesor = new bootstrap.Modal(document.getElementById('modalProfesor'));
    window.modalDisponibilidad = new bootstrap.Modal(document.getElementById('modalDisponibilidad'));
    window.toastError = new bootstrap.Toast(document.getElementById('liveToast'));
});

// Variables globales para el modal de disponibilidad
let disponibilidadActual = {};
const diasSemana = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const horasDisponibles = [
    '08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30',
    '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30', '17:00', '17:30', '18:00'
];
const ramaOptionsHTML = document.getElementById('profRama').innerHTML;

function prepararEdicion(id, nombre, rama) 
{
    document.getElementById('modalTitulo').innerText = "Editar Profesor";
    document.getElementById('profId').value = id;
    document.getElementById('profNombre').value = nombre;
    document.getElementById('nuevaRamaNombre').value = "";
    resetSelectoresRama();

    fetch(`/api/profesores/${id}`)
        .then(res => res.ok ? res.json() : null)
        .then(profesor => {
            if (profesor) {
                cargarRamasProfesor(profesor.branch || []);
            }
        })
        .catch(error => console.error('Error cargando profesor:', error));

    window.modalProfesor.show();
}

function abrirModalCrear() 
{
    document.getElementById('modalTitulo').innerText = "Añadir Profesor";
    document.getElementById('formProfesor').reset();
    document.getElementById('profId').value = "";
    document.getElementById('nuevaRamaNombre').value = "";
    resetSelectoresRama();
    window.modalProfesor.show();
}

async function intentarEliminar(id, tieneCursos) 
{
    if (tieneCursos) 
    {
        document.getElementById('toastMsg').innerText = "No se puede eliminar al profesor porque tiene cursos asignados.";
        new bootstrap.Toast(document.getElementById('liveToast')).show();
    } 
    else 
    {
        if(confirm('¿Estás seguro de que deseas eliminar a este profesor?')) 
        {
            const res = await fetch(`/api/profesores/${id}`, { method: 'DELETE' });
            if (res.ok) location.reload(); // Recargar página para ver los cambios.
        }
    }
}

async function guardarProfesor() 
{
    const id = document.getElementById('profId').value;
    const nombre = document.getElementById('profNombre').value;
    const ramas = obtenerRamasSeleccionadas();

    if (!nombre || !ramas || ramas.length === 0) return alert("Por favor, rellena todos los campos");

    const payload = {
        name: nombre,
        branch: ramas,
        unavailability: {}  // Por defecto vacío
    };
    if (id) payload.id = id;

    const res = await fetch('/api/profesores',
    {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    if (res.ok)
    {
        const modalElement = document.getElementById('modalProfesor');
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        if (modalInstance) modalInstance.hide();
        location.reload();
    }
}

function verificarNuevaRama(select) 
{
    const inputDiv = document.getElementById('inputNuevaRama');
    const selects = Array.from(document.querySelectorAll('.profRamaSelect'));
    const anyNueva = selects.some(s => s.value === "NUEVA");

    if (anyNueva) 
    {
        inputDiv.classList.remove('d-none');
    } 
    else 
    {
        inputDiv.classList.add('d-none');
    }

    const hasEmpty = selects.some(s => !s.value);
    if (!hasEmpty) 
    {
        agregarSelectorRama();
    }
}

function crearSelectorRama(value = '', required = false) {
    const select = document.createElement('select');
    select.className = 'form-select profRamaSelect';
    select.innerHTML = ramaOptionsHTML;
    if (required) select.required = true;
    select.value = value;
    select.addEventListener('change', () => verificarNuevaRama(select));

    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.className = 'btn btn-sm btn-outline-danger';
    deleteButton.style.cssText = 'width: 2.5rem; padding: 0.25rem 0.5rem;';
    deleteButton.textContent = 'X';
    deleteButton.addEventListener('click', () => eliminarSelectorRama(deleteButton));

    const wrapper = document.createElement('div');
    wrapper.className = 'rama-item d-flex align-items-center gap-2 mb-2';
    wrapper.appendChild(select);
    wrapper.appendChild(deleteButton);
    return wrapper;
}

function resetSelectoresRama() {
    const contenedor = document.getElementById('contenedorRamas');
    contenedor.innerHTML = '';
    contenedor.appendChild(crearSelectorRama('', true));
    document.getElementById('inputNuevaRama').classList.add('d-none');
}

function agregarSelectorRama(value = '') {
    const contenedor = document.getElementById('contenedorRamas');
    contenedor.appendChild(crearSelectorRama(value, false));
}

function eliminarSelectorRama(button) {
    const wrapper = button.closest('.rama-item');
    if (!wrapper) return;
    wrapper.remove();

    const selects = document.querySelectorAll('.profRamaSelect');
    if (selects.length === 0) {
        const contenedor = document.getElementById('contenedorRamas');
        contenedor.appendChild(crearSelectorRama('', true));
    }
    verificarNuevaRama();
}

function cargarRamasProfesor(ramas) {
    const contenedor = document.getElementById('contenedorRamas');
    contenedor.innerHTML = '';

    if (!Array.isArray(ramas)) {
        ramas = ramas ? [ramas] : [];
    }

    if (ramas.length === 0) {
        contenedor.appendChild(crearSelectorRama('', true));
        return;
    }

    ramas.forEach((rama, index) => {
        contenedor.appendChild(crearSelectorRama(rama, index === 0));
    });

    contenedor.appendChild(crearSelectorRama('', false));
}

function obtenerRamasSeleccionadas() {
    const selects = Array.from(document.querySelectorAll('.profRamaSelect'));
    const ramas = [];
    let nuevaRama = null;

    for (const select of selects) {
        if (!select.value) continue;
        if (select.value === 'NUEVA') {
            nuevaRama = document.getElementById('nuevaRamaNombre').value.trim().toUpperCase();
            continue;
        }
        if (!ramas.includes(select.value)) {
            ramas.push(select.value);
        }
    }

    if (selects.some(s => s.value === 'NUEVA')) {
        if (!nuevaRama) {
            alert('Por favor indica el nombre de la nueva rama');
            return null;
        }
        if (!ramas.includes(nuevaRama)) {
            ramas.push(nuevaRama);
        }
    }

    return ramas;
}

function filtrarProfesores() 
{
    const texto = document.getElementById('buscadorNombre').value.toLowerCase();
    const seccionesRama = document.querySelectorAll('.seccion-rama');

    seccionesRama.forEach(seccion => {
        // Obtener el nombre de la rama de esta sección (usando el h4)
        const nombreRamaSeccion = seccion.querySelector('h4').innerText.trim().toUpperCase();
        const tarjetas = seccion.querySelectorAll('.tarjeta-profesor');
        
        let tieneResultadosEnRama = false;

        // Lógica de visibilidad de la sección por Rama
        const ramaCoincide = (ramaSeleccionada === "TODAS" || nombreRamaSeccion === ramaSeleccionada.toUpperCase());

        tarjetas.forEach(tarjeta => {
            const nombreProfesor = tarjeta.getAttribute('data-nombre');
            const coincideNombre = nombreProfesor.includes(texto);

            if (ramaCoincide && coincideNombre) 
            {
                tarjeta.style.display = ""; 
                tieneResultadosEnRama = true;
            } 
            else 
            {
                tarjeta.style.display = "none";
            }
        });

        // Mostrar la sección solo si la rama coincide y hay profesores visibles
        if (ramaCoincide && tieneResultadosEnRama) 
        {
            seccion.style.display = "";
        } 
        else 
        {
            seccion.style.display = "none";
        }
    });
}

let ramaSeleccionada = "TODAS";
function seleccionarRama(rama) 
{
    ramaSeleccionada = rama;
    
    // Actualizar el texto del botón
    const btn = document.getElementById('btnFiltroRama');
    btn.innerText = rama === "TODAS" ? "Todas las Ramas" : rama;
    
    // Ejecutar el filtrado
    filtrarProfesores();
}

// ========== FUNCIONES DE DISPONIBILIDAD ==========

async function abrirModalDisponibilidad(profId, profNombre)
{
    document.getElementById('profIdDisp').value = profId;
    document.getElementById('modalDisponibilidadTitulo').innerText = `Disponibilidad de ${profNombre}`;
    
    // Cargar la disponibilidad actual del profesor
    const res = await fetch(`/api/profesores/${profId}`);
    if (res.ok) {
        const profesor = await res.json();
        disponibilidadActual = profesor.unavailability || {};
    } else {
        disponibilidadActual = {};
    }
    
    // Renderizar la interfaz
    renderizarInterfazDisponibilidad();
    window.modalDisponibilidad.show();
}

function renderizarInterfazDisponibilidad()
{
    const contenedor = document.getElementById('contenedorDiasHoras');
    contenedor.innerHTML = '';
    
    const diasNombres = {
        'Monday': 'Lunes',
        'Tuesday': 'Martes',
        'Wednesday': 'Miércoles',
        'Thursday': 'Jueves',
        'Friday': 'Viernes'
    };
    
    diasSemana.forEach(dia => {
        const divDia = document.createElement('div');
        divDia.className = 'col-md-6';
        
        const horasNoDisp = disponibilidadActual[dia] || [];
        const esCompleto = horasNoDisp === 'all';
        
        let html = `
            <div class="card border">
                <div class="card-header bg-light d-flex align-items-center gap-2">
                    <input type="checkbox" class="form-check-input" 
                        onchange="toggleDiaCompleto('${dia}', this.checked)"
                        ${esCompleto ? 'checked' : ''}>
                    <label class="form-check-label fw-bold mb-0">${diasNombres[dia]}</label>
                </div>
                <div class="card-body p-2">
        `;
        
        if (!esCompleto) {
            html += `<div class="d-flex flex-wrap gap-1" id="horas-${dia}">`;
            
            horasDisponibles.forEach(hora => {
                const isSelected = Array.isArray(horasNoDisp) && 
                    horasNoDisp.some(rango => {
                        const [inicio, fin] = rango.split('-');
                        return hora >= inicio && hora < fin;
                    });
                
                html += `
                    <button type="button" class="btn btn-sm ${isSelected ? 'btn-danger' : 'btn-outline-danger'} flex-grow-1"
                        onclick="toggleHora('${dia}', '${hora}')" 
                        data-hora="${hora}" 
                        data-dia="${dia}"
                        style="padding: 0.25rem 0.5rem; font-size: 0.75rem;">
                        ${hora}
                    </button>
                `;
            });
            
            html += `</div>`;
        } else {
            html += `<p class="text-center text-muted mb-0">No disponible todo el día</p>`;
        }
        
        html += `</div></div>`;
        
        divDia.innerHTML = html;
        contenedor.appendChild(divDia);
    });
}

function toggleDiaCompleto(dia, checked)
{
    if (checked) {
        disponibilidadActual[dia] = 'all';
    } else {
        disponibilidadActual[dia] = [];
    }
    renderizarInterfazDisponibilidad();
}

function toggleHora(dia, hora)
{
    if (!Array.isArray(disponibilidadActual[dia])) {
        disponibilidadActual[dia] = [];
    }
    
    const horaInicio = hora;
    const horaFin = calcularHoraFin(hora);
    const rango = `${horaInicio}-${horaFin}`;
    
    const index = disponibilidadActual[dia].findIndex(r => r === rango);
    if (index === -1) {
        disponibilidadActual[dia].push(rango);
        disponibilidadActual[dia].sort();
    } else {
        disponibilidadActual[dia].splice(index, 1);
    }
    
    if (disponibilidadActual[dia].length === 0) {
        delete disponibilidadActual[dia];
    }
    
    renderizarInterfazDisponibilidad();
}

function calcularHoraFin(horaInicio)
{
    const [horas, minutos] = horaInicio.split(':').map(Number);
    const siguienteIndice = horasDisponibles.indexOf(horaInicio) + 1;
    return siguienteIndice < horasDisponibles.length ? horasDisponibles[siguienteIndice] : '18:30';
}

async function guardarDisponibilidad()
{
    const profId = document.getElementById('profIdDisp').value;
    
    const res = await fetch(`/api/profesores/${profId}/unavailability`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ unavailability: disponibilidadActual })
    });
    
    if (res.ok) {
        const modalElement = document.getElementById('modalDisponibilidad');
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        if (modalInstance) modalInstance.hide();
        location.reload();
    } else {
        alert('Error al guardar la disponibilidad');
    }
}