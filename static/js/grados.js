function filtrarGrados() 
{
    const texto = document.getElementById('buscadorGrado').value.toLowerCase();
    const grados = document.querySelectorAll('.seccion-grado');

    grados.forEach(grado => {
        const nombreCarrera = grado.getAttribute('data-nombre');

        if (nombreCarrera.includes(texto)) 
        {
            if (grado.style.display === "none")
            {
                grado.classList.add("animar-entrada");
            }
            grado.style.display = "";
        } 
        else 
        {
            grado.style.display = "none";
            grado.classList.remove("animar-entrada");
        }
    });
}

function actualizarGrupoGrados(codigoGrupo, direccion) {
    const cardBody = document.querySelector(`.card-body[data-grupo="${codigoGrupo}"]`);
    if (!cardBody) return;

    const secciones = Array.from(cardBody.querySelectorAll('.grado-por-codigo'));
    let indiceActual = Number(cardBody.dataset.gradoIndex || 0);
    const maxIndice = secciones.length - 1;

    if (direccion === 'prev' && indiceActual > 0) {
        secciones[indiceActual].style.display = 'none';
        indiceActual -= 1;
        secciones[indiceActual].style.display = '';
    }
    if (direccion === 'next' && indiceActual < maxIndice) {
        secciones[indiceActual].style.display = 'none';
        indiceActual += 1;
        secciones[indiceActual].style.display = '';
    }

    cardBody.dataset.gradoIndex = indiceActual;

    const labelActual = document.querySelector(`.grupo-curso-actual[data-grupo="${codigoGrupo}"]`);
    if (labelActual) {
        labelActual.textContent = secciones[indiceActual].dataset.gradoId;
    }

    const btnPrev = document.querySelector(`.btn-prev-grado[data-grupo="${codigoGrupo}"]`);
    const btnNext = document.querySelector(`.btn-next-grado[data-grupo="${codigoGrupo}"]`);

    if (btnPrev) btnPrev.disabled = indiceActual <= 0;
    if (btnNext) btnNext.disabled = indiceActual >= maxIndice;
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.btn-prev-grado').forEach(btn => {
        btn.addEventListener('click', () => actualizarGrupoGrados(btn.dataset.grupo, 'prev'));
    });

    document.querySelectorAll('.btn-next-grado').forEach(btn => {
        btn.addEventListener('click', () => actualizarGrupoGrados(btn.dataset.grupo, 'next'));
    });
});

async function procesarImportacion(input) {
    if (!input.files || input.files.length === 0) return;

    const archivo = input.files[0];
    const formData = new FormData();
    formData.append('file', archivo);

    try {
        const resp = await fetch('/api/asignaturas/importar', {
            method: 'POST',
            body: formData
        });

        const result = await resp.json();

        if (resp.ok) {
            alert(result.message || 'Importación completada.');
            location.reload();
        } else {
            alert(result.error || 'Error al importar las asignaturas.');
        }
    } catch (error) {
        console.error('Error de importación:', error);
        alert('No se pudo conectar con el servidor durante la importación.');
    }
}

// Variable global para controlar la instancia del modal de Edición de Asignaturas
let modalEditarAsignaturaInstance = null;

function abrirModalEditarAsignatura(cursoId) {
    // 1. Buscar los datos locales de la asignatura usando la variable inyectada en el HTML
    const curso = window.__GRADOS_ASIGNATURAS.find(c => String(c.id) === String(cursoId));
    if (!curso) {
        alert('No se encontraron los datos de la asignatura.');
        return;
    }

    // 2. Rellenar los campos del formulario en el modal
    document.getElementById('editCursoId').value = curso.id;
    document.getElementById('editName').value = curso.name;
    
    // Convertir 'Q1'/'Q2' a '1'/'2'
    const termNum = curso.term ? curso.term.replace('Q', '') : '1';
    document.getElementById('editTerm').value = termNum;
    
    document.getElementById('editTeacher').value = curso.teacher || 'No asignado';
    document.getElementById('editStudents').value = curso.students || 0;
    document.getElementById('editSessions').value = curso.sessions_per_week || 1;
    document.getElementById('editDuration').value = curso.duration_slots || 4;
    document.getElementById('editOptativa').checked = !!curso.optativa;

    // 3. Mapear la selección múltiple de los grados
    const selectGrados = document.getElementById('editGrades');
    const cursoGrades = curso.grades || [];
    
    Array.from(selectGrados.options).forEach(option => {
        option.selected = cursoGrades.includes(option.value);
    });

    // 4. Mostrar el modal de Bootstrap
    if (!modalEditarAsignaturaInstance) {
        modalEditarAsignaturaInstance = new bootstrap.Modal(document.getElementById('modalEditarAsignatura'));
    }
    modalEditarAsignaturaInstance.show();
}

async function guardarCambiosAsignatura() {
    const cursoId = document.getElementById('editCursoId').value;
    
    // Obtener los grados seleccionados en el select múltiple
    const selectGrados = document.getElementById('editGrades');
    const gradosSeleccionados = Array.from(selectGrados.selectedOptions).map(opt => opt.value);

    // Construir el payload JSON con los campos requeridos
    const payload = {
        name: document.getElementById('editName').value,
        term: document.getElementById('editTerm').value,
        teacher: document.getElementById('editTeacher').value,
        grades: gradosSeleccionados,
        students: parseInt(document.getElementById('editStudents').value) || 0,
        sessions_per_week: parseInt(document.getElementById('editSessions').value) || 1,
        duration_slots: parseInt(document.getElementById('editDuration').value) || 4,
        optativa: document.getElementById('editOptativa').checked
    };

    // Validación básica del lado del cliente
    if (!payload.name) {
        alert('El nombre de la asignatura es obligatorio.');
        return;
    }

    try {
        const resp = await fetch(`/api/asignaturas/${cursoId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const resultado = await resp.json();

        if (resp.ok) {
            alert(resultado.message || 'Asignatura modificada con éxito.');
            if (modalEditarAsignaturaInstance) {
                modalEditarAsignaturaInstance.hide();
            }
            location.reload(); // Recargar la página para visualizar las mutaciones de datos
        } else {
            alert(resultado.error || 'Hubo un problema al guardar los cambios.');
        }
    } catch (error) {
        console.error('Error al actualizar asignatura:', error);
        alert('No se pudo establecer conexión con el backend.');
    }
}