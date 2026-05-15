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