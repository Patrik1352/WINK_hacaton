// Состояние приложения
const state = {
    sessionId: null,
    fileName: null,
    fileSize: null,
    defaultFields: [],
    selectedFields: [],
    processedData: null
};

// DOM элементы
const elements = {
    fileInput: document.getElementById('file-input'),
    uploadArea: document.getElementById('upload-area'),
    fileInfo: document.getElementById('file-info'),
    fileName: document.getElementById('file-name'),
    fileSize: document.getElementById('file-size'),
    btnRemoveFile: document.getElementById('btn-remove-file'),
    stepFields: document.getElementById('step-fields'),
    fieldsContainer: document.getElementById('fields-container'),
    btnSelectAll: document.getElementById('btn-select-all'),
    btnDeselectAll: document.getElementById('btn-deselect-all'),
    stepPreview: document.getElementById('step-preview'),
    previewContainer: document.getElementById('preview-container'),
    previewLoading: document.getElementById('preview-loading'),
    previewContent: document.getElementById('preview-content'),
    btnGeneratePreview: document.getElementById('btn-generate-preview'),
    stepProcess: document.getElementById('step-process'),
    selectedFieldsCount: document.getElementById('selected-fields-count'),
    btnProcess: document.getElementById('btn-process'),
    processProgress: document.getElementById('process-progress'),
    progressFill: document.getElementById('progress-fill'),
    progressText: document.getElementById('progress-text'),
    stepResult: document.getElementById('step-result'),
    btnDownload: document.getElementById('btn-download'),
    btnNewFile: document.getElementById('btn-new-file')
};

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
});

function initEventListeners() {
    // Загрузка файла
    elements.fileInput.addEventListener('change', handleFileSelect);
    elements.uploadArea.addEventListener('click', () => elements.fileInput.click());
    elements.uploadArea.addEventListener('dragover', handleDragOver);
    elements.uploadArea.addEventListener('dragleave', handleDragLeave);
    elements.uploadArea.addEventListener('drop', handleDrop);
    elements.btnRemoveFile.addEventListener('click', handleRemoveFile);

    // Выбор полей
    elements.btnSelectAll.addEventListener('click', () => selectAllFields(true));
    elements.btnDeselectAll.addEventListener('click', () => selectAllFields(false));

    // Превью
    elements.btnGeneratePreview.addEventListener('click', generatePreview);

    // Обработка
    elements.btnProcess.addEventListener('click', processFile);

    // Новый файл
    elements.btnNewFile.addEventListener('click', resetApp);
}

// Обработка файлов
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        processFileUpload(file);
    }
}

function handleDragOver(event) {
    event.preventDefault();
    elements.uploadArea.classList.add('dragover');
}

function handleDragLeave(event) {
    event.preventDefault();
    elements.uploadArea.classList.remove('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    elements.uploadArea.classList.remove('dragover');
    
    const file = event.dataTransfer.files[0];
    if (file) {
        processFileUpload(file);
    }
}

async function processFileUpload(file) {
    // Проверка типа файла
    const allowedTypes = ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/pdf'];
    const allowedExtensions = ['.docx', '.pdf'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedExtensions.includes(fileExtension)) {
        showError('Неподдерживаемый формат файла. Разрешены только .docx и .pdf');
        return;
    }

    // Проверка размера (50MB)
    if (file.size > 50 * 1024 * 1024) {
        showError('Файл слишком большой. Максимальный размер: 50 МБ');
        return;
    }

    // Показываем информацию о файле
    state.fileName = file.name;
    state.fileSize = formatFileSize(file.size);
    showFileInfo();

    // Загружаем файл на сервер
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            state.sessionId = data.session_id;
            state.defaultFields = data.default_fields || [];
            showStepFields();
            renderFields();
        } else {
            showError(data.error || 'Ошибка при загрузке файла');
        }
    } catch (error) {
        showError('Ошибка при загрузке файла: ' + error.message);
    }
}

function showFileInfo() {
    elements.fileName.textContent = state.fileName;
    elements.fileSize.textContent = state.fileSize;
    elements.fileInfo.style.display = 'flex';
    elements.uploadArea.querySelector('.upload-text').style.display = 'none';
    elements.uploadArea.querySelector('.upload-hint').style.display = 'none';
}

function handleRemoveFile() {
    state.sessionId = null;
    state.fileName = null;
    state.fileSize = null;
    state.defaultFields = [];
    state.selectedFields = [];
    
    elements.fileInput.value = '';
    elements.fileInfo.style.display = 'none';
    elements.uploadArea.querySelector('.upload-text').style.display = 'block';
    elements.uploadArea.querySelector('.upload-hint').style.display = 'block';
    elements.stepFields.style.display = 'none';
    elements.stepPreview.style.display = 'none';
    elements.stepProcess.style.display = 'none';
    elements.stepResult.style.display = 'none';
}

// Работа с полями
function renderFields() {
    elements.fieldsContainer.innerHTML = '';
    
    state.defaultFields.forEach(field => {
        const fieldId = field.id || field.name;
        const fieldName = field.name || fieldId;
        
        const checkbox = document.createElement('div');
        checkbox.className = 'field-checkbox';
        checkbox.innerHTML = `
            <input type="checkbox" id="field-${fieldId}" value="${fieldId}" checked>
            <label for="field-${fieldId}" class="field-label">${fieldName}</label>
        `;
        
        const input = checkbox.querySelector('input');
        input.addEventListener('change', () => {
            updateSelectedFields();
            checkbox.classList.toggle('checked', input.checked);
        });
        
        if (input.checked) {
            checkbox.classList.add('checked');
        }
        
        elements.fieldsContainer.appendChild(checkbox);
    });
    
    updateSelectedFields();
}

function updateSelectedFields() {
    const checkboxes = elements.fieldsContainer.querySelectorAll('input[type="checkbox"]:checked');
    state.selectedFields = Array.from(checkboxes).map(cb => cb.value);
    elements.selectedFieldsCount.textContent = state.selectedFields.length;
    
    // Показываем шаг обработки, если выбраны поля
    if (state.selectedFields.length > 0) {
        elements.stepProcess.style.display = 'block';
    } else {
        elements.stepProcess.style.display = 'none';
    }
}

function selectAllFields(select) {
    const checkboxes = elements.fieldsContainer.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(cb => {
        cb.checked = select;
        const checkbox = cb.closest('.field-checkbox');
        checkbox.classList.toggle('checked', select);
    });
    updateSelectedFields();
}

function showStepFields() {
    elements.stepFields.style.display = 'block';
}

// Превью
async function generatePreview() {
    if (state.selectedFields.length === 0) {
        showError('Выберите хотя бы одно поле');
        return;
    }

    elements.previewLoading.style.display = 'flex';
    elements.previewContent.style.display = 'none';

    try {
        const response = await fetch('/api/preview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fields: state.selectedFields
            })
        });

        const data = await response.json();

        if (data.success) {
            renderPreview(data.preview);
            elements.stepPreview.style.display = 'block';
        } else {
            showError(data.error || 'Ошибка при генерации превью');
        }
    } catch (error) {
        showError('Ошибка при генерации превью: ' + error.message);
    }
}

function renderPreview(preview) {
    elements.previewLoading.style.display = 'none';
    elements.previewContent.style.display = 'block';
    
    // ЗДЕСЬ ПОЛЬЗОВАТЕЛЬ ДОЛЖЕН РЕАЛИЗОВАТЬ ОТОБРАЖЕНИЕ ПРЕВЬЮ
    // Это пример реализации - пользователь должен адаптировать под свою структуру данных
    
    const previewData = preview.preview_data || [];
    
    if (previewData.length === 0) {
        elements.previewContent.innerHTML = '<p>Нет данных для отображения</p>';
        return;
    }

    // Создаем таблицу
    let html = '<table class="preview-table"><thead><tr>';
    state.selectedFields.forEach(field => {
        const fieldObj = state.defaultFields.find(f => (f.id || f.name) === field);
        const fieldName = fieldObj ? (fieldObj.name || field) : field;
        html += `<th>${fieldName}</th>`;
    });
    html += '</tr></thead><tbody>';

    // Ограничиваем количество строк для превью
    const maxRows = Math.min(previewData.length, 10);
    for (let i = 0; i < maxRows; i++) {
        html += '<tr>';
        state.selectedFields.forEach(field => {
            const value = previewData[i][field] || '';
            html += `<td>${escapeHtml(String(value))}</td>`;
        });
        html += '</tr>';
    }
    html += '</tbody></table>';

    if (previewData.length > maxRows) {
        html += `<p style="margin-top: 1rem; color: var(--text-secondary); text-align: center;">Показано ${maxRows} из ${previewData.length} записей</p>`;
    }

    elements.previewContent.innerHTML = html;
}

// Обработка файла
async function processFile() {
    if (state.selectedFields.length === 0) {
        showError('Выберите хотя бы одно поле');
        return;
    }

    const btnText = elements.btnProcess.querySelector('.btn-text');
    const btnSpinner = elements.btnProcess.querySelector('.btn-spinner');
    
    elements.btnProcess.disabled = true;
    btnText.style.display = 'none';
    btnSpinner.style.display = 'block';
    elements.processProgress.style.display = 'block';
    elements.progressFill.style.width = '30%';
    elements.progressText.textContent = 'Обработка файла...';

    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fields: state.selectedFields
            })
        });

        const data = await response.json();

        if (data.success) {
            elements.progressFill.style.width = '100%';
            elements.progressText.textContent = 'Обработка завершена!';
            
            setTimeout(() => {
                elements.btnDownload.href = data.download_url;
                elements.stepResult.style.display = 'block';
                elements.processProgress.style.display = 'none';
            }, 500);
        } else {
            showError(data.error || 'Ошибка при обработке файла');
            elements.btnProcess.disabled = false;
            btnText.style.display = 'block';
            btnSpinner.style.display = 'none';
            elements.processProgress.style.display = 'none';
        }
    } catch (error) {
        showError('Ошибка при обработке файла: ' + error.message);
        elements.btnProcess.disabled = false;
        btnText.style.display = 'block';
        btnSpinner.style.display = 'none';
        elements.processProgress.style.display = 'none';
    }
}

// Утилиты
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    // Простое отображение ошибки (можно улучшить)
    alert(message);
}

function resetApp() {
    handleRemoveFile();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}


