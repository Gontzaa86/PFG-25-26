# NOTAS
Documento para almacenar comandos, apuntes... que puedan ser útiles de  cara a futuro, por que se puedan olvidar o voy a necesitar hacer múltiples veces durante el proceso de desarrollo.

## Poetry
### Python packaging and dependency management
Listado de comandos de poetry que puedan ser útiles.

1. cmd > poetry init
    
    Crea un proyecto nuevo gestionado por poetry. Crea el archivo *pyproject.toml*

2. cmd > poetry env activate

    Activa el entorno virtual del proyecto. Siendo este un enterno "aislado" donde se instalan las librerías.

3. cmd > poetry add (librería)

    Instalación de librerías en el proyecto, descargandola y agregandola al *pyproject.toml*, actualizando también *poetry.lock* para fijar versiones.