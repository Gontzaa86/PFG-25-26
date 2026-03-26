from flask import Flask, render_template

# Crear la app de Flask
app = Flask(__name__)

# Ruta principal
@app.route('/')
def inicio():
    return render_template('inicio.html')

# Ejecutar la app
if __name__ == '__main__':
    # debug=True recarga automáticamente al guardar cambios
    app.run(debug=True)