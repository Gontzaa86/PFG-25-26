let archivoAulasPendiente = null;
const modalConfirmacionAulas = new bootstrap.Modal(document.getElementById('modalConfirmarImportarAulas'));

function subirAulas(input) 
{
    if (!input.files || !input.files[0]) return;
    
    // Se guarda el archivo y se abre el modal en lugar de subirlo directamente
    archivoAulasPendiente = input.files[0];
    modalConfirmacionAulas.show();
}

document.getElementById('btnConfirmarSubidaAulas').addEventListener('click', async () => {
    if (!archivoAulasPendiente) return;

    const btn = document.getElementById('btnConfirmarSubidaAulas');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Procesando...';
    btn.disabled = true;

    const formData = new FormData();
    formData.append('file', archivoAulasPendiente);

    try 
    {
        const res = await fetch('/api/aulas/importar', {
            method: 'POST',
            body: formData
        });

        const result = await res.json();

        if (res.ok) 
        {
            modalConfirmacionAulas.hide();
            alert(`¡Éxito! Se han importado ${result.count} aulas correctamente.`);
            window.location.reload();
        } 
        else 
        {
            alert("Error: " + result.error);
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    } 
    catch (error) 
    {
        console.error('Error:', error);
        alert("Error crítico al conectar con el servidor.");
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
});

// Limpiar el input si se cierra el modal para permitir seleccionar el mismo archivo otra vez
document.getElementById('modalConfirmarImportarAulas').addEventListener('hidden.bs.modal', () => {
    document.getElementById('csv-aulas').value = '';
    archivoAulasPendiente = null;
});