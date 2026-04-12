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
    const rama = document.getElementById('profRama').value;

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
        body: JSON.stringify({ id, name: nombre, branch: rama, availability: [] })
    });
    
    if (res.ok)
    {
        bootstrap.Modal.getInstance(document.getElementById('modalProfesor')).hide();
        location.reload();
    }
}