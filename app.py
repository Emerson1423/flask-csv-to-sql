from flask import Flask, request, render_template, send_file, redirect, url_for
import os
import csv

app = Flask(__name__)

# Configuraciones
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Límite de 50 MB

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Validar si se subió un archivo
        if 'file' not in request.files:
            return "No se subió ningún archivo", 400

        file = request.files['file']
        if file.filename == '':
            return "El archivo no tiene nombre", 400

        # Guardar el archivo CSV
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Procesar el CSV
        table_name = request.form.get('table_name', 'tabla')

        # Generar el archivo SQL
        output_file = generate_sql(file_path, table_name)

        # Redirigir a la descarga del archivo generado
        return redirect(url_for('download_file', filename=output_file))

    except Exception as e:
        return f"Error al procesar el archivo: {e}", 500


def generate_sql(csv_path, table_name):
    try:
        # Archivo de salida
        output_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{table_name}.sql")

        with open(csv_path, mode='r', encoding='utf-8') as csv_file, open(output_file, mode='w', encoding='utf-8') as sql_file:
            reader = csv.DictReader(csv_file)

            # Obtener columnas automáticamente del CSV
            columns = reader.fieldnames
            if not columns:
                raise ValueError("No se pudieron detectar columnas en el archivo CSV.")

            values = []
            for row in reader:
                formatted_row = []
                for col in columns:
                    value = row[col]
                    if value.isdigit():  # Si es un número
                        formatted_row.append(value)
                    elif value == "":  # Si está vacío, es NULL
                        formatted_row.append("NULL")
                    else:  # Si es texto
                        # Evitar problemas con las comillas
                        safe_value = "'" + value.replace("'", "''") + "'"
                        formatted_row.append(safe_value)
                values.append("(" + ", ".join(formatted_row) + ")")

                # Escribir en bloques para evitar memoria excesiva
                if len(values) >= 500:
                    sql_file.write(f"INSERT INTO `{table_name}` ({', '.join(f'`{col}`' for col in columns)}) VALUES\n")
                    sql_file.write(",\n".join(values) + ";\n")
                    values = []

            # Escribir los valores restantes
            if values:
                sql_file.write(f"INSERT INTO `{table_name}` ({', '.join(f'`{col}`' for col in columns)}) VALUES\n")
                sql_file.write(",\n".join(values) + ";\n")

        return os.path.basename(output_file)
    except Exception as e:
        raise RuntimeError(f"Error generando el archivo SQL: {e}")


@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "Archivo no encontrado", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
