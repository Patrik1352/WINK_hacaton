from flask import Flask, render_template, request, jsonify, send_file, session
import os
import json
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
from utils.file_processor import FileProcessor
from utils.excel_generator import ExcelGenerator
from utils.field_loader import FieldLoader

import sys
sys.path.append('../../')
from make_short_disc.synopsis_generator import SynopsisGenerator


app = Flask(__name__)
app.secret_key = os.urandom(24)

# Определяем базовую директорию приложения
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(BASE_DIR, 'outputs')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'docx', 'pdf'}

# Создаем необходимые директории
for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

# Инициализация утилит
file_processor = FileProcessor()
excel_generator = ExcelGenerator()
field_loader = FieldLoader()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Загрузка файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Неподдерживаемый формат файла. Разрешены только .docx и .pdf'}), 400
    
    # Генерируем уникальный ID для сессии
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    
    # Сохраняем файл
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
    file.save(filepath)
    
    # Сохраняем информацию о файле в сессии
    session['filepath'] = filepath
    session['filename'] = filename
    session['file_type'] = filename.rsplit('.', 1)[1].lower()
    
    # Загружаем поля по умолчанию
    default_fields = field_loader.load_default_fields()
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'filename': filename,
        'default_fields': default_fields
    })


@app.route('/api/fields', methods=['GET'])
def get_fields():
    """Получить список доступных полей"""
    default_fields = field_loader.load_default_fields()
    return jsonify({'fields': default_fields})


@app.route('/api/preview', methods=['POST'])
def preview_processing():
    """Превью обработки для 2 страниц"""
    data = request.json
    selected_fields = data.get('fields', [])
    session_id = session.get('session_id')
    
    if not session_id or 'filepath' not in session:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    filepath = session['filepath']
    
    # Вызываем пользовательскую логику для превью
    # Здесь пользователь должен реализовать свою логику обработки
    preview_result = file_processor.process_preview(filepath, selected_fields, pages=2)
    
    return jsonify({
        'success': True,
        'preview': preview_result
    })


@app.route('/api/process', methods=['POST'])
def process_file():
    """Обработка всего файла"""
    data = request.json
    selected_fields = data.get('fields', [])
    session_id = session.get('session_id')
    
    if not session_id or 'filepath' not in session:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    if not selected_fields:
        return jsonify({'error': 'Не выбраны поля для обработки'}), 400
    
    filepath = session['filepath']
    filename = session.get('filename', 'output')
    
    # Вызываем пользовательскую логику обработки
    # Здесь пользователь должен реализовать свою логику обработки
    processed_data = file_processor.process_file(filepath, selected_fields, syn_gen)
    
    # Генерируем Excel файл
    output_filename = f"{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    
    excel_generator.generate_excel(processed_data, selected_fields, output_path)
    
    # Сохраняем путь к файлу в сессии
    session['output_file'] = output_path
    session['output_filename'] = output_filename
    
    return jsonify({
        'success': True,
        'output_file': output_filename,
        'download_url': f'/api/download/{output_filename}'
    })


@app.route('/api/download/<filename>')
def download_file(filename):
    """Скачать обработанный Excel файл"""
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Файл не найден'}), 404
    
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.route('/api/custom-logic', methods=['POST'])
def custom_logic():
    """
    Эндпоинт для вызова пользовательской логики обработки.
    Пользователь может переопределить эту функцию или использовать её как есть.
    """
    data = request.json
    filepath = data.get('filepath')
    fields = data.get('fields', [])
    options = data.get('options', {})
    
    # Здесь пользователь может добавить свою логику
    # По умолчанию вызываем стандартную обработку
    result = file_processor.process_file(filepath, fields, options)
    
    return jsonify({
        'success': True,
        'result': result
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

