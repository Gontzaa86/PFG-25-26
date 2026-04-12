// Inicialización de componentes de Bootstrap
document.addEventListener('DOMContentLoaded', function() 
{
    window.modalProfesor = new bootstrap.Modal(document.getElementById('modalProfesor'));
    window.toastError = new bootstrap.Toast(document.getElementById('liveToast'));
});

function prepararEdicion(id, nombre, rama) 
{
    document.getElementById('modalTitulo').innerText = "Editar Profesor";
    document.getElementById('profId').value = id;
    document.getElementById('profNombre').value = nombre;
    document.getElementById('profRama').value = rama;
    window.modalProfesor.show();
}

function abrirModalCrear() 
{
    document.getElementById('modalTitulo').innerText = "Añadir Profesor";
    document.getElementById('formProfesor').reset();
    document.getElementById('profId').value = "";
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
    let rama = document.getElementById('profRama').value;

    // Si el usuario decide crear una nueva rama
    if (rama === "NUEVA")
    {
        rama = document.getElementById('nuevaRamaNombre').value.toUpperCase();
    }

    if (!nombre || !rama) return alert("Por favor, rellena todos los campos");

    const payload = {
        name: nombre,
        branch: rama,
        availability: [] // Por defecto vacío
    };
    if (id) payload.id = id;

    const res = await fetch ('/api/profesores',
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
    if (select.value === "NUEVA") 
    {
        inputDiv.classList.remove('d-none');
    } 
    else 
    {
        inputDiv.classList.add('d-none');
    }
}

function filtrarProfesores() 
{
    const texto = document.getElementById('buscadorNombre').value.toLowerCase();
    const seccionesRama = document.querySelectorAll('.seccion-rama');

    seccionesRama.forEach(seccion => {
        const tarjetas = seccion.querySelectorAll('.tarjeta-profesor');
        let tieneResultadosEnRama = false;

        tarjetas.forEach(tarjeta => {
            const nombreProfesor = tarjeta.getAttribute('data-nombre');
            
            if (nombreProfesor.includes(texto)) 
            {
                tarjeta.style.display = ""; // Mostrar
                tieneResultadosEnRama = true;
            } else 
            {
                tarjeta.style.display = "none"; // Ocultar
            }
        });

        // Si no hay profesores que coincidan en esta rama, ocultamos la rama entera
        if (tieneResultadosEnRama) 
        {
            seccion.style.display = "";
        } 
        else 
        {
            seccion.style.display = "none";
        }
    });
}