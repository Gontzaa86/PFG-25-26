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
            grado.style.display = ""
        } 
        else 
        {
            grado.style.display = "none";
            grado.classList.remove("animar-entrada");
        }
    });
}