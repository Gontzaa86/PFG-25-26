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

// Ejecutar cuando el DOM esté listo para inicializar el buscador de profesores
document.addEventListener('DOMContentLoaded', () => {
    const inputBuscar = document.getElementById('buscarProfesor');
    if (inputBuscar) {
        inputBuscar.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();
            const selectTeacher = document.getElementById('editTeacher');
            const opciones = selectTeacher.options;

            for (let i = 0; i < opciones.length; i++) {
                const opt = opciones[i];
                // No filtrar la opción "No asignado"
                if (opt.value === "No asignado") continue;
                
                const texto = opt.text.toLowerCase();
                if (texto.includes(query)) {
                    opt.style.display = "";
                } else {
                    opt.style.display = "none";
                }
            }
        });
    }
});

// Función interna para renderizar los grados en formato Matriz/Filas
function renderizarPanelGradosCheckbox(gradosSeleccionadosActualmente) {
    const contenedor = document.getElementById('contenedorGradosAgrupados');
    contenedor.innerHTML = ""; // Limpiar

    const todosLosGrados = window.__GRADOS_LISTA_COMPLETA || [];
    const mapaAgrupado = {};

    todosLosGrados.forEach(grado => {
        const id = grado.id; // Ej: "1ADE", "4COTam", "2INFOR"
        
        // Expresión regular para separar el número del curso del nombre de la carrera
        // Captura el primer número (curso) y el resto del string (carrera)
        const match = id.match(/^(\d+)?(.*)$/);
        let curso = match[1] ? parseInt(match[1]) : 99; // Si no tiene número, se manda al final (99)
        let carrera = match[2] || "Otros";

        // Caso especial si la carrera queda vacía por alguna anomalía
        if (!carrera) carrera = "General";

        if (!mapaAgrupado[carrera]) {
            mapaAgrupado[carrera] = [];
        }
        mapaAgrupado[carrera].push({ id: id, name: grado.name, curso: curso });
    });

    // Crear las filas ordenadas por el nombre de la carrera
    const carrerasOrdenadas = Object.keys(mapaAgrupado).sort();

    carrerasOrdenadas.forEach(carrera => {
        // Ordenar los grados de esta carrera internamente por número de curso (1, 2, 3, 4...)
        const listaGrados = mapaAgrupado[carrera].sort((a, b) => a.curso - b.curso);

        // Crear contenedor de fila estilizado
        const rowDiv = document.createElement('div');
        rowDiv.className = "d-flex flex-wrap align-items-center gap-2 mb-3 border-bottom pb-2";

        // Etiqueta de la carrera al inicio de la fila
        const labelCarrera = document.createElement('span');
        labelCarrera.className = "badge bg-secondary me-2 p-2";
        labelCarrera.style.minWidth = "80px";
        labelCarrera.textContent = carrera;
        rowDiv.appendChild(labelCarrera);

        // Crear los botones tipo checkbox para cada uno de sus cursos
        listaGrados.forEach(g => {
            const estaSeleccionado = gradosSeleccionadosActualmente.includes(g.id);

            const itemDiv = document.createElement('div');
            itemDiv.className = "form-check-inline";

            // Un checkbox real oculto pero funcional
            const inputCheck = document.createElement('input');
            inputCheck.type = "checkbox";
            inputCheck.className = "btn-check";
            inputCheck.id = `btncheck-${g.id}`;
            inputCheck.value = g.id;
            inputCheck.name = "grados_seleccionados";
            inputCheck.checked = estaSeleccionado;

            // El botón visual que cambia de estado al hacer clic sin desmarcar el resto
            const labelBtn = document.createElement('label');
            labelBtn.className = `btn btn-sm ${estaSeleccionado ? 'btn-primary' : 'btn-outline-primary'}`;
            labelBtn.htmlFor = `btncheck-${g.id}`;
            labelBtn.title = g.name; // Tooltip con el nombre largo
            labelBtn.textContent = g.id;

            // Evento dinámico para cambiar el color del botón instantáneamente al hacer click
            inputCheck.addEventListener('change', function() {
                if (this.checked) {
                    labelBtn.className = "btn btn-sm btn-primary";
                } else {
                    labelBtn.className = "btn btn-sm btn-outline-primary";
                }
            });

            itemDiv.appendChild(inputCheck);
            itemDiv.appendChild(labelBtn);
            rowDiv.appendChild(itemDiv);
        });

        contenedor.appendChild(rowDiv);
    });
}

function abrirModalEditarAsignatura(cursoId) {
    const curso = window.__GRADOS_ASIGNATURAS.find(c => String(c.id) === String(cursoId));
    if (!curso) {
        alert('No se encontraron los datos de la asignatura.');
        return;
    }

    // Resetear el buscador de profesores
    document.getElementById('buscarProfesor').value = "";
    const opcionesProf = document.getElementById('editTeacher').options;
    for(let i=0; i<opcionesProf.length; i++) opcionesProf[i].style.display = "";

    // Cargar datos básicos
    document.getElementById('editCursoId').value = curso.id;
    document.getElementById('editName').value = curso.name;
    
    const termNum = curso.term ? curso.term.replace('Q', '') : '1';
    document.getElementById('editTerm').value = termNum;
    
    document.getElementById('editTeacher').value = curso.teacher || 'No asignado';
    document.getElementById('editStudents').value = curso.students || 0;
    document.getElementById('editSessions').value = curso.sessions_per_week || 1;
    document.getElementById('editDuration').value = curso.duration_slots || 4;
    document.getElementById('editOptativa').checked = !!curso.optativa;

    // Renderizar la matriz de grados seleccionados
    const cursoGrades = curso.grades || [];
    renderizarPanelGradosCheckbox(cursoGrades);

    if (!modalEditarAsignaturaInstance) {
        modalEditarAsignaturaInstance = new bootstrap.Modal(document.getElementById('modalEditarAsignatura'));
    }
    modalEditarAsignaturaInstance.show();
}

async function guardarCambiosAsignatura() {
    const cursoId = document.getElementById('editCursoId').value;
    
    // Obtener todos los checkboxes de grados que estén marcados
    const checkboxesMarcados = document.querySelectorAll('input[name="grados_seleccionados"]:checked');
    const gradosSeleccionados = Array.from(checkboxesMarcados).map(cb => cb.value);

    const payload = {
        name: document.getElementById('editName').value,
        term: document.getElementById('editTerm').value,
        teacher: document.getElementById('editTeacher').value,
        grades: gradosSeleccionados, // Enviamos el array nativo acumulado
        students: parseInt(document.getElementById('editStudents').value) || 0,
        sessions_per_week: parseInt(document.getElementById('editSessions').value) || 1,
        duration_slots: parseInt(document.getElementById('editDuration').value) || 4,
        optativa: document.getElementById('editOptativa').checked
    };

    if (!payload.name) {
        alert('El nombre de la asignatura es obligatorio.');
        return;
    }

    try {
        const resp = await fetch(`/api/asignaturas/${cursoId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const resultado = await resp.json();

        if (resp.ok) {
            alert(resultado.message || 'Asignatura modificada con éxito.');
            if (modalEditarAsignaturaInstance) {
                modalEditarAsignaturaInstance.hide();
            }
            location.reload();
        } else {
            alert(resultado.error || 'Hubo un problema al guardar los cambios.');
        }
    } catch (error) {
        console.error('Error al actualizar asignatura:', error);
        alert('No se pudo establecer conexión con el backend.');
    }
}

// Variable de control para el estado del modal de asignaturas ('crear' o 'editar')
let modoModalAsignatura = 'editar';

async function guardarNuevoGrado() {
    const year = document.getElementById('addGradoYear').value.trim();
    const existing = document.getElementById('addGradoExisting').value;

    if (!year || !existing) {
        alert('Por favor, seleccione el año y la titulación (o elija "Nueva titulación").');
        return;
    }

    let payload = { year };

    if (existing === 'new') {
        const code = document.getElementById('addGradoCode').value.trim();
        const name = document.getElementById('addGradoName').value.trim();
        if (!code || !name) {
            alert('Para crear una nueva titulación, indique el tag y el nombre completo.');
            return;
        }
        payload.code = code;
        payload.name = name;
    } else {
        payload.existing_tag = existing;
    }

    try {
        const resp = await fetch('/api/grados', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const res = await resp.json();

        if (resp.ok) {
            alert(res.message);
            location.reload();
        } else {
            alert(res.error || 'Error al guardar el grado.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('No se pudo conectar con el servidor.');
    }
}

// Mostrar/ocultar campos de nueva titulación según selección
document.addEventListener('DOMContentLoaded', () => {
    const sel = document.getElementById('addGradoExisting');
    const campos = document.getElementById('nuevoTitulacionFields');
    if (!sel) return;
    sel.addEventListener('change', () => {
        if (sel.value === 'new') {
            campos.style.display = '';
        } else {
            campos.style.display = 'none';
        }
    });
});


// FUNCIONES PARA ASIGNATURAS
function abrirModalCrearAsignatura(gradoIdPredeterminado) {
    modoModalAsignatura = 'crear';
    

    // Ocultar botón eliminar en modo creación
    const btnEliminar = document.getElementById('btnEliminarAsignaturaModal');
    if (btnEliminar) btnEliminar.style.display = 'none';

    // Cambiar el título del modal dinámicamente
    const modalTitle = document.querySelector('#modalEditarAsignatura .modal-title');
    if (modalTitle) modalTitle.innerHTML = '<i class="bi bi-plus-circle"></i> Añadir Nueva Asignatura';

    // Limpiar campos del formulario
    document.getElementById('editCursoId').value = "";
    document.getElementById('editName').value = "";
    document.getElementById('editTerm').value = "1";
    document.getElementById('editTeacher').value = "No asignado";
    document.getElementById('editStudents').value = 0;
    document.getElementById('editSessions').value = 2;
    document.getElementById('editDuration').value = 4;
    document.getElementById('editOptativa').checked = false;
    document.getElementById('buscarProfesor').value = "";

    // Forzar el filtrado del profesor para que aparezcan todos
    const opcionesProf = document.getElementById('editTeacher').options;
    for(let i=0; i<opcionesProf.length; i++) opcionesProf[i].style.display = "";

    // Renderizar la lista completa de checkboxes pre-marcando el grado desde el que se llamó
    renderizarPanelGradosCheckbox([gradoIdPredeterminado]);

    if (!modalEditarAsignaturaInstance) {
        modalEditarAsignaturaInstance = new bootstrap.Modal(document.getElementById('modalEditarAsignatura'));
    }
    modalEditarAsignaturaInstance.show();
}

// Re-enrutamos la función original de apertura de edición para definir el modo
const viejaFuncionAbrirEditar = abrirModalEditarAsignatura;
abrirModalEditarAsignatura = function(cursoId) {
    modoModalAsignatura = 'editar';
    
    // Mostrar botón eliminar en modo edición
    const btnEliminar = document.getElementById('btnEliminarAsignaturaModal');
    if (btnEliminar) btnEliminar.style.display = 'block';

    const modalTitle = document.querySelector('#modalEditarAsignatura .modal-title');
    if (modalTitle) modalTitle.innerHTML = '<i class="bi bi-pencil-square"></i> Editar Asignatura';
    
    viejaFuncionAbrirEditar(cursoId);
};

// Evaluadora central que sustituye el comportamiento del botón guardar
async function procesarFormularioAsignatura() {
    if (modoModalAsignatura === 'editar') {
        await guardarCambiosAsignatura(); // Ejecuta tu función original nativa
    } else {
        await guardarNuevaAsignatura();   // Ejecuta el flujo de guardado POST
    }
}

async function guardarNuevaAsignatura() {
    const checkboxesMarcados = document.querySelectorAll('input[name="grados_seleccionados"]:checked');
    const gradosSeleccionados = Array.from(checkboxesMarcados).map(cb => cb.value);

    const payload = {
        name: document.getElementById('editName').value.trim(),
        term: document.getElementById('editTerm').value,
        teacher: document.getElementById('editTeacher').value,
        grades: gradosSeleccionados,
        students: parseInt(document.getElementById('editStudents').value) || 0,
        sessions_per_week: parseInt(document.getElementById('editSessions').value) || 1,
        duration_slots: parseInt(document.getElementById('editDuration').value) || 4,
        optativa: document.getElementById('editOptativa').checked
    };

    if (!payload.name) {
        alert('El nombre de la asignatura es obligatorio.');
        return;
    }

    try {
        const resp = await fetch('/api/asignaturas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const resultado = await resp.json();

        if (resp.ok) {
            alert(resultado.message || 'Asignatura creada con éxito.');
            if (modalEditarAsignaturaInstance) modalEditarAsignaturaInstance.hide();
            location.reload();
        } else {
            alert(resultado.error || 'Hubo un problema al crear la asignatura.');
        }
    } catch (error) {
        console.error('Error al crear asignatura:', error);
        alert('No se pudo establecer conexión con el backend.');
    }
}

async function eliminarGradoCompleto(gradoId) {
    const confirmacion = confirm(`¿Estás completamente seguro de que deseas eliminar el grado "${gradoId}"?\n\nEsta acción borrará el grado y lo eliminará de todas las asignaturas asociadas.`);
    if (!confirmacion) return;

    try {
        const resp = await fetch(`/api/grados/${encodeURIComponent(gradoId)}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        const res = await resp.json();

        if (resp.ok) {
            alert(res.message || 'Grado eliminado con éxito.');
            location.reload();
        } else {
            alert(res.error || 'No se pudo eliminar el grado.');
        }
    } catch (error) {
        console.error('Error al eliminar grado:', error);
        alert('Ocurrió un error de red al intentar eliminar el grado.');
    }
}

async function eliminarAsignaturaActual() {
    const cursoId = document.getElementById('editCursoId').value;
    const nombreAsignatura = document.getElementById('editName').value;

    if (!cursoId) {
        alert('No se pudo determinar el ID de la asignatura a eliminar.');
        return;
    }

    const confirmacion = confirm(`¿Seguro que deseas eliminar definitivamente la asignatura:\n"${nombreAsignatura}"?`);
    if (!confirmacion) return;

    try {
        const resp = await fetch(`/api/asignaturas/${encodeURIComponent(cursoId)}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        const res = await resp.json();

        if (resp.ok) {
            alert(res.message || 'Asignatura eliminada con éxito.');
            if (modalEditarAsignaturaInstance) modalEditarAsignaturaInstance.hide();
            location.reload();
        } else {
            alert(res.error || 'No se pudo eliminar la asignatura.');
        }
    } catch (error) {
        console.error('Error al eliminar asignatura:', error);
        alert('Ocurrió un error de red al intentar eliminar la asignatura.');
    }
}