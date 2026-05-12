let archivoAulasPendiente = null;
let modalAula = null;
const modalConfirmacionAulas = new bootstrap.Modal(document.getElementById('modalConfirmarImportarAulas'));

function subirAulas(input) {
    if (!input.files || !input.files[0]) return;
    archivoAulasPendiente = input.files[0];
    modalConfirmacionAulas.show();
}

document.addEventListener('DOMContentLoaded', function() {
    modalAula = new bootstrap.Modal(document.getElementById('modalAula'));
});

document.getElementById('btnConfirmarSubidaAulas').addEventListener('click', async () => {
    if (!archivoAulasPendiente) return;

    const btn = document.getElementById('btnConfirmarSubidaAulas');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Procesando...';
    btn.disabled = true;

    const formData = new FormData();
    formData.append('file', archivoAulasPendiente);

    try {
        const res = await fetch('/api/aulas/importar', {
            method: 'POST',
            body: formData
        });

        const result = await res.json();

        if (res.ok) {
            modalConfirmacionAulas.hide();
            alert(`¡Éxito! Se han importado ${result.count} aulas correctamente.`);
            window.location.reload();
        } else {
            alert('Error: ' + (result.error || 'No se pudo procesar el archivo.'));
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error crítico al conectar con el servidor.');
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
});

document.getElementById('modalConfirmarImportarAulas').addEventListener('hidden.bs.modal', () => {
    document.getElementById('csv-aulas').value = '';
    archivoAulasPendiente = null;
});

function abrirModalCrearAula() {
    document.getElementById('modalTituloAula').innerText = 'Añadir Aula';
    document.getElementById('formAula').reset();
    document.getElementById('originalAulaId').value = '';
    document.getElementById('inputNuevoEdificio').classList.add('d-none');
    modalAula.show();
}

async function prepararEdicionAula(id) {
    document.getElementById('modalTituloAula').innerText = 'Editar Aula';
    document.getElementById('formAula').reset();
    document.getElementById('originalAulaId').value = id;
    document.getElementById('inputNuevoEdificio').classList.add('d-none');

    try {
        const res = await fetch(`/api/aulas/${encodeURIComponent(id)}`);
        if (!res.ok) {
            alert('No se encontró el aula solicitada.');
            return;
        }

        const aula = await res.json();
        document.getElementById('aulaId').value = aula.id;
        document.getElementById('aulaCapacity').value = aula.capacity;

        const selectEdificio = document.getElementById('aulaEdificio');
        const opcionExistente = Array.from(selectEdificio.options).find(opt => opt.value === aula.building);
        if (opcionExistente) {
            selectEdificio.value = aula.building;
        } else {
            selectEdificio.value = 'NUEVO';
            document.getElementById('nuevaEdificioNombre').value = aula.building;
            document.getElementById('inputNuevoEdificio').classList.remove('d-none');
        }

        modalAula.show();
    } catch (error) {
        console.error('Error cargando aula:', error);
        alert('Error cargando datos del aula.');
    }
}

async function guardarAula() {
    const originalId = document.getElementById('originalAulaId').value.trim();
    const aulaId = document.getElementById('aulaId').value.trim();
    const edificioSelect = document.getElementById('aulaEdificio');
    let building = edificioSelect.value;
    const nuevaEdificio = document.getElementById('nuevaEdificioNombre').value.trim();
    const capacity = parseInt(document.getElementById('aulaCapacity').value, 10);

    if (!aulaId || !building || isNaN(capacity) || capacity < 1) {
        return alert('Por favor, rellena todos los campos correctamente.');
    }

    if (building === 'NUEVO') {
        if (!nuevaEdificio) {
            return alert('Por favor, indica el nombre del nuevo edificio.');
        }
        building = nuevaEdificio;
    }

    building = normalizarNombreEdificio(building);

    const payload = {
        id: aulaId,
        building,
        capacity
    };
    if (originalId) {
        payload.original_id = originalId;
    }

    try {
        const res = await fetch('/api/aulas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await res.json();
        if (!res.ok) {
            return alert(result.error || 'No se pudo guardar el aula.');
        }

        modalAula.hide();
        window.location.reload();
    } catch (error) {
        console.error('Error guardando aula:', error);
        alert('Error al guardar el aula.');
    }
}

function verificarNuevaEdificio(select) {
    const inputDiv = document.getElementById('inputNuevoEdificio');
    if (select.value === 'NUEVO') {
        inputDiv.classList.remove('d-none');
    } else {
        inputDiv.classList.add('d-none');
    }
}

function normalizarNombreEdificio(raw) {
    if (!raw) return '';

    let value = raw.trim();
    if (/^ed-/i.test(value)) {
        value = value.replace(/^ed-/i, '').trim();
    }

    const parenIndex = value.indexOf('(');
    if (parenIndex !== -1) {
        value = value.slice(0, parenIndex).trim();
    }

    value = value.replace(/\s+/g, ' ');
    value = value
        .split(' ')
        .map(word => word
            .split('-')
            .map(part => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
            .join('-'))
        .join(' ');

    return `Ed-${value}`;
}

async function intentarEliminarAula(id) {
    if (!confirm('¿Estás seguro de que deseas eliminar esta aula?')) {
        return;
    }

    try {
        const res = await fetch(`/api/aulas/${encodeURIComponent(id)}`, { method: 'DELETE' });
        if (!res.ok) {
            const error = await res.json();
            return alert(error.error || 'No se pudo eliminar el aula.');
        }
        window.location.reload();
    } catch (error) {
        console.error('Error eliminando aula:', error);
        alert('Error al eliminar el aula.');
    }
}
